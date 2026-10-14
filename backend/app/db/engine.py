"""Database engine and session management."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Configure engine with connection pooling and prepare_threshold=None for PgBouncer/Supavisor
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=3,
    max_overflow=2,
    pool_pre_ping=True,
    pool_timeout=30,
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
