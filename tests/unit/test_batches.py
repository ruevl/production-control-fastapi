"""Тесты для Batch API."""


async def test_create_work_center_first(client, db_session):
    """Сначала создаём рабочий центр, потом партию."""
    # Создаём Work Center
    wc_response = await client.post(
        "/api/v1/work-centers",
        json={
            "identifier": "WC_TEST_001",
            "name": "Тестовый рабочий центр"
        }
    )
    assert wc_response.status_code == 201
    wc_data = wc_response.json()
    assert wc_data["identifier"] == "WC_TEST_001"


async def test_list_batches_empty(client):
    """Тест списка партий когда их нет."""
    response = await client.get("/api/v1/batches")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
