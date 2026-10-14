"""Configuration settings for Enterprise Knowledge AI."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General Environment
    ENVIRONMENT: str = "production"
    ALLOW_TEST_TOKENS: bool = False
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # OpenRouter Inference Settings
    OPENROUTER_API_KEY: SecretStr = Field(default=SecretStr(""), description="OpenRouter API Key")
    OPENROUTER_MODELS: str = Field(
        default="google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free,nvidia/nemotron-3.5-lightning:free,liquid/lfm-2.5-2.6b:free",
        description="Comma-separated allowlist of OpenRouter free models",
    )
    OPENROUTER_APP_TITLE: str = "Enterprise Knowledge AI"
    OPENROUTER_APP_URL: str = "http://localhost:5173"
    OPENROUTER_TIMEOUT_SECONDS: float = 45.0
    OPENROUTER_MAX_RETRIES: int = 1
    OPENROUTER_REASONING_EFFORT: str = "low"
    ALLOW_PAID_MODEL: bool = False

    # Shared Free-Tier LLM Quota
    LLM_DAILY_REQUEST_BUDGET: int = 40

    # Supabase & Database
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: SecretStr = Field(default=SecretStr(""), description="Supabase Secret Key")
    SUPABASE_JWT_SECRET: Optional[SecretStr] = Field(
        default=None, description="Optional Supabase legacy HS256 JWT secret for non-production"
    )
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    SIGNUP_MODE: str = "invite"  # 'invite' or 'open'

    # Local Embeddings & Chunking
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSIONS: int = 384
    EMBEDDING_BATCH_SIZE: int = 16
    EMBEDDING_THREADS: int = 1
    EMBEDDING_CACHE_DIR: str = ".fastembed_cache"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200

    # Retrieval & RRF
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_CANDIDATE_K: int = 20
    RRF_K: int = 60
    ENABLE_QUERY_REWRITE: bool = True
    MAX_RETRIEVAL_ATTEMPTS: int = 2
    MIN_RETRIEVAL_SIMILARITY: float = 0.50
    EVIDENCE_LOW_KW_THRESHOLD: float = 0.15
    EVIDENCE_LOW_KW_MIN_SIMILARITY: float = 0.72
    EVIDENCE_SUBCRITICAL_SIMILARITY: float = 0.63
    EVIDENCE_SUBCRITICAL_MIN_KW: float = 0.50
    EVIDENCE_SCORE_GAP_CEILING: float = 0.65
    EVIDENCE_SCORE_GAP_MIN: float = 0.05
    EVIDENCE_VECTOR_ONLY_MIN_SIMILARITY: float = 0.65
    EVIDENCE_KEYWORD_ONLY_MIN_SCORE: float = 0.45
    MAX_OUTPUT_TOKENS: int = 700

    # Request Bounds & Safety
    MAX_UPLOAD_MB: int = 5
    MAX_DOCUMENTS_PER_USER: int = 25
    MAX_CHUNKS_PER_DOCUMENT: int = 300
    MAX_QUESTION_LENGTH: int = 2000
    MAX_CONTEXT_CHARS: int = 16000
    CHAT_RATE_LIMIT_PER_MINUTE: int = 10
    UPLOAD_RATE_LIMIT_PER_MINUTE: int = 3

    # CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Supabase Storage Bucket
    SUPABASE_STORAGE_BUCKET: str = "source-documents"
    STORAGE_LOCAL_FALLBACK_DIR: str = "/tmp/.storage_cache"

    @model_validator(mode="after")
    def validate_environment_and_security(self) -> "Settings":
        """Verify environment settings and guardrails."""
        valid_envs = {"development", "test", "production"}
        if self.ENVIRONMENT not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of {valid_envs}, got '{self.ENVIRONMENT}'")
        if self.ALLOW_TEST_TOKENS and self.ENVIRONMENT != "test":
            raise ValueError(
                f"ALLOW_TEST_TOKENS is only permitted when ENVIRONMENT is 'test'. Got ENVIRONMENT='{self.ENVIRONMENT}'"
            )
        return self

    @model_validator(mode="after")
    def validate_numeric_bounds(self) -> "Settings":
        """Verify numeric configuration bounds."""
        if self.CHUNK_SIZE <= 0:
            raise ValueError("CHUNK_SIZE must be greater than 0")
        if self.CHUNK_OVERLAP < 0 or self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be non-negative and less than CHUNK_SIZE")
        if self.RETRIEVAL_TOP_K < 1:
            raise ValueError("RETRIEVAL_TOP_K must be at least 1")
        if self.RETRIEVAL_CANDIDATE_K < self.RETRIEVAL_TOP_K:
            raise ValueError(
                "RETRIEVAL_CANDIDATE_K must be greater than or equal to RETRIEVAL_TOP_K"
            )
        if self.LLM_DAILY_REQUEST_BUDGET <= 0:
            raise ValueError("LLM_DAILY_REQUEST_BUDGET must be greater than 0")
        if self.MAX_UPLOAD_MB <= 0:
            raise ValueError("MAX_UPLOAD_MB must be greater than 0")
        if self.MAX_DOCUMENTS_PER_USER <= 0:
            raise ValueError("MAX_DOCUMENTS_PER_USER must be greater than 0")
        if self.MAX_CHUNKS_PER_DOCUMENT <= 0:
            raise ValueError("MAX_CHUNKS_PER_DOCUMENT must be greater than 0")
        if self.MAX_QUESTION_LENGTH <= 0:
            raise ValueError("MAX_QUESTION_LENGTH must be greater than 0")
        if self.MAX_RETRIEVAL_ATTEMPTS < 1:
            raise ValueError("MAX_RETRIEVAL_ATTEMPTS must be at least 1")
        evidence_threshold_keys = [
            "MIN_RETRIEVAL_SIMILARITY",
            "EVIDENCE_LOW_KW_THRESHOLD",
            "EVIDENCE_LOW_KW_MIN_SIMILARITY",
            "EVIDENCE_SUBCRITICAL_SIMILARITY",
            "EVIDENCE_SUBCRITICAL_MIN_KW",
            "EVIDENCE_SCORE_GAP_CEILING",
            "EVIDENCE_SCORE_GAP_MIN",
            "EVIDENCE_VECTOR_ONLY_MIN_SIMILARITY",
            "EVIDENCE_KEYWORD_ONLY_MIN_SCORE",
        ]
        for key in evidence_threshold_keys:
            val = getattr(self, key)
            if val < 0.0 or val > 1.0:
                raise ValueError(f"{key} must be between 0.0 and 1.0, got {val}")
        return self

    @model_validator(mode="after")
    def validate_free_models(self) -> "Settings":
        """Verify that all models in allowlist end in :free unless ALLOW_PAID_MODEL is True."""
        if not self.ALLOW_PAID_MODEL:
            models = self.get_model_allowlist()
            if not models:
                raise ValueError("OPENROUTER_MODELS must contain at least one model ID.")
            for model in models:
                if not model.endswith(":free"):
                    raise ValueError(
                        f"Non-free model '{model}' is not permitted because ALLOW_PAID_MODEL is False. "
                        "All configured models must end in ':free'."
                    )
        return self

    def get_model_allowlist(self) -> List[str]:
        """Return parsed list of model identifiers."""
        return [m.strip() for m in self.OPENROUTER_MODELS.split(",") if m.strip()]

    def get_cors_origins(self) -> List[str]:
        """Return parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    def get_openrouter_api_key(self) -> str:
        """Return raw OpenRouter API key string."""
        return self.OPENROUTER_API_KEY.get_secret_value()

    def get_supabase_secret_key(self) -> str:
        """Return raw Supabase secret key string."""
        return self.SUPABASE_SECRET_KEY.get_secret_value()

    def get_supabase_jwt_secret(self) -> Optional[str]:
        """Return raw Supabase JWT secret string if configured."""
        return self.SUPABASE_JWT_SECRET.get_secret_value() if self.SUPABASE_JWT_SECRET else None


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
