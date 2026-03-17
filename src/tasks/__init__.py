from src.celery_app import celery_app


@celery_app.task
def aggregate_products_batch(batch_id: int, unique_codes: list[str], user_id: int | None = None):
    return {"success": True, "total": len(unique_codes), "aggregated": len(unique_codes), "failed": 0, "errors": []}

@celery_app.task
def generate_batch_report(batch_id: int, format: str = "excel", user_email: str | None = None):
    return {"success": True, "file_url": "http://localhost:9000/reports/demo.xlsx", "file_name": "demo.xlsx", "file_size": 1024, "expires_at": "2024-02-07T00:00:00Z"}

@celery_app.task
def import_batches_from_file(file_url: str, user_id: int):
    return {"success": True, "total_rows": 10, "created": 10, "skipped": 0, "errors": []}

@celery_app.task
def export_batches_to_file(filters: dict, format: str = "excel"):
    return {"success": True, "file_url": "http://localhost:9000/exports/demo.xlsx", "total_batches": 5}

@celery_app.task
def auto_close_expired_batches():
    return {"success": True, "closed_count": 0}

@celery_app.task
def cleanup_old_files():
    return {"success": True, "deleted_count": 0}

@celery_app.task
def update_cached_statistics():
    return {"success": True}

@celery_app.task
def retry_failed_webhooks():
    return {"success": True, "retry_count": 0}
