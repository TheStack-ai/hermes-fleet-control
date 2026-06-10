from __future__ import annotations

import socket
from typing import Any

DEFAULT_HOSTS = ["discord.com", "gateway-us-east1-b.discord.gg", "gateway-us-east1-c.discord.gg", "gateway-us-east1-d.discord.gg"]


def check_discord_network(hosts: list[str] | None = None, timeout: float = 3.0) -> dict[str, Any]:
    results = []
    dns_ok = True
    tcp_ok = True
    for host in hosts or DEFAULT_HOSTS:
        item = {"host": host, "dns_ok": False, "tcp_443_ok": False, "error": None}
        try:
            socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            item["dns_ok"] = True
        except Exception as exc:
            item["error"] = f"DNS {type(exc).__name__}"
            dns_ok = False
        if item["dns_ok"]:
            try:
                sock = socket.create_connection((host, 443), timeout=timeout)
                sock.close()
                item["tcp_443_ok"] = True
            except Exception as exc:
                item["error"] = f"TCP {type(exc).__name__}"
                tcp_ok = False
        else:
            tcp_ok = False
        results.append(item)
    return {"discord_dns_ok": dns_ok, "discord_tcp_ok": tcp_ok, "hosts": results}
