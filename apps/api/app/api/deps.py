from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cognito import verify_token
from app.auth.models import CurrentUser, PLAN_ORDER
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


async def require_publisher(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Allow publishers, distributors (publishers group) and admins."""
    if not current_user.is_publisher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Publisher access required",
        )
    return current_user


async def require_retailer(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Allow retailers and admins."""
    if not current_user.is_retailer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Retailer access required",
        )
    return current_user


async def require_distributor(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Allow distributors and admins."""
    if not current_user.is_distributor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Distributor access required",
        )
    return current_user


def require_plan(min_plan: str) -> Callable:
    """
    Dependency factory that enforces a minimum retailer plan tier.

    Usage:
        @router.get("/some-feature")
        async def my_endpoint(
            current_user: CurrentUser = Depends(require_plan("starter_api")),
            db: AsyncSession = Depends(get_db),
        ):

    Admins always pass. Non-retailer accounts (publishers, distributors) always pass
    — plan gating is retailer-specific.
    """
    async def _check(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CurrentUser:
        if current_user.is_admin:
            return current_user
        if not current_user.is_retailer:
            # Publishers and distributors are never blocked by retailer plan gates
            return current_user

        # Look up retailer plan
        from app.models.retailer import Retailer
        retailer = (
            await db.execute(
                select(Retailer).where(Retailer.cognito_sub == current_user.sub)
            )
        ).scalar_one_or_none()

        if retailer is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Retailer account not found")

        current_rank = PLAN_ORDER.get(retailer.plan, 0)
        required_rank = PLAN_ORDER.get(min_plan, 0)

        if current_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires the {min_plan.replace('_', ' ').title()} plan or above.",
                headers={"X-Required-Plan": min_plan},
            )
        return current_user

    return _check


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> CurrentUser | None:
    """Like get_current_user but returns None instead of 401 for unauthenticated requests."""
    if not credentials:
        return None
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
    except ValueError:
        return None
