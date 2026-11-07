"""Network reachability probe for the swarm. Stdlib only, no model needed.

  python probe.py -serve [port]        master machine: listen, print your IP
  python probe.py <master-ip> [port]   other machine: classify reachability

It tells apart the ways a network blocks two machines, from the TCP error:
  REACHABLE    the swarm will work
  PORT CLOSED  host reached, nothing listening (master down / wrong IP / reject)
  FILTERED     SYN dropped; ping decides firewall-on-master vs campus isolation
  NO ROUTE     not on the same network, or wrong IP
"""
import http.server
import socket
import subprocess
import sys

PORT = 8765


def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()


def serve(port):
    print(f"listening on 0.0.0.0:{port}  --  from another machine run:  "
          f"nettest.bat {my_ip()} {port}")
    print("(allow the Windows Firewall prompt if one appears; Ctrl+C to stop)")
    http.server.HTTPServer(("0.0.0.0", port),
                           http.server.SimpleHTTPRequestHandler).serve_forever()


def host_answers_ping(host):
    try:
        r = subprocess.run(["ping", "-n", "1", "-w", "1500", host],
                           capture_output=True, text=True)
    except OSError:
        return False
    return r.returncode == 0 and "TTL=" in r.stdout.upper()


def probe(host, port):
    print(f"testing {host}:{port} ...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((host, port))
        print("REACHABLE -- the swarm will work on this network.")
        return 0
    except ConnectionRefusedError:
        print(f"PORT CLOSED -- reached the master host, but nothing is listening "
              f"on {port}.\n"
              "  The master is not running, its firewall is set to REJECT, or the "
              "IP is wrong.\n"
              "  Fix: run `start.bat -master` on that machine, then retry.")
        return 1
    except (socket.timeout, TimeoutError):
        if host_answers_ping(host):
            print(f"FILTERED, host is UP -- it answers ping but drops port {port}.\n"
                  "  This is the MASTER'S WINDOWS FIREWALL. On the master, run:\n"
                  f'  netsh advfirewall firewall add rule name="swarm" dir=in '
                  f"action=allow protocol=TCP localport={port}\n"
                  "  then retry from here.")
        else:
            print(f"FILTERED, host is SILENT -- no answer on port {port} or to ping.\n"
                  "  Likely CAMPUS CLIENT-ISOLATION: devices on this wifi cannot reach\n"
                  "  each other. To be sure, add the firewall rule on the master (see\n"
                  "  the master's-firewall case) and retry: if it flips to REACHABLE it\n"
                  "  was the firewall; if still FILTERED it is isolation.\n"
                  "  Isolation fix: use a phone hotspot or a travel router.")
        return 1
    except OSError as e:
        print(f"NO ROUTE -- cannot reach {host} ({e}).\n"
              "  Wrong IP, or this machine is not on the same network as the master.")
        return 1
    finally:
        s.close()


def main(argv):
    if not argv:
        print("Usage:  python probe.py -serve [port]   OR   "
              "python probe.py <master-ip> [port]")
        return 1
    port = int(argv[1]) if len(argv) > 1 else PORT
    if argv[0].lower() == "-serve":
        serve(port)
        return 0
    return probe(argv[0], port)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
