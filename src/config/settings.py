"""
Application configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "evzone-ml-service"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # API Authentication
    api_key: str
    api_key_header: str = "X-API-Key"

    # Database
    database_url: str
    database_pool_size: int = 10

    # Kafka
    kafka_brokers: str = "localhost:9092"
    kafka_client_id: str = "evzone-ml-service"
    kafka_group_id: str = "ml-service-group"
    kafka_topic_charger_metrics: str = "charger.metrics"
    kafka_topic_predictions: str = "ml.predictions"

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_socket_connect_timeout: int = 5
    redis_socket_timeout: int = 5
    redis_max_connections: int = 50
    redis_retry_on_timeout: bool = True
    
    # Cache
    cache_version: str = "v1"
    cache_ttl_failure_prediction: int = 3600  # 1 hour
    cache_ttl_maintenance: int = 1800  # 30 minutes
    cache_ttl_anomaly: int = 300  # 5 minutes
    cache_enabled: bool = True

    # ML Models
    model_base_path: str = "./models"
    model_failure_predictor: str = "failure_predictor"
    model_maintenance_scheduler: str = "maintenance_scheduler"
    model_anomaly_detector: str = "anomaly_detector"

    # TensorFlow
    tf_cpp_min_log_level: str = "2"
    tf_force_gpu_allow_growth: bool = True

    # Monitoring
    prometheus_port: int = 9090
    enable_metrics: bool = True

    # Main API Integration
    main_api_url: Optional[str] = None
    main_api_key: Optional[str] = None

    # Feature Flags
    enable_predictions: bool = True
    enable_training: bool = False
    enable_batch_predictions: bool = True

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),  # Fix for model_* field warnings
    )


# Global settings instance
settings = Settings()

