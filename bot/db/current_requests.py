# db_getters.py
# Async getters for aiogram_dialog that fetch from the database instead of in-memory dicts.

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from aiogram_dialog import DialogManager
from sqlalchemy.ext.asyncio import AsyncSession

# Adjust these imports to your package layout if needed
from bot.db.models import UserModel, SessionModel, PlayerModel, MasterModel  # type: ignore
from bot.db.requests import (
    get_user_model,
    get_game_model,
)  # type: ignore


def _extract_session(dialog_manager: DialogManager, **kwargs) -> AsyncSession:
    sess: Optional[AsyncSession] = kwargs.get("session")
    if sess is None:
        md = getattr(dialog_manager, "middleware_data", {}) or {}
        for key in ("session", "db", "db_session"):
            if key in md and isinstance(md[key], AsyncSession):
                sess = md[key]  # type: ignore[assignment]
                break
    if sess is None:
        raise RuntimeError(
            "AsyncSession not found. Pass it as `session=...` or provide it via dialog_manager.middleware_data['db_session']."
        )
    return sess


def _current_tg_id(dialog_manager: DialogManager) -> int:
    try:
        return int(dialog_manager.event.from_user.id)
    except Exception as e:
        raise RuntimeError("Cannot resolve Telegram user id from dialog_manager.event") from e


