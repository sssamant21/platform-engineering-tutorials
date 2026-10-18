# Chapter 075 — TCP, UDP, DNS and TLS Network Troubleshooting SRE/DBRE Lab

**Python 3.11+ | Standard library only | Disposable loopback servers | No production access**

## 1. Topology
\`\`\`text
test runner -> 127.0.0.1 ephemeral TCP echo server -> framed response
            -> 127.0.0.1 ephemeral UDP echo server -> datagram response
            -> getaddrinfo("localhost", ...) -> resolver checks
            -> ssl.create_default_context() -> TLS policy checks
\`\`\`
No network scanning, packet sniffing, cloud credentials or external requests are performed. The TLS lab validates context policy, not a live TLS handshake.

## 2. Complete probe library — network_probe.py
\`\`\`python
"""Safe bounded network probes for disposable local TCP/UDP fixtures."""
from __future__ import annotations

import socket
import ssl
import struct
import time
from dataclasses import dataclass

MAX_FRAME = 4096
MAX_DATAGRAM = 1200

class ProbeError(RuntimeError):
    pass

@dataclass(frozen=True)
class ProbeResult:
    protocol: str
    received: bytes
    elapsed_ms: float

def _validate_target(host: str, port: int, timeout: float) -> None:
    if host != "127.0.0.1":
        raise ValueError("only IPv4 loopback is allowed in lab")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("invalid port")
    if type(timeout) not in (int, float) or not 0 < timeout <= 5:
        raise ValueError("invalid timeout")

def read_exact(sock: socket.socket, length: int) -> bytes:
    if type(length) is not int or not 0 <= length <= MAX_FRAME:
        raise ProbeError("invalid frame length")
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ProbeError("truncated TCP frame")
        data.extend(chunk)
    return bytes(data)

def tcp_echo(host: str, port: int, payload: bytes, *, timeout: float = 1.0) -> ProbeResult:
    _validate_target(host, port, timeout)
    if not isinstance(payload, bytes) or len(payload) > MAX_FRAME:
        raise ValueError("invalid TCP payload")
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(struct.pack("!I", len(payload)) + payload)
            length = struct.unpack("!I", read_exact(sock, 4))[0]
            result = read_exact(sock, length)
    except (OSError, TimeoutError) as exc:
        raise ProbeError("TCP transport failure") from exc
    return ProbeResult("tcp", result, (time.monotonic() - start) * 1000)

def udp_echo(host: str, port: int, payload: bytes, *, timeout: float = 1.0) -> ProbeResult:
    _validate_target(host, port, timeout)
    if not isinstance(payload, bytes) or len(payload) > MAX_DATAGRAM:
        raise ValueError("invalid UDP payload")
    start = time.monotonic()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sent = sock.sendto(payload, (host, port))
            if sent != len(payload):
                raise ProbeError("short UDP send")
            result, peer = sock.recvfrom(MAX_DATAGRAM + 1)
            if peer != (host, port) or len(result) > MAX_DATAGRAM:
                raise ProbeError("invalid UDP response")
    except (OSError, TimeoutError) as exc:
        raise ProbeError("UDP transport failure") from exc
    return ProbeResult("udp", result, (time.monotonic() - start) * 1000)

def resolve_loopback() -> list[tuple[int, str]]:
    """Resolve localhost without contacting external DNS services."""
    try:
        records = socket.getaddrinfo("localhost", 0, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ProbeError("local resolver failure") from exc
    addresses = sorted({(family, sockaddr[0]) for family, _, _, _, sockaddr in records})
    if not addresses:
        raise ProbeError("no loopback addresses")
    return addresses

def tls_client_context() -> ssl.SSLContext:
    """Create a certificate-verifying context; do not disable verification."""
    return ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
\`\`\`

## 3. Complete integration tests — test_network_probe.py
\`\`\`python
from __future__ import annotations

from contextlib import contextmanager
import socket
import ssl
import struct
from threading import Event, Thread
import time
import unittest

from network_probe import (
    MAX_FRAME, ProbeError, read_exact, resolve_loopback,
    tcp_echo, tls_client_context, udp_echo,
)

@contextmanager
def tcp_server(*, truncate=False, delay=0.0):
    ready = Event()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        listener.settimeout(1.0)
        port = listener.getsockname()[1]
        def serve():
            ready.set()
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(1.0)
                    if delay:
                        time.sleep(delay)
                    if truncate:
                        conn.sendall(struct.pack("!I", 10) + b"short")
                        return
                    length = struct.unpack("!I", read_exact(conn, 4))[0]
                    payload = read_exact(conn, length)
                    response = struct.pack("!I", len(payload)) + payload
                    # Fragment intentionally to verify exact-frame reads.
                    conn.sendall(response[:2])
                    conn.sendall(response[2:])
            except (OSError, ProbeError):
                pass
        thread = Thread(target=serve, daemon=True)
        thread.start()
        ready.wait(timeout=1)
        try:
            yield port
        finally:
            thread.join(timeout=2)

@contextmanager
def udp_server(*, drop=False):
    ready = Event()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.settimeout(1.0)
        port = sock.getsockname()[1]
        def serve():
            ready.set()
            try:
                payload, peer = sock.recvfrom(1201)
                if not drop:
                    sock.sendto(payload, peer)
            except OSError:
                pass
        thread = Thread(target=serve, daemon=True)
        thread.start()
        ready.wait(timeout=1)
        try:
            yield port
        finally:
            thread.join(timeout=2)

class TCPTests(unittest.TestCase):
    def test_tcp_echo(self):
        with tcp_server() as port:
            result = tcp_echo("127.0.0.1", port, b"postgresql-lag")
            self.assertEqual(result.protocol, "tcp")
            self.assertEqual(result.received, b"postgresql-lag")

    def test_empty_frame(self):
        with tcp_server() as port:
            self.assertEqual(tcp_echo("127.0.0.1", port, b"").received, b"")

    def test_partial_tcp_frame(self):
        with tcp_server(truncate=True) as port:
            with self.assertRaises(ProbeError):
                tcp_echo("127.0.0.1", port, b"request")

    def test_read_exact_bad_length(self):
        with socket.socket() as sock:
            for length in (-1, MAX_FRAME + 1, True):
                with self.assertRaises(ProbeError):
                    read_exact(sock, length)

    def test_invalid_target(self):
        with self.assertRaises(ValueError):
            tcp_echo("example.com", 5432, b"data")

    def test_invalid_port(self):
        with self.assertRaises(ValueError):
            tcp_echo("127.0.0.1", 0, b"data")

    def test_oversized_frame(self):
        with self.assertRaises(ValueError):
            tcp_echo("127.0.0.1", 1234, b"x" * (MAX_FRAME + 1))

    def test_connection_refused(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with self.assertRaises(ProbeError):
            tcp_echo("127.0.0.1", port, b"probe", timeout=0.1)

    def test_read_timeout(self):
        with tcp_server(delay=0.3) as port:
            with self.assertRaises(ProbeError):
                tcp_echo("127.0.0.1", port, b"probe", timeout=0.05)

class UDPTests(unittest.TestCase):
    def test_udp_echo(self):
        with udp_server() as port:
            result = udp_echo("127.0.0.1", port, b"kafka-lag")
            self.assertEqual(result.protocol, "udp")
            self.assertEqual(result.received, b"kafka-lag")

    def test_udp_empty_datagram(self):
        with udp_server() as port:
            self.assertEqual(udp_echo("127.0.0.1", port, b"").received, b"")

    def test_udp_drop_timeout(self):
        with udp_server(drop=True) as port:
            with self.assertRaises(ProbeError):
                udp_echo("127.0.0.1", port, b"probe", timeout=0.05)

    def test_udp_bad_target(self):
        with self.assertRaises(ValueError):
            udp_echo("8.8.8.8", 53, b"probe")

    def test_udp_oversized(self):
        with self.assertRaises(ValueError):
            udp_echo("127.0.0.1", 1234, b"x" * 1201)

class DNSTLSTests(unittest.TestCase):
    def test_localhost_resolves(self):
        addresses = resolve_loopback()
        self.assertTrue(addresses)
        self.assertTrue(any(address in ("127.0.0.1", "::1") for _, address in addresses))

    def test_tls_verification(self):
        context = tls_client_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_invalid_timeout(self):
        with self.assertRaises(ValueError):
            tcp_echo("127.0.0.1", 1, b"x", timeout=0)

if __name__ == "__main__":
    unittest.main()
\`\`\`

## 4. Execute
\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m compileall -q network_probe.py test_network_probe.py
python -m unittest -v test_network_probe.py
\`\`\`
Windows PowerShell: \`py -3 -m venv .venv\`, \`.venv\\Scripts\\Activate.ps1\`, \`py -m unittest -v test_network_probe.py\`. Local sockets must be permitted.

## 5. Packet-level troubleshooting exercises
Use only authorized captures in a disposable environment. Interpret the sequence:
\`\`\`text
TCP: client SYN -> server SYN-ACK -> client ACK -> application frame
RST: peer/proxy aborts connection; FIN: orderly half-close
Retransmissions: packet loss/congestion/MTU/host saturation candidates
TLS: ClientHello -> ServerHello/certificate -> validation -> encrypted traffic
UDP: datagram sent -> optional application reply; no transport acknowledgement
\`\`\`
Optional local commands (not run by the lab):
\`\`\`bash
ss -tnp
nslookup localhost
openssl version
# Linux, only if authorized:
# sudo tcpdump -i lo -nn 'tcp or udp' -c 50
\`\`\`
Never capture sensitive production payloads without approval.

## 6. CI template
\`\`\`yaml
name: chapter-075-network
on: workflow_dispatch
jobs:
  loopback:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Verify extracted source
        run: |
          test -f network_probe.py
          test -f test_network_probe.py
      - name: Local socket tests
        run: python -m unittest -v test_network_probe.py
\`\`\`
Template only. Extract Markdown source into files, pin reviewed action SHAs and enable only after validating runner permissions.

## 7. Incident drills
1. TCP echo and partial framing.
2. Early peer close/truncated frame.
3. TCP connection refused.
4. TCP read timeout.
5. Oversized TCP frame rejected.
6. UDP echo success.
7. UDP datagram drop/timeout.
8. Oversized UDP payload rejected.
9. Localhost DNS lookup.
10. IPv4/IPv6 result comparison.
11. TLS context certificate validation policy.
12. Wrong TLS hostname (conceptual extension with a certificate-backed fixture).
13. SYN/SYN-ACK absence and routing hypotheses.
14. TCP RST versus FIN interpretation.
15. Kubernetes NetworkPolicy deny scenario (runbook only).
16. Connection churn/TIME_WAIT investigation.
17. MTU/packet loss/retransmission diagnosis.
18. Safe rollback and post-incident verification.

## 8. Runbooks
**DNS:** compare resolver settings, record TTLs and addresses, verify CoreDNS or VPC DNS health and restore approved configuration.

**TCP:** inspect listener and endpoint, network policy, firewall, routing, backlog and saturation; correlate timestamps.

**UDP:** validate application acknowledgements, datagram sizes and filtering; do not assume delivery.

**TLS:** validate certificate chain, SAN, SNI and trust store; never disable verification.

**Rollback:** revert approved networking changes, rerun probes and verify application SLO.

## 9. 100-point assessment
| Category | Points |
|---|---:|
| TCP sockets, framing and timeouts | 25 |
| UDP datagrams and failure semantics | 15 |
| DNS and dual-stack troubleshooting | 15 |
| TLS trust and certificate validation | 15 |
| Integration tests and fault injection | 20 |
| Runbooks, packet diagnostics and CI | 10 |

**Pass:** 90/100 and independently executed mandatory tests. The lab does not implement a real TLS handshake or packet capture; those are explicitly documented extension exercises. Publication is not execution evidence.
