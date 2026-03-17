import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.core.config import settings
from src.db.session import engine
from src.models.batch import Batch
from src.models.product import Product
from src.models.work_center import WorkCenter
from src.storage.minio_service import MinIOService


@celery_app.task(bind=True, max_retries=3)
def generate_batch_report(
        self,
        batch_id: int,
        format: str = "excel",
        user_email: str | None = None
):
    """
    Генерация детального отчета по партии.
    """
    try:
        async def _generate():
            async with AsyncSession(engine) as db:
                # Get batch with products
                batch_query = (
                    select(Batch)
                    .join(WorkCenter)
                    .where(Batch.id == batch_id)
                )
                batch_result = await db.execute(batch_query)
                batch = batch_result.scalar_one_or_none()

                if not batch:
                    raise ValueError(f"Batch {batch_id} not found")

                products_query = select(Product).where(Product.batch_id == batch_id)
                products_result = await db.execute(products_query)
                products = products_result.scalars().all()

                # Generate report
                with tempfile.NamedTemporaryFile(
                        suffix=f".{format}",
                        delete=False
                ) as tmp_file:
                    if format == "excel":
                        _generate_excel_report(tmp_file.name, batch, products)
                    elif format == "pdf":
                        _generate_pdf_report(tmp_file.name, batch, products)
                    else:
                        raise ValueError(f"Unsupported format: {format}")

                    # Upload to MinIO
                    minio_service = MinIOService()
                    object_name = f"batch_{batch_id}_report.{format}"
                    file_url = minio_service.upload_file(
                        bucket=settings.minio_bucket_reports,
                        file_path=tmp_file.name,
                        object_name=object_name,
                        expires_days=7
                    )

                    # Clean up temp file
                    Path(tmp_file.name).unlink()

                    return {
                        "success": True,
                        "file_url": file_url,
                        "file_name": object_name,
                        "file_size": Path(tmp_file.name).stat().st_size if Path(tmp_file.name).exists() else 0,
                        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
                    }

        return asyncio.run(_generate())

    except Exception as exc:
        self.retry(exc=exc, countdown=60)


def _generate_excel_report(file_path: str, batch, products):
    """Generate Excel report."""
    from openpyxl import Workbook

    wb = Workbook()

    # Sheet 1: Batch Info
    ws_info = wb.active
    ws_info.title = "Информация о партии"

    ws_info["A1"] = "Номер партии"
    ws_info["B1"] = batch.batch_number
    ws_info["A2"] = "Дата партии"
    ws_info["B2"] = str(batch.batch_date)
    ws_info["A3"] = "Статус"
    ws_info["B3"] = "Закрыта" if batch.is_closed else "Открыта"
    ws_info["A4"] = "Рабочий центр"
    ws_info["B4"] = batch.work_center.name if batch.work_center else "N/A"
    ws_info["A5"] = "Смена"
    ws_info["B5"] = batch.shift
    ws_info["A6"] = "Бригада"
    ws_info["B6"] = batch.team
    ws_info["A7"] = "Номенклатура"
    ws_info["B7"] = batch.nomenclature
    ws_info["A8"] = "Начало смены"
    ws_info["B8"] = str(batch.shift_start)
    ws_info["A9"] = "Окончание смены"
    ws_info["B9"] = str(batch.shift_end)

    # Sheet 2: Products
    ws_products = wb.create_sheet("Продукция")
    ws_products["A1"] = "ID"
    ws_products["B1"] = "Уникальный код"
    ws_products["C1"] = "Аггрегирована"
    ws_products["D1"] = "Дата аггрегации"

    for idx, product in enumerate(products, start=2):
        ws_products[f"A{idx}"] = product.id
        ws_products[f"B{idx}"] = product.unique_code
        ws_products[f"C{idx}"] = "Да" if product.is_aggregated else "Нет"
        ws_products[f"D{idx}"] = str(product.aggregated_at) if product.aggregated_at else "-"

    # Sheet 3: Statistics
    ws_stats = wb.create_sheet("Статистика")
    total = len(products)
    aggregated = sum(1 for p in products if p.is_aggregated)

    ws_stats["A1"] = "Всего продукции"
    ws_stats["B1"] = total
    ws_stats["A2"] = "Аггрегировано"
    ws_stats["B2"] = aggregated
    ws_stats["A3"] = "Осталось"
    ws_stats["B3"] = total - aggregated
    ws_stats["A4"] = "Процент выполнения"
    ws_stats["B4"] = f"{(aggregated / total * 100):.2f}%" if total > 0 else "0%"

    wb.save(file_path)


def _generate_pdf_report(file_path: str, batch, products):
    """Generate PDF report."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(2 * cm, height - 2 * cm, f"Отчет по партии {batch.batch_number}")

    # Batch info
    c.setFont("Helvetica", 12)
    y_pos = height - 4 * cm
    c.drawString(2 * cm, y_pos, f"Дата: {batch.batch_date}")
    y_pos -= 0.5 * cm
    c.drawString(2 * cm, y_pos, f"Рабочий центр: {batch.work_center.name if batch.work_center else 'N/A'}")
    y_pos -= 0.5 * cm
    c.drawString(2 * cm, y_pos, f"Смена: {batch.shift}")
    y_pos -= 0.5 * cm
    c.drawString(2 * cm, y_pos, f"Бригада: {batch.team}")
    y_pos -= 0.5 * cm
    c.drawString(2 * cm, y_pos, f"Номенклатура: {batch.nomenclature}")

    # Products table
    y_pos -= 1 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y_pos, "Продукция:")

    c.setFont("Helvetica", 10)
    y_pos -= 0.7 * cm
    c.drawString(2 * cm, y_pos, "Код")
    c.drawString(6 * cm, y_pos, "Статус")
    c.drawString(10 * cm, y_pos, "Дата аггрегации")

    y_pos -= 0.5 * cm
    for product in products[:50]:  # Limit to 50 products per page
        if y_pos < 2 * cm:
            c.showPage()
            y_pos = height - 2 * cm

        c.drawString(2 * cm, y_pos, product.unique_code)
        c.drawString(6 * cm, y_pos, "Аггрегирована" if product.is_aggregated else "Не аггрегирована")
        c.drawString(10 * cm, y_pos, str(product.aggregated_at) if product.aggregated_at else "-")
        y_pos -= 0.5 * cm

    c.save()
