# bot/base/db_middleware.py
from __future__ import annotations

from typing import Optional, Callable, Awaitable, Any

from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)


def normalize_async_dsn(dsn: str) -> str:
    """
    Приводим DSN к async-формату.
    Например: postgresql://... -> postgresql+asyncpg://...
    Если уже содержит '+', оставляем как есть.
    """
    if "://" not in dsn:
        raise ValueError("Invalid DSN: missing scheme (e.g. 'postgresql://')")
    scheme, rest = dsn.split("://", 1)
    if "+" in scheme:
        return dsn
    if scheme == "postgresql":
        return f"postgresql+asyncpg://{rest}"
    # при желании можно добавить и другие схемы
    return dsn


def build_session_maker(dsn: str, echo: bool = False) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    dsn_async = normalize_async_dsn(dsn)
    engine = create_async_engine(dsn_async, echo=echo, future=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, maker


class DbSessionMiddleware(BaseMiddleware):
    """
    Кладёт AsyncSession в data['db_session'] для каждого апдейта.
    aiogram-dialog перенесёт это в dialog_manager.middleware_data['db_session'].
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        super().__init__()
        self._session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[Any, dict], Awaitable[Any]],
        event: Any,
        data: dict
    ) -> Any:
        async with self._session_maker() as session:
            data["db_session"] = session
            return await handler(event, data)
