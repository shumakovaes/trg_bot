# bot/dialogs/games/searching_game.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Back, Cancel, Select, ScrollingGroup
from aiogram_dialog.widgets.text import Const, Format

from bot.states.games_states import SearchingGame
from bot.db.current_requests import get_open_games


def _get_session(dm: DialogManager):
    """Extract AsyncSession that db_middleware puts into middleware_data."""
    session = dm.middleware_data.get("db_session")
    if session is None:
        raise RuntimeError("AsyncSession not found in middleware_data['db_session']")
    return session


async def search_on_start(start_data: Dict[str, Any], manager: DialogManager):
    """
    aiogram_dialog on_start signature is (start_data, manager).
    We just jump to the listing window; data will be lazy-loaded by getter.
    """
    await manager.switch_to(SearchingGame.listing_results)


async def _load_open_games(dm: DialogManager) -> List[Dict[str, Any]]:
    """
    Load open games from DB via the new current_requests API.
    Returns a list of dicts with at least: id, title, system, city, cost, master_id, etc.
    """
    session = _get_session(dm)

    # get_open_games returns a dict like {"games": [...]} by current_requests.py
    # If your signature supports filters, you can pass them in here.
    raw = await get_open_games(dm, session=session)

    games: List[Dict[str, Any]] = raw.get("games", []) if isinstance(raw, dict) else []
    # Normalize/ensure keys exist to avoid KeyErrors when rendering
    normalized: List[Dict[str, Any]] = []
    for g in games:
        normalized.append(
            {
                "id": str(g.get("id")),
                "title": g.get("title") or "Без названия",
                "system": g.get("system") or "—",
                "city": g.get("city") or "—",
                "cost": g.get("cost", 0),
                "format": g.get("format") or "—",
                "current_players": g.get("current_players"),
                "max_players": g.get("max_players"),
                "min_age": g.get("min_age"),
                "max_age": g.get("max_age"),
                "master_id": g.get("master_id"),
                "status": g.get("status"),
            }
        )

    # Sort by title for deterministic output
    normalized.sort(key=lambda it: it["title"].lower())
    return normalized


async def get_search_data(dialog_manager: DialogManager, **_):
    """
    Getter for the listing window. Must accept dialog_manager in aiogram_dialog v2.
    """
    items = await _load_open_games(dialog_manager)
    # Store for later (e.g., when clicking an item)
    dialog_manager.dialog_data["search_items"] = {it["id"]: it for it in items}
    return {"items": items, "count": len(items)}


async def on_select_game(
    c: CallbackQuery,
    widget: Select,
    manager: DialogManager,
    item_id: str,
):
    """
    Handle select click: item_id is the game's string id (we set it in Select.item_id=...).
    You can switch to a details state/window here if you have one.
    For now, just acknowledge and keep the list.
    """
    items_map: Dict[str, Dict[str, Any]] = manager.dialog_data.get("search_items", {})
    chosen = items_map.get(item_id)
    if chosen:
        await c.answer(f"Вы выбрали игру: {chosen['title']}", show_alert=False)
    else:
        await c.answer("Игра не найдена", show_alert=False)


# === Widgets ===

# One row per game
row_text = Format(
    "🎲 <b>{title}</b>\n"
    "📚 {system}   🏙️ {city}   💵 {cost}\n"
    "👥 {current_players}/{max_players}   🧭 {format}"
)

# Scrollable list with Select; item_id is a string game id
list_widget = ScrollingGroup(
    Select(
        text=row_text,
        id="open_game",
        item_id=Format("{id}"),
        items="items",
        on_click=on_select_game,
    ),
    id="open_games_scroll",
    width=1,
    height=8,
)


searching_game_dialog = Dialog(
    # A short "loading/entering" window; immediately switches to listing on start
    Window(
        Const("🔎 Ищу открытые игры…"),
        state=SearchingGame.checking_open_games,
        on_start=search_on_start,
    ),
    # The main listing window
    Window(
        Format("Найдено игр: <b>{count}</b>"),
        list_widget,
        Back(Const("⬅️ Назад")),
        Cancel(Const("❌ Отмена")),
        getter=get_search_data,
        state=SearchingGame.listing_results,
    ),
)