async def get_user_general(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    session = _extract_session(dialog_manager, **kwargs)
    tg_id = _current_tg_id(dialog_manager)

    user: Optional[UserModel] = await get_user_model(session, tg_id)
    if not user:
        logging.warning("get_user_general: user %s not found", tg_id)
        return {"name": "", "age": 18, "city": "", "time_zone": "", "role": "", "format": "", "about_info": ""}

    return {
        "name": user.name or "",
        "age": int(user.age) if user.age is not None else 18,
        "city": user.city or "",
        "time_zone": user.time_zone or "",
        "role": user.role or "",
        "format": user.game_format or "",
        "about_info": user.about_info or "",
    }


async def get_user_player(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    session = _extract_session(dialog_manager, **kwargs)
    tg_id = _current_tg_id(dialog_manager)

    user: Optional[UserModel] = await get_user_model(session, tg_id)
    if not user or not user.player_profile:
        return {"experience": "", "payment": "", "systems": [], "games": [], "archive": [], "rating": 0, "reviews": {}}

    p = user.player_profile

    # preferred_systems у UserModel — строка; превратим в список
    try:
        systems = [s.strip() for s in (user.preferred_systems or "").split(",") if s.strip()]
    except Exception:
        systems = []

    games_brief: List[Dict[str, str]] = [{"status": s.status or "", "title": s.title or ""} for s in p.games]
    archive_brief: List[Dict[str, str]] = [{"status": s.status or "", "title": s.title or ""} for s in p.archive]

    return {
        "experience": p.experience or "",
        "payment": p.payment or "",
        "systems": systems,
        "games": games_brief,
        "archive": archive_brief,
        "rating": int(p.rating) if p.rating is not None else 0,
        "reviews": p.reviews or {},
    }


async def get_user_master(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    session = _extract_session(dialog_manager, **kwargs)
    tg_id = _current_tg_id(dialog_manager)

    user: Optional[UserModel] = await get_user_model(session, tg_id)
    if not user or not user.master_profile:
        return {
            "is_filled": False, "experience": "", "cost": "", "place": "", "platform": "",
            "requirements": "", "games": [], "archive": [], "rating": 0, "reviews": {},
        }

    m = user.master_profile
    games_brief: List[Dict[str, str]] = [{"status": s.status or "", "title": s.title or ""} for s in m.games]
    archive_brief: List[Dict[str, str]] = [{"status": s.status or "", "title": s.title or ""} for s in m.archive]

    return {
        "is_filled": bool(m.is_filled),
        "experience": m.experience or "",
        "cost": m.cost or "",
        "place": m.place or "",
        "platform": m.platform or "",
        "requirements": m.requirements or "",
        "games": games_brief,
        "archive": archive_brief,
        "rating": int(m.rating) if m.rating is not None else 0,
        "reviews": m.reviews or {},
    }


async def get_player_games(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    session = _extract_session(dialog_manager, **kwargs)
    tg_id = _current_tg_id(dialog_manager)

    user: Optional[UserModel] = await get_user_model(session, tg_id)
    if not user or not user.player_profile:
        return {"games": []}

    result: List[Dict[str, str]] = []
    for s in user.player_profile.games:
        # при желании можно дообновить запись из БД
        try:
            db_game = await get_game_model(session, s.id)
        except Exception:
            db_game = None
        session_model = db_game or s

        in_players = any(getattr(p, "telegram_id", None) == tg_id for p in session_model.players)
        try:
            in_requests = any(getattr(r, "telegram_id", None) == tg_id for r in session_model.requests)  # если есть relation
        except Exception:
            in_requests = False

        if in_players:
            status = "Заявка принята"
        elif in_requests:
            status = "Заявка находится на рассмотрении"
        else:
            status = "Заявка отклонена"

        result.append({"status": status, "title": session_model.title or ""})

    return {"games": result}


async def get_master_games(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    session = _extract_session(dialog_manager, **kwargs)
    tg_id = _current_tg_id(dialog_manager)

    user: Optional[UserModel] = await get_user_model(session, tg_id)
    if not user or not user.master_profile:
        return {"games": []}

    return {"games": [{"status": s.status or "", "title": s.title or ""} for s in user.master_profile.games]}


async def get_player_archive(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    session = _extract_session(dialog_manager, **kwargs)
    tg_id = _current_tg_id(dialog_manager)

    user: Optional[UserModel] = await get_user_model(session, tg_id)
    if not user or not user.player_profile:
        return {"games": []}

    result: List[Dict[str, str]] = []
    for s in user.player_profile.archive:
        in_players = any(getattr(p, "telegram_id", None) == tg_id for p in s.players)
        try:
            in_requests = any(getattr(r, "telegram_id", None) == tg_id for r in s.requests)
        except Exception:
            in_requests = False

        if in_players:
            status = "Заявка принята"
        elif in_requests:
            status = "Заявка находится на рассмотрении"
        else:
            status = "Заявка отклонена"

        result.append({"status": status, "title": s.title or ""})

    return {"games": result}


async def get_master_archive(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    session = _extract_session(dialog_manager, **kwargs)
    tg_id = _current_tg_id(dialog_manager)

    user: Optional[UserModel] = await get_user_model(session, tg_id)
    if not user or not user.master_profile:
        return {"games": []}

    return {"games": [{"status": s.status or "", "title": s.title or ""} for s in user.master_profile.archive]}

async def get_open_games(
    dialog_manager: DialogManager,
    *,
    session: Optional[AsyncSession] = None,
    limit: int = 100,
) -> Sequence[Dict[str, Any]]:
    """
    Load open games from DB for the search dialog.

    Returns a list of dicts like:
    {
        "id": 123,
        "title": "Some title",
        "system": "D&D 5e",
        "format": "online",
        "place": "Roll20/Discord",
        "cost": "Free",
        "description": "...",
        "master_name": "Alice",
        "players": [],   # fill if you want; empty list is fine
    }
    """
    sess: AsyncSession = session or _extract_session(dialog_manager)

    # Grab basic game info + master's display name if available
    q = text(
        """
        SELECT
            g.id,
            g.title,
            COALESCE(g.system, '')      AS system,
            COALESCE(g.format, '')      AS format,
            COALESCE(g.place, '')       AS place,
            COALESCE(g.cost, '')        AS cost,
            COALESCE(g.description, '') AS description,
            COALESCE(u.name, '')        AS master_name
        FROM games AS g
        LEFT JOIN users AS u ON u.id = g.master_user_id
        WHERE g.is_open = TRUE
        ORDER BY g.created_at DESC
        LIMIT :limit
        """
    )
    res = await sess.execute(q, {"limit": limit})
    rows = res.mappings().all()

    # You can enrich with players list here if needed.
    games: List[Dict[str, Any]] = []
    for r in rows:
        games.append(
            {
                "id": r["id"],
                "title": r["title"] or "Без названия",
                "system": r["system"] or "—",
                "format": r["format"] or "—",
                "place": r["place"] or "—",
                "cost": r["cost"] or "—",
                "description": r["description"] or "",
                "master_name": r["master_name"] or "—",
                "players": [],
            }
        )
    return games

# Backward-compat alias (so older imports still work)
open_games = get_open_games