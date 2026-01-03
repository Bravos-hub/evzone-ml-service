"""
Logging configuration.
"""
import logging
import sys
from src.config.settings import settings


def setup_logging():
    """Setup application logging."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    logger = logging.getLogger(settings.app_name)
    return logger

