from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings


@lru_cache(maxsize=1)
def _engine():
    return create_engine(
        settings.POSTGRES_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


@lru_cache(maxsize=1)
def _session_factory():
    return sessionmaker(
        bind=_engine(),
        autocommit=False,
        autoflush=False,
    )


def create_session() -> Session:
    return _session_factory()()


def get_db() -> Generator[Session, None, None]:
    db = create_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
