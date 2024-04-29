from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status

from common.config import env_settings

# Constants for messages
UNAUTHORIZED_DETAIL = "Bearer token missing or unknown"

# We will handle a missing token ourselves
bearer_scheme = HTTPBearer(auto_error=False)


async def get_token(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    # Simulate a database query to find a known token
    if auth is None or auth.credentials not in env_settings.SERVICE_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED_DETAIL,
        )
    return auth.credentials
