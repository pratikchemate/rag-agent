"""Pytest fixtures for unit and integration testing."""

import os
from typing import Generator, List
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Configure test environment flags before importing application modules
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_TEST_TOKENS"] = "true"

from app.core.config import get_settings  # noqa: E402
from app.db.engine import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.model_factory import set_test_model  # noqa: E402

get_settings.cache_clear()

TEST_USER_A = UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_B = UUID("00000000-0000-0000-0000-000000000002")

# Database URL pointing to local pgvector container
TEST_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
)


class MockEmbeddingService:
    """Fast deterministic embedding stub producing normalized 384-dim vectors."""

    def __init__(self):
        self.dimensions = 384

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text_content in texts:
            # Deterministic pseudo-vector based on text hash
            val = float(hash(text_content) % 100) / 100.0
            vec = [val] * self.dimensions
            results.append(vec)
        return results

    def embed_query(self, query: str) -> List[float]:
        val = float(hash(query) % 100) / 100.0
        return [val] * self.dimensions


class MockChatModel(BaseChatModel):
    """Mock LLM returning deterministic answers."""

    custom_response: str = "This is a verified test response from document [S1]."

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content=self.custom_response,
                        response_metadata={"finish_reason": "stop"},
                    )
                )
            ]
        )

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a clean, isolated database session for tests."""
    with db_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE feedback, document_chunks, documents, daily_usage_counters CASCADE;"
            )
        )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with db_engine.begin() as conn:
            conn.execute(
                text(
                    "TRUNCATE TABLE feedback, document_chunks, documents, daily_usage_counters CASCADE;"
                )
            )


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """TestClient wired with database session dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Set mock model for tests by default
    set_test_model(MockChatModel())
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    set_test_model(None)


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset sliding window in-memory rate limiters between individual tests."""
    from app.core.rate_limit import get_chat_limiter, get_upload_limiter

    get_chat_limiter().clear()
    get_upload_limiter().clear()
    yield


@pytest.fixture
def auth_headers_user_a() -> dict:
    """Authorization headers for Test User A."""
    return {"Authorization": f"Bearer test-token-{TEST_USER_A}"}


@pytest.fixture
def auth_headers_user_b() -> dict:
    """Authorization headers for Test User B."""
    return {"Authorization": f"Bearer test-token-{TEST_USER_B}"}
