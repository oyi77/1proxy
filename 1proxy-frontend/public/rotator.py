import socket
import threading
import select
import json
import urllib.request
import argparse
import sys
import time
from urllib.error import URLError

API_BASE = "http://localhost:8000"
BUFFER_SIZE = 4096


def get_proxy(api_url, filters):
    url = f"{api_url}/api/v1/proxies/random"
    query_parts = []

    if filters["protocol"]:
        query_parts.append(f"protocol={filters['protocol']}")
    if filters["country"]:
        query_parts.append(f"country_code={filters['country']}")
    if filters["anonymity"]:
        query_parts.append(f"anonymity={filters['anonymity']}")
    if filters["quality"]:
        query_parts.append(f"min_quality={filters['quality']}")
    if filters["max_latency"]:
        query_parts.append(f"max_latency={filters['max_latency']}")

    if query_parts:
        url += "?" + "&".join(query_parts)

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching proxy: {e}")
        return None


def handle_client(client_socket, filters, api_url):
    proxy_info = get_proxy(api_url, filters)

    if not proxy_info:
        client_socket.close()
        return

    try:
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.settimeout(10)
        remote_socket.connect((proxy_info["ip"], proxy_info["port"]))

        print(
            f"Tunneling via {proxy_info['protocol']}://{proxy_info['ip']}:{proxy_info['port']}"
        )

        sockets = [client_socket, remote_socket]

        while True:
            readable, _, _ = select.select(sockets, [], [], 10)
            if not readable:
                break

            for sock in readable:
                other = remote_socket if sock is client_socket else client_socket
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    return
                other.sendall(data)

    except Exception as e:
        pass
    finally:
        client_socket.close()
        if "remote_socket" in locals():
            remote_socket.close()


def start_server(port, filters, api_url):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(100)

    print(f"Local Rotator running on port {port}")
    print(f"Fetching proxies from: {api_url}")
    print(f"Filters: {filters}")

    while True:
        try:
            client, addr = server.accept()
            threading.Thread(
                target=handle_client, args=(client, filters, api_url)
            ).start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Accept error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--api", default=API_BASE)
    parser.add_argument("--protocol", help="http, socks4, socks5")
    parser.add_argument("--country", help="US, DE, etc.")
    parser.add_argument("--anonymity", help="transparent, anonymous, elite")
    parser.add_argument("--quality", type=int)
    parser.add_argument("--max-latency", type=int)

    args = parser.parse_args()

    filters = {
        "protocol": args.protocol,
        "country": args.country,
        "anonymity": args.anonymity,
        "quality": args.quality,
        "max_latency": args.max_latency,
    }

    start_server(args.port, filters, args.api)
