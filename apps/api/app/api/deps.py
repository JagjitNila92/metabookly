from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cognito import verify_token
from app.auth.models import CurrentUser
from app.config import get_settings
from app.db.session import get_db

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    settings = get_settings()
    try:
        claims = verify_token(
            token=credentials.credentials,
            user_pool_id=settings.cognito_user_pool_id,
            client_id=settings.cognito_client_id,
            region=settings.cognito_region,
        )
        return CurrentUser(
            sub=claims["sub"],
            email=claims.get("email", ""),
            groups=claims.get("cognito:groups", []),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
