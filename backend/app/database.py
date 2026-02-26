from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_async_session = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.config import settings
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def _get_session_factory():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False,
        )
    return _async_session


async def get_db() -> AsyncSession:
    factory = _get_session_factory()
    async with factory() as session:
        yield session
