# Production Control System

Система контроля заданий на выпуск продукции.

## Стек

- Python 3.11+, FastAPI
- SQLAlchemy 2.0+ (async)
- PostgreSQL 16
- Celery 5.3+ with RabbitMQ
- Redis 7+
- MinIO (S3-compatible)
- Docker & Docker Compose

## Быстрый старт

1. poetry install
2. cp .env.example .env
3. docker-compose up -d
4. poetry run alembic upgrade head
5. poetry run uvicorn src.main:app --reload

## API Документация

- Swagger: http://localhost:8000/docs
