"""
Database initialization script.
"""
import asyncio
import logging
from src.database.connection import engine, Base
# Import models to register them with Base
from src.database.models import ChargerMetrics, Prediction, ModelMetadata

logger = logging.getLogger(__name__)

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        logger.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())
