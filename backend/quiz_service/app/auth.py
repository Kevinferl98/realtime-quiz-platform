from fastapi import Header, HTTPException
import jwt
from jwt import PyJWKClient
from app.core.config import config

JWKS_URL = f"{config.KEYCLOAK_URL}/realms/{config.KEYCLOAK_REALM}/protocol/openid-connect/certs"

jwks_client = PyJWKClient(JWKS_URL)

def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token missing")
    
    token = authorization.replace("Bearer ", "")

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
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

        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")