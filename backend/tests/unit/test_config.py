"""Unit tests for configuration validation and free-tier enforcement."""

import pytest

from app.core.config import Settings


def test_free_model_validation_success():
    """Verify that settings accept allowlist of models ending in :free."""
    settings = Settings(
        OPENROUTER_MODELS="google/gemma-4-31b-it:free,liquid/lfm-2.5-2.6b:free",
        ALLOW_PAID_MODEL=False,
    )
    assert len(settings.get_model_allowlist()) == 2
    assert settings.get_model_allowlist()[0] == "google/gemma-4-31b-it:free"


def test_paid_model_rejected_by_default():
    """Verify that any non-:free model raises ValueError when ALLOW_PAID_MODEL is False."""
    with pytest.raises(ValueError, match="Non-free model 'openai/gpt-4o' is not permitted"):
        Settings(
            OPENROUTER_MODELS="openai/gpt-4o,google/gemma-4-31b-it:free",
            ALLOW_PAID_MODEL=False,
        )


def test_paid_model_allowed_when_flag_enabled():
    """Verify that paid models are accepted only if explicitly permitted by developer override."""
    settings = Settings(
        OPENROUTER_MODELS="openai/gpt-4o",
        ALLOW_PAID_MODEL=True,
    )
    assert settings.get_model_allowlist() == ["openai/gpt-4o"]


def test_empty_models_rejected():
    """Verify that empty model string is rejected."""
    with pytest.raises(ValueError, match="OPENROUTER_MODELS must contain at least one model ID"):
        Settings(
            OPENROUTER_MODELS="",
            ALLOW_PAID_MODEL=False,
        )


def test_cors_origins_parsing():
    """Verify parsing of comma-separated CORS origins."""
    settings = Settings(CORS_ALLOWED_ORIGINS="http://localhost:5173, https://demo.example.com")
    origins = settings.get_cors_origins()
    assert origins == ["http://localhost:5173", "https://demo.example.com"]


def test_invalid_environment_rejected():
    """Verify that unknown environments are rejected."""
    with pytest.raises(ValueError, match="ENVIRONMENT must be one of"):
        Settings(ENVIRONMENT="staging")


def test_allow_test_tokens_prohibited_outside_test_environment():
    """Verify that ALLOW_TEST_TOKENS raises if ENVIRONMENT is not 'test'."""
    with pytest.raises(
        ValueError, match="ALLOW_TEST_TOKENS is only permitted when ENVIRONMENT is 'test'"
    ):
        Settings(ENVIRONMENT="production", ALLOW_TEST_TOKENS=True)

    with pytest.raises(
        ValueError, match="ALLOW_TEST_TOKENS is only permitted when ENVIRONMENT is 'test'"
    ):
        Settings(ENVIRONMENT="development", ALLOW_TEST_TOKENS=True)


def test_allow_test_tokens_permitted_in_test_environment():
    """Verify that ALLOW_TEST_TOKENS succeeds when ENVIRONMENT is 'test'."""
    settings = Settings(ENVIRONMENT="test", ALLOW_TEST_TOKENS=True)
    assert settings.ALLOW_TEST_TOKENS is True
    assert settings.ENVIRONMENT == "test"


def test_numeric_bounds_validation():
    """Verify range checks on numerical configuration."""
    with pytest.raises(ValueError, match="CHUNK_SIZE must be greater than 0"):
        Settings(CHUNK_SIZE=-10)

    with pytest.raises(
        ValueError, match="CHUNK_OVERLAP must be non-negative and less than CHUNK_SIZE"
    ):
        Settings(CHUNK_SIZE=100, CHUNK_OVERLAP=150)

    with pytest.raises(ValueError, match="RETRIEVAL_TOP_K must be at least 1"):
        Settings(RETRIEVAL_TOP_K=0)

    with pytest.raises(
        ValueError, match="RETRIEVAL_CANDIDATE_K must be greater than or equal to RETRIEVAL_TOP_K"
    ):
        Settings(RETRIEVAL_TOP_K=10, RETRIEVAL_CANDIDATE_K=5)

    with pytest.raises(ValueError, match="MIN_RETRIEVAL_SIMILARITY must be between 0.0 and 1.0"):
        Settings(MIN_RETRIEVAL_SIMILARITY=1.5)

    with pytest.raises(ValueError, match="EVIDENCE_LOW_KW_THRESHOLD must be between 0.0 and 1.0"):
        Settings(EVIDENCE_LOW_KW_THRESHOLD=-0.1)

    with pytest.raises(
        ValueError, match="EVIDENCE_LOW_KW_MIN_SIMILARITY must be between 0.0 and 1.0"
    ):
        Settings(EVIDENCE_LOW_KW_MIN_SIMILARITY=1.1)

    with pytest.raises(
        ValueError, match="EVIDENCE_SUBCRITICAL_SIMILARITY must be between 0.0 and 1.0"
    ):
        Settings(EVIDENCE_SUBCRITICAL_SIMILARITY=2.0)

    with pytest.raises(ValueError, match="EVIDENCE_SUBCRITICAL_MIN_KW must be between 0.0 and 1.0"):
        Settings(EVIDENCE_SUBCRITICAL_MIN_KW=-0.5)

    with pytest.raises(ValueError, match="EVIDENCE_SCORE_GAP_CEILING must be between 0.0 and 1.0"):
        Settings(EVIDENCE_SCORE_GAP_CEILING=1.2)

    with pytest.raises(ValueError, match="EVIDENCE_SCORE_GAP_MIN must be between 0.0 and 1.0"):
        Settings(EVIDENCE_SCORE_GAP_MIN=-0.01)


def test_secrets_are_masked():
    """Verify that secret fields are masked in string/repr output."""
    settings = Settings(
        OPENROUTER_API_KEY="sk-or-v1-secret12345",
        SUPABASE_SECRET_KEY="sb-secret-key-67890",
        SUPABASE_JWT_SECRET="jwt-super-secret",
    )
    assert "sk-or-v1-secret12345" not in repr(settings)
    assert "sb-secret-key-67890" not in repr(settings)
    assert "jwt-super-secret" not in repr(settings)
    assert settings.get_openrouter_api_key() == "sk-or-v1-secret12345"
    assert settings.get_supabase_secret_key() == "sb-secret-key-67890"
    assert settings.get_supabase_jwt_secret() == "jwt-super-secret"
