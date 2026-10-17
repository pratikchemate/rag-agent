"""Authentication and token verification with Supabase JWKS support."""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

import jwt
from fastapi import Header
from jwt import PyJWKClient

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cached JWKS client
_jwk_client: Optional[PyJWKClient] = None
_jwk_client_url: Optional[str] = None


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user derived from verified JWT claims."""

    user_id: UUID
    email: Optional[str] = None
    role: str = "authenticated"


def get_jwk_client(supabase_url: str) -> PyJWKClient:
    """Return or initialize cached PyJWKClient."""
    global _jwk_client, _jwk_client_url
    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    if _jwk_client is None or _jwk_client_url != jwks_url:
        _jwk_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
        _jwk_client_url = jwks_url
    return _jwk_client


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Verify Supabase JWT signature and claims using JWKS or dev secret."""
    settings = get_settings()

    # 1. Test token path: strictly restricted to ENVIRONMENT == "test" and ALLOW_TEST_TOKENS is True
    if token.startswith("test-token-"):
        if settings.ENVIRONMENT == "test" and settings.ALLOW_TEST_TOKENS:
            user_part = token.replace("test-token-", "")
            try:
                user_uuid = str(UUID(user_part))
            except ValueError:
                user_uuid = "00000000-0000-0000-0000-000000000001"
            return {
                "sub": user_uuid,
                "email": f"test-{user_part[:8]}@example.com",
                "role": "authenticated",
                "aud": "authenticated",
            }
        logger.warning(
            f"Rejected unsigned test token in unauthorized environment: "
            f"ENVIRONMENT='{settings.ENVIRONMENT}', ALLOW_TEST_TOKENS={settings.ALLOW_TEST_TOKENS}"
        )
        raise UnauthorizedError("Test tokens are not permitted in this environment")

    # 2. HS256 fallback with dedicated SUPABASE_JWT_SECRET (non-production only)
    jwt_secret = settings.get_supabase_jwt_secret()
    if jwt_secret and settings.ENVIRONMENT != "production":
        expected_issuer = (
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1" if settings.SUPABASE_URL else None
        )
        decode_options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": True,
            "require": ["exp", "sub", "aud"],
        }
        if expected_issuer:
            decode_options["verify_iss"] = True
        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                issuer=expected_issuer,
                options=decode_options,
            )
            return payload
        except Exception as hs_err:
            if not settings.SUPABASE_URL:
                logger.warning(f"HS256 JWT verification failed: {str(hs_err)}")
                raise UnauthorizedError("Invalid or expired authentication token")

    # 3. Asymmetric JWKS Verification
    if settings.SUPABASE_URL:
        expected_issuer = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"
        try:
            jwk_client = get_jwk_client(settings.SUPABASE_URL)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience="authenticated",
                issuer=expected_issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "sub", "aud"],
                },
            )
            return payload
        except Exception as jwks_err:
            logger.warning(f"JWT verification failed: {str(jwks_err)}")
            raise UnauthorizedError("Invalid or expired authentication token")

    raise UnauthorizedError("Authentication provider not configured")


ANONYMOUS_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """Dependency for securing endpoints and extracting verified owner_id."""
    if not authorization or not authorization.strip():
        raise UnauthorizedError("Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Invalid Authorization header format. Expected 'Bearer <token>'")

    token = parts[1]
    if token.lower() in ("undefined", "null", ""):
        raise UnauthorizedError("Missing or invalid Authorization token")

    payload = verify_supabase_jwt(token)

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Token missing subject claim")

    try:
        user_id = UUID(str(sub))
    except ValueError:
        raise UnauthorizedError("Token subject is not a valid UUID")

    return AuthenticatedUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


def get_current_user_optional(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """Dependency extracting verified user if Authorization header is provided, or returning anonymous demo user."""
    if not authorization or not authorization.strip():
        return AuthenticatedUser(
            user_id=ANONYMOUS_USER_ID,
            email=None,
            role="anonymous",
        )

    parts = authorization.split()
    if len(parts) == 2 and parts[1].lower() in ("undefined", "null", ""):
        return AuthenticatedUser(
            user_id=ANONYMOUS_USER_ID,
            email=None,
            role="anonymous",
        )

    return get_current_user(authorization=authorization)
