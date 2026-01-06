"""
API dependencies (authentication, rate limiting, etc.).
"""
from typing import Optional
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


async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(default=None, alias=settings.tenant_header),
) -> Optional[str]:
    """Get tenant identifier from request headers."""
    return x_tenant_id
