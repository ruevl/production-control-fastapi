"""Интеграционные тесты полного потока работы с партией."""


async def test_full_batch_lifecycle(client, db_session):
    """
    Тест полного цикла:
    1. Создать Work Center
    2. Создать Batch
    3. Получить Batch по ID
    4. Обновить Batch
    5. Закрыть Batch
    """
    # 1. Создаём рабочий центр
    wc_response = await client.post(
        "/api/v1/work-centers",
        json={
            "identifier": "WC_INTEGRATION_001",
            "name": "Интеграционный тест"
        }
    )
    assert wc_response.status_code == 201
    wc = wc_response.json()

    # 2. Создаём партию
    batch_payload = {
        "ПредставлениеЗаданияНаСмену": "Тестовое задание",
        "ИдентификаторРЦ": "WC_INTEGRATION_001",
        "Смена": "День",
        "Бригада": "Бригада-1",
        "НомерПартии": 9999,
        "ДатаПартии": "2024-01-15",
        "Номенклатура": "Тест-продукт",
        "КодЕКН": "TEST-001",
        "ДатаВремяНачалаСмены": "2024-01-15T08:00:00",
        "ДатаВремяОкончанияСмены": "2024-01-15T20:00:00"
    }

    batch_response = await client.post("/api/v1/batches", json=[batch_payload])
    assert batch_response.status_code == 201
    batch = batch_response.json()[0]
    assert batch["batch_number"] == 9999
    assert not batch["is_closed"]

    # 3. Получаем партию по ID
    get_response = await client.get(f"/api/v1/batches/{batch['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == batch["id"]

    # 4. Обновляем партию
    update_response = await client.patch(
        f"/api/v1/batches/{batch['id']}",
        json={"task_description": "Обновлённое задание"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["task_description"] == "Обновлённое задание"

    # 5. Закрываем партию
    close_response = await client.patch(
        f"/api/v1/batches/{batch['id']}",
        json={"is_closed": True}
    )
    assert close_response.status_code == 200
    assert close_response.json()["is_closed"] is True
    assert close_response.json()["closed_at"] is not None
