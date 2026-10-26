"""Database engine and session helpers.

Works with TiDB Cloud (MySQL protocol, TLS required) and with SQLite for tests.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    url = url or settings.database_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("mysql"):
        import certifi

        # TiDB Cloud serverless requires TLS; certifi's CA bundle validates it.
        kwargs["connect_args"] = {"ssl": {"ca": certifi.where()}}
        kwargs["pool_recycle"] = 280
    elif url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(eng=None) -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(eng or engine)


def get_session():
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
