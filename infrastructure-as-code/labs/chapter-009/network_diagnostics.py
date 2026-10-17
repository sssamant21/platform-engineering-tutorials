"""Read-only DNS and TLS diagnostics for an approved registry hostname."""
import socket
import ssl
import sys

def valid_host(host):
    return isinstance(host, str) and bool(host) and len(host) <= 253 and all(part and len(part) <= 63 and all(c.isalnum() or c == "-" for c in part) and not part.startswith("-") and not part.endswith("-") for part in host.split("."))

def diagnose(host, resolver=socket.getaddrinfo, connector=socket.create_connection, context_factory=ssl.create_default_context):
    if not valid_host(host):
        return False, "invalid hostname"
    try:
        addresses = resolver(host, 443, type=socket.SOCK_STREAM)
        ips = sorted({item[4][0] for item in addresses})
        print(f"DNS OK: {host} -> {', '.join(ips[:5])}")
        with connector((host, 443), timeout=5) as sock:
            with context_factory().wrap_socket(sock, server_hostname=host) as tls:
                print(f"TLS OK: {tls.version()} certificate verified")
        return True, "DNS/TLS succeeded"
    except (OSError, ssl.SSLError) as exc:
        return False, f"{type(exc).__name__}: {exc}"

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 network_diagnostics.py registry.terraform.io")
        return 1
    ok, message = diagnose(argv[1])
    print(("PASS: " if ok else "FAIL: ") + message)
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
