"""Unit tests for authentication, test token security, and JWT verification."""

import time
from uuid import uuid4

import jwt
import pytest

from app.core.auth import verify_supabase_jwt
from app.core.config import Settings
from app.core.errors import UnauthorizedError


def test_test_token_accepted_in_test_env(monkeypatch):
    """Verify test tokens are accepted when ENVIRONMENT is 'test' and ALLOW_TEST_TOKENS is True."""
    user_id = str(uuid4())
    token = f"test-token-{user_id}"
    payload = verify_supabase_jwt(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "authenticated"


def test_test_token_rejected_in_production(monkeypatch):
    """Verify test tokens are rejected when ENVIRONMENT is 'production'."""
    settings = Settings(ENVIRONMENT="production", ALLOW_TEST_TOKENS=False)
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    with pytest.raises(UnauthorizedError, match="Test tokens are not permitted"):
        verify_supabase_jwt(f"test-token-{uuid4()}")


def test_test_token_rejected_when_flag_disabled(monkeypatch):
    """Verify test tokens are rejected when ALLOW_TEST_TOKENS is False even in test environment."""
    settings = Settings(ENVIRONMENT="test", ALLOW_TEST_TOKENS=False)
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    with pytest.raises(UnauthorizedError, match="Test tokens are not permitted"):
        verify_supabase_jwt(f"test-token-{uuid4()}")


def test_jwt_hs256_accepted_in_dev(monkeypatch):
    """Verify HS256 token signed with SUPABASE_JWT_SECRET is accepted in non-production."""
    jwt_secret = "a_secure_dev_jwt_secret_with_32_bytes_or_more"
    supabase_url = "https://demo.supabase.co"
    settings = Settings(
        ENVIRONMENT="development",
        ALLOW_TEST_TOKENS=False,
        SUPABASE_URL=supabase_url,
        SUPABASE_JWT_SECRET=jwt_secret,
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    user_id = str(uuid4())
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": user_id,
            "aud": "authenticated",
            "iss": f"{supabase_url}/auth/v1",
            "exp": now + 3600,
            "role": "authenticated",
        },
        jwt_secret,
        algorithm="HS256",
    )

    payload = verify_supabase_jwt(token)
    assert payload["sub"] == user_id
    assert payload["aud"] == "authenticated"


def test_jwt_hs256_rejected_in_production(monkeypatch):
    """Verify HS256 fallback is ignored in production mode."""
    jwt_secret = "a_secure_dev_jwt_secret_with_32_bytes_or_more"
    supabase_url = "https://demo.supabase.co"
    settings = Settings(
        ENVIRONMENT="production",
        ALLOW_TEST_TOKENS=False,
        SUPABASE_URL=supabase_url,
        SUPABASE_JWT_SECRET=jwt_secret,
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": f"{supabase_url}/auth/v1",
            "exp": now + 3600,
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError, match="Invalid or expired authentication token"):
        verify_supabase_jwt(token)


def test_jwt_wrong_issuer_rejected(monkeypatch):
    """Verify JWT from wrong issuer is rejected."""
    jwt_secret = "a_secure_dev_jwt_secret_with_32_bytes_or_more"
    settings = Settings(
        ENVIRONMENT="development",
        ALLOW_TEST_TOKENS=False,
        SUPABASE_URL="https://correct-project.supabase.co",
        SUPABASE_JWT_SECRET=jwt_secret,
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": "https://attacker-project.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError, match="Invalid or expired authentication token"):
        verify_supabase_jwt(token)


def test_jwt_expired_rejected(monkeypatch):
    """Verify expired JWT is rejected."""
    jwt_secret = "a_secure_dev_jwt_secret_with_32_bytes_or_more"
    settings = Settings(
        ENVIRONMENT="development",
        ALLOW_TEST_TOKENS=False,
        SUPABASE_URL="https://demo.supabase.co",
        SUPABASE_JWT_SECRET=jwt_secret,
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": "https://demo.supabase.co/auth/v1",
            "exp": int(time.time()) - 300,
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError, match="Invalid or expired authentication token"):
        verify_supabase_jwt(token)


def test_jwt_missing_required_claims_rejected(monkeypatch):
    """Verify JWT missing 'sub' claim is rejected."""
    jwt_secret = "a_secure_dev_jwt_secret_with_32_bytes_or_more"
    settings = Settings(
        ENVIRONMENT="development",
        ALLOW_TEST_TOKENS=False,
        SUPABASE_URL="https://demo.supabase.co",
        SUPABASE_JWT_SECRET=jwt_secret,
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    token = jwt.encode(
        {
            "aud": "authenticated",
            "iss": "https://demo.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError, match="Invalid or expired authentication token"):
        verify_supabase_jwt(token)


def test_jwt_wrong_audience_rejected(monkeypatch):
    """Verify JWT with incorrect audience is rejected."""
    jwt_secret = "a_secure_dev_jwt_secret_with_32_bytes_or_more"
    settings = Settings(
        ENVIRONMENT="development",
        ALLOW_TEST_TOKENS=False,
        SUPABASE_URL="https://demo.supabase.co",
        SUPABASE_JWT_SECRET=jwt_secret,
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "wrong_audience",
            "iss": "https://demo.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError, match="Invalid or expired authentication token"):
        verify_supabase_jwt(token)
