"""
Integration tests for Health and Network Info HTTP REST endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify GET /api/health returns status 200 and ok status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["game"] == "Kadi Teeri"


def test_network_info_endpoint():
    """Verify GET /api/network-info returns LAN IPs, port, and hostname."""
    response = client.get("/api/network-info")
    assert response.status_code == 200
    data = response.json()
    assert "lan_ips" in data
    assert isinstance(data["lan_ips"], list)
    assert "port" in data
    assert isinstance(data["port"], int)
    assert "hostname" in data
    assert isinstance(data["hostname"], str)
