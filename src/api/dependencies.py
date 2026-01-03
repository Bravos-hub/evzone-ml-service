"""
API dependencies (authentication, rate limiting, etc.).
"""
from fastapi import Header, HTTPException, status
from src.config.settings import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key from header."""
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key

