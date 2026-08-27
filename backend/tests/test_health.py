"""Tests for the health endpoint."""


def test_health_endpoint_returns_200(client):
    """GET /api/health should return 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_endpoint_returns_healthy_status(client):
    """GET /api/health should return status 'healthy'."""
    response = client.get("/api/health")
    data = response.json()
    assert data["status"] == "healthy"


def test_health_endpoint_returns_service_name(client):
    """GET /api/health should identify the Parakh Seva API."""
    response = client.get("/api/health")
    data = response.json()
    assert "Parakh Seva" in data["service"]


def test_health_endpoint_has_timestamp(client):
    """GET /api/health should include a timestamp."""
    response = client.get("/api/health")
    data = response.json()
    assert "timestamp" in data
    assert data["timestamp"] is not None
