"""
FastAPI application entry point for EVzone ML Service.
"""
import os
import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import settings
from src.api.routes import predictions, health, models
from src.utils.logging import setup_logging
from src.services.data_collector import DataCollector
from src.services.feature_extractor import FeatureExtractor
from src.services.model_manager import ModelManager
from src.services.prediction_service import PredictionService
from src.kafka.consumer import KafkaConsumer
from src.kafka.producer import KafkaProducer

# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Initialize Redis cache
    from src.services.cache_service import CacheService
    await CacheService.initialize()

    # Initialize Kafka Producer
    await KafkaProducer.get_instance().start()

    consumer_task = None
    kafka_consumer = None
    if settings.enable_kafka_consumer:
        model_manager = ModelManager.get_instance()
        cache_service = CacheService()
        feature_extractor = FeatureExtractor()
        prediction_service = PredictionService(model_manager, feature_extractor, cache_service)
        data_collector = DataCollector()
        kafka_consumer = KafkaConsumer(data_collector, prediction_service)
        consumer_task = asyncio.create_task(kafka_consumer.start())

    yield
    
    # Shutdown
    logger.info("Shutting down ML service")
    if kafka_consumer:
        await kafka_consumer.stop()
    if consumer_task:
        consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await consumer_task

    await KafkaProducer.get_instance().stop()
    await CacheService.close()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ML Service for EVzone Platform - Predictive Maintenance",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(predictions.router, prefix="/api/v1", tags=["Predictions"])
app.include_router(models.router, prefix="/api/v1", tags=["Models"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc) if settings.debug else None},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
