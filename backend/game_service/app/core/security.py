import jwt
from jwt import PyJWKClient
from app.core.config import config
from my_observability import get_logger
from fastapi import HTTPException, status

logger = get_logger(__name__)

JWKS_URL = f"{config.KEYCLOAK_URL}/realms/{config.KEYCLOAK_REALM}/protocol/openid-connect/certs"

jwks_client = PyJWKClient(
    JWKS_URL,
    cache_keys=True,
    max_cached_keys=16,
    cache_jwk_set=True,
    lifespan=3600
)

def decode_access_token(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=config.KEYCLOAK_CLIENT_ID,
        issuer=f"{config.KEYCLOAK_ISSUER}/{config.KEYCLOAK_REALM}",
        options={
            "verify_exp": True,
            "verify_iss": True
        }
    )

def authenticate_token_string(token: str) -> dict:
    try:
        return decode_access_token(token)
    except Exception as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )