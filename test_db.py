import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    engine = create_async_engine(
        'postgresql+asyncpg://postgres:postgres@localhost:5434/production_control'
    )
    async with engine.connect() as conn:
        print('✅ Connection successful!')
    await engine.dispose()

asyncio.run(test())