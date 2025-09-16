# bot/dialogs/games/all_games.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Row,
    SwitchTo,
    Select,
    Back,
)
from aiogram_dialog.widgets.text import Const, Jinja, Format, Multi

from bot.states.games_states import AllGames  # must define: checking_games, listing_player_games, listing_master_games, viewing_game

# ---- optional imports from current_requests; tolerate absence ----
_get_user_player = None
_get_user_master = None
_get_player_games = None
_get_master_games = None

try:
    from bot.db.current_requests import get_user_player as _gup  # type: ignore
    _get_user_player = _gup
except Exception:
    pass
try:
    from bot.db.current_requests import get_user_master as _gum  # type: ignore
    _get_user_master = _gum
except Exception:
    pass
try:
    from bot.db.current_requests import get_player_games as _gpg  # type: ignore
    _get_player_games = _gpg
except Exception:
    pass
try:
    from bot.db.current_requests import get_master_games as _gmg  # type: ignore
    _get_master_games = _gmg
except Exception:
    pass


# ---------------- helpers ----------------

async def _maybe_await(x):
    return await x if hasattr(x, "__await__") else x


async def _load_player_games(dm: DialogManager) -> List[Dict[str, Any]]:
    if _get_player_games is None:
        return []
    try:
        games = await _maybe_await(_get_player_games(dm))
        return list(games or [])
    except Exception:
        return []


async def _load_master_games(dm: DialogManager) -> List[Dict[str, Any]]:
    if _get_master_games is None:
        return []
    try:
        games = await _maybe_await(_get_master_games(dm))
        return list(games or [])
    except Exception:
        return []


def _game_title(g: Dict[str, Any]) -> str:
    name = g.get("name") or g.get("title") or "Без названия"
    sys = g.get("system") or g.get("game_system") or ""
    city = g.get("city") or ""
    bits = [name]
    if sys:
        bits.append(f"({sys})")
    if city:
        bits.append(f"— {city}")
    return " ".join(bits)


def _game_details(g: Dict[str, Any]) -> str:
    parts: List[str] = []
    parts.append(f"<b>Название:</b> {g.get('name') or g.get('title') or '—'}")
    parts.append(f"<b>Система:</b> {g.get('system') or g.get('game_system') or '—'}")
    parts.append(f"<b>Город / формат:</b> {g.get('city') or '—'} / {g.get('format') or g.get('game_format') or '—'}")
    parts.append(f"<b>Уровень:</b> {g.get('level') or '—'}")
    parts.append(f"<b>Описание:</b> {g.get('description') or g.get('about') or '—'}")
    return "\n".join(parts)


# ---------------- getters (IMPORTANT: accept dialog_manager kwarg) ----------------

async def getter_menu(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """
    Initial menu getter. Preload lists so buttons can show counts.
    """
    dd = dialog_manager.dialog_data
    player_games = await _load_player_games(dialog_manager)
    master_games = await _load_master_games(dialog_manager)
    dd["player_games"] = player_games
    dd["master_games"] = master_games
    return {
        "player_count": len(player_games),
        "master_count": len(master_games),
    }


async def getter_player_list(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    dd = dialog_manager.dialog_data
    games = dd.get("player_games")
    if games is None:
        games = await _load_player_games(dialog_manager)
        dd["player_games"] = games
    items: List[Dict[str, Any]] = [{"id": i, "title": _game_title(g)} for i, g in enumerate(games or [])]
    return {"items": items, "has_items": bool(items)}


async def getter_master_list(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    dd = dialog_manager.dialog_data
    games = dd.get("master_games")
    if games is None:
        games = await _load_master_games(dialog_manager)
        dd["master_games"] = games
    items: List[Dict[str, Any]] = [{"id": i, "title": _game_title(g)} for i, g in enumerate(games or [])]
    return {"items": items, "has_items": bool(items)}


async def getter_view(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    dd = dialog_manager.dialog_data
    selected: Optional[Tuple[str, int]] = dd.get("selected_game")  # ("player"|"master", idx)
    if not selected:
        return {"details": "Игра не выбрана."}
    kind, idx = selected
    lst = dd.get("player_games") if kind == "player" else dd.get("master_games")
    lst = lst or []
    g = lst[idx] if 0 <= idx < len(lst) else {}
    return {"details": _game_details(g)}


# ---------------- click handlers ----------------

async def open_player_game(c: CallbackQuery, w: Select, dialog_manager: DialogManager, item_id: int):
    dd = dialog_manager.dialog_data
    dd["selected_game"] = ("player", int(item_id))
    await dialog_manager.switch_to(AllGames.viewing_game)


async def open_master_game(c: CallbackQuery, w: Select, dialog_manager: DialogManager, item_id: int):
    dd = dialog_manager.dialog_data
    dd["selected_game"] = ("master", int(item_id))
    await dialog_manager.switch_to(AllGames.viewing_game)


# ---------------- dialog ----------------

all_games_dialog = Dialog(
    # 0) Menu / checking_games
    Window(
        Multi(
            Const("Ваши игры 📚"),
            Jinja("\nКак игрок: <b>{{ player_count }}</b>"),
            Jinja("\nКак мастер: <b>{{ master_count }}</b>"),
        ),
        Row(
            SwitchTo(Const("Игры (я игрок)"), id="to_player_list", state=AllGames.listing_player_games),
            SwitchTo(Const("Игры (я мастер)"), id="to_master_list", state=AllGames.listing_master_games),
        ),
        Cancel(Const("Закрыть")),
        getter=getter_menu,
        state=AllGames.checking_games,
    ),

    # 1) Player games list
    Window(
        Multi(
            Const("Список игр, где вы игрок:\n"),
            Jinja("{% if not has_items %}<i>Ничего не найдено</i>{% endif %}"),
        ),
        Select(
            Format("{item[title]}"),
            id="player_game_select",
            item_id_getter=lambda item: item["id"],
            items="items",
            on_click=open_player_game,
            when=lambda d, *_: d.get("has_items", False),
        ),
        Row(Back(Const("Назад")), Cancel(Const("Закрыть"))),
        getter=getter_player_list,
        state=AllGames.listing_player_games,
    ),

    # 2) Master games list
    Window(
        Multi(
            Const("Список игр, где вы мастер:\n"),
            Jinja("{% if not has_items %}<i>Ничего не найдено</i>{% endif %}"),
        ),
        Select(
            Format("{item[title]}"),
            id="master_game_select",
            item_id_getter=lambda item: item["id"],
            items="items",
            on_click=open_master_game,
            when=lambda d, *_: d.get("has_items", False),
        ),
        Row(Back(Const("Назад")), Cancel(Const("Закрыть"))),
        getter=getter_master_list,
        state=AllGames.listing_master_games,
    ),

    # 3) View one game
    Window(
        Jinja("{{ details }}"),
        Row(Back(Const("Назад")), Cancel(Const("Закрыть"))),
        getter=getter_view,
        state=AllGames.viewing_game,
    ),
)
