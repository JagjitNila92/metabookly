import logging
from functools import lru_cache
import httpx
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_jwks(user_pool_id: str, region: str) -> dict:
    """Fetch and cache the Cognito JWKS for token verification."""
    url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return {key["kid"]: key for key in response.json()["keys"]}


def verify_token(token: str, user_pool_id: str, client_id: str, region: str) -> dict:
    """
    Verify a Cognito JWT and return its claims.
    Raises ValueError if the token is invalid or expired.
    """
    try:
        headers = jwt.get_unverified_headers(token)
        kid = headers["kid"]
        keys = get_jwks(user_pool_id, region)
        if kid not in keys:
            raise ValueError("Token key ID not found in Cognito JWKS")

        public_key = jwk.construct(keys[kid])
        message, encoded_sig = token.rsplit(".", 1)
        decoded_sig = base64url_decode(encoded_sig.encode())

        if not public_key.verify(message.encode(), decoded_sig):
            raise ValueError("Token signature verification failed")

        claims = jwt.get_unverified_claims(token)

        if claims.get("token_use") != "access":
            raise ValueError("Token must be an access token")

        if claims.get("client_id") != client_id:
            raise ValueError("Token client_id does not match")

        return claims

    except JWTError as e:
        raise ValueError(f"Token validation failed: {e}") from e
