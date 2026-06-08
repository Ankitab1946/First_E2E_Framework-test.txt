from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=8)
def create_db_engine():
    """Create and reuse SQLAlchemy engines instead of rebuilding them per query.

    Engine creation is expensive for SQL Server/pyodbc. Caching it keeps the
    connection pool warm and significantly improves Streamlit rerun latency.
    """
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        fast_executemany=True,
    )


@lru_cache(maxsize=8)
def get_session_factory():
    engine = create_db_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def reset_database_cache() -> None:
    """Clear cached engine/session factory after environment or DB config changes."""
    get_session_factory.cache_clear()
    create_db_engine.cache_clear()
