"""Тесты для health check и root endpoints."""


async def test_health_check(client):
    """Тест эндпоинта /health."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "production-control"


async def test_root(client):
    """Тест корневого эндпоинта /."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Production Control API" in data["message"]
