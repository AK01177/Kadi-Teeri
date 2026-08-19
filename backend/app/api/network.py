"""
HTTP REST endpoint for network discovery and local network multiplayer.
"""

from __future__ import annotations

import platform
import socket
import subprocess

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["Network"])


class NetworkInfoResponse(BaseModel):
    """LAN IP addresses and host configuration for local network play."""

    lan_ips: list[str]
    port: int
    hostname: str


@router.get("/api/network-info", response_model=NetworkInfoResponse)
async def get_network_info():
    """Return local LAN IP addresses for direct network connections."""
    lan_ips: set[str] = set()
    hostname = socket.gethostname()

    # 1. Try standard getaddrinfo
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                lan_ips.add(ip)
    except Exception:
        pass

    # 2. Try dummy UDP connections
    dummy_ips = ["8.8.8.8", "192.168.1.1", "10.0.0.1", "172.16.0.1", "192.168.43.1"]
    for test_ip in dummy_ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect((test_ip, 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                lan_ips.add(ip)
            s.close()
        except Exception:
            pass

    # 3. Try hostname -I on POSIX
    if platform.system() != "Windows":
        try:
            output = subprocess.check_output(["hostname", "-I"], stderr=subprocess.DEVNULL).decode("utf-8")
            for ip in output.split():
                if ip and not ip.startswith("127."):
                    lan_ips.add(ip)
        except Exception:
            pass

    return NetworkInfoResponse(
        lan_ips=list(lan_ips),
        port=settings.port,
        hostname=hostname,
    )
