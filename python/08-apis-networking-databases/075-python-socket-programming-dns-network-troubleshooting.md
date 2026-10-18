# Chapter 075 — Python Socket Programming, DNS and Network Troubleshooting

**Part 08 — APIs, Networking and Databases | Python 3.11+ | 10–14 hours**

## Objectives
Understand TCP and UDP socket lifecycles, DNS resolution, TLS handshake and certificate validation, connection and read timeouts, address families, ephemeral ports, connection failures, packet-level diagnostic reasoning and safe production incident triage. Build and test disposable local TCP/UDP services and network probes without touching production systems.

## 1. Network layers and operational context
\`\`\`text
DBRE application -> getaddrinfo DNS -> TCP/UDP socket -> routing/firewall/NAT
 -> TLS (TCP only in this chapter) -> application protocol
 -> PostgreSQL 5432 / Elasticsearch 9200 / Kafka 9092 / HTTPS 443
\`\`\`
Application timeouts can arise from DNS, routing, SYN retransmissions, TLS trust, upstream accept queues, socket reads or application overload. Do not infer a single root cause from a timeout alone.

## 2. TCP sockets
TCP is a reliable, ordered byte stream. A client creates \`socket.socket(AF_INET, SOCK_STREAM)\`, sets a finite timeout and calls \`connect\`. A server calls \`bind\`, \`listen\` and \`accept\`. TCP does not preserve message boundaries: use an explicit length prefix, delimiter or protocol framing. \`sendall\` sends all bytes or raises; \`recv\` may return fewer bytes than requested. A zero-length \`recv\` indicates peer shutdown of its sending side. Close sockets using context managers. Distinguish connection refused, timed out, reset, and remote close.

## 3. UDP sockets
UDP sends datagrams without delivery, ordering or duplicate guarantees. Use \`sendto\` and \`recvfrom\`. Datagram boundaries are preserved, but large datagrams may fragment and be dropped; use conservative payload sizes. UDP health checks need an application-level acknowledgement and must tolerate packet loss. The lab uses a local echo service and never broadcasts or scans networks.

## 4. DNS
\`socket.getaddrinfo(host, port, type=SOCK_STREAM)\` resolves candidate IPv4/IPv6 addresses and protocols. A successful lookup does not prove TCP connectivity. Resolver caches, split-horizon DNS, search domains, TTLs, stale records and IPv6/IPv4 preference can affect incidents. Avoid logging sensitive hostnames or querying untrusted hosts in the lab. \`getaddrinfo\` may block; its duration is not necessarily governed by the subsequent socket timeout. In production, measure DNS separately and consider dual-stack connection policies.

## 5. TLS
TLS authenticates the server when the client validates its certificate chain and hostname using an approved trust store. \`ssl.create_default_context()\` enables verification. Wrap a connected TCP socket with \`SSLContext.wrap_socket(..., server_hostname=hostname)\`. Never set \`CERT_NONE\` or disable hostname checks as an outage workaround. mTLS additionally authenticates clients with certificates. The executable lab checks the TLS policy configuration offline; a full certificate-backed handshake is an optional extension, not an executed test.

## 6. Timeout and retry budgets
A socket timeout is not a guaranteed end-to-end deadline across DNS, TCP, TLS and all reads. Set explicit connect/read budgets, cap response bytes and retry only operations with safe semantics. TCP reconnecting can duplicate a request whose response was lost; idempotency matters. Track retry amplification and avoid reconnect storms during outages.

## 7. Packet-level diagnostics
Understand the TCP three-way handshake (SYN, SYN-ACK, ACK), FIN versus RST, retransmissions, window/zero-window, MTU and packet loss. Interpret a missing SYN-ACK as a possible firewall, routing, server or network problem, not proof of any one cause. TLS handshake failures occur after TCP establishment. Use \`ss -tnp\`, \`netstat\`, \`dig\`/\`nslookup\`, \`openssl s_client\`, \`tcpdump\` or Wireshark only with authorized access and appropriate redaction. Packet captures can contain sensitive data; limit scope, duration and retention.

## 8. SRE/DBRE incident scenarios
1. PostgreSQL connection refused: inspect listener, Service endpoint, security groups and network policy.
2. Elasticsearch connect timeout: inspect routing, firewall and node pressure.
3. Kafka broker DNS resolution fails: inspect advertised listeners, resolver and private DNS.
4. TCP service sends a partial frame: client must read exact length.
5. TCP peer closes early: classify truncated response, never silently accept.
6. UDP echo reply is lost: timeout is expected and does not prove server failure.
7. DNS returns IPv6 before IPv4: verify dual-stack route support.
8. TLS certificate expires: fix certificate chain and trust, never bypass validation.
9. TLS hostname mismatch: verify endpoint/SNI and certificate SAN.
10. TCP RST under load: inspect process restarts, proxy resets and backlog.
11. Packet retransmissions increase: correlate RTT, drops, MTU and NIC counters.
12. High TIME_WAIT count: inspect connection churn and keepalive strategy.
13. Port exhaustion: inspect ephemeral range, connection pooling and NAT.
14. NetworkPolicy denies pod egress: validate Kubernetes policy and DNS separately.
15. DNS cache contains stale IP: verify TTL and service discovery propagation.
16. Load balancer idle timeout closes connections: configure keepalive and retry safely.

## 9. Troubleshooting matrix
| Symptom | Likely domain | First checks |
|---|---|---|
| \`gaierror\` | DNS | Resolver, records, search domains, network DNS policy |
| \`ConnectionRefusedError\` | Listener/path | Service endpoints, process, port, firewall reject |
| \`socket.timeout\` | Path/upstream | RTT, SYN retries, accept backlog, load |
| \`ConnectionResetError\` | Peer/proxy | Process restarts, proxy timeouts, packet trace |
| Empty \`recv\` | Peer shutdown | Framing and protocol lifecycle |
| TLS verification error | Trust/SNI | Certificate chain, SAN, hostname, expiry |
| UDP no response | Loss/filtering/app | Destination, firewall, server health |
| High retransmits | Network congestion | Drops, interface errors, MTU, queue |

## 10. Production runbooks
**DNS outage:** capture sanitized resolver and \`getaddrinfo\` errors, compare affected pods/nodes, validate records and DNS service health, restore resolver configuration through approved change.

**TCP connect failures:** validate endpoint and listener, trace allowed network path, check Kubernetes NetworkPolicy/cloud firewall/security groups, correlate node/service load and roll back erroneous policy.

**TLS outage:** inspect chain, SAN, SNI, trust store and certificate rotation. Restore approved certificates; never disable verification.

**Packet loss/latency:** collect authorized bounded captures and interface counters, compare retransmissions and queue pressure, escalate to networking with timestamps and affected flows.

**Rollback:** revert approved network/client configuration, rerun synthetic probes and production canaries, confirm SLO recovery and record evidence.

## 11. Hands-on lab
[Chapter 075 — TCP, UDP, DNS and TLS Diagnostics SRE/DBRE Lab](labs/075-tcp-udp-dns-tls-network-troubleshooting-sre-dbre-lab.md) includes a complete Python probe library, local TCP and UDP servers, automated integration tests, fault injection, runbooks, CI template and a 100-point assessment.

**Next proposed:** Chapter 076 — Python Database Connectivity and Connection Pooling Fundamentals.
