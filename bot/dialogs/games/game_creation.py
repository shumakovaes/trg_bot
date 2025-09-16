# bot/dialogs/games/game_creation.py
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const, Format, Jinja, Multi
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    Column,
    Back,
    Cancel,
    Start,
    Select,
    Group,
)
from aiogram_dialog.widgets.input import MessageInput

from sqlalchemy import text  # <-- used to persist into DB

from bot.states.games_states import GameCreation
from bot.dialogs.general_tools import (
    switch_state,
    raise_keyboard_error,
)
from bot.db.current_requests import get_user_master  # may be useful for defaults

# --- optional import for popular systems (works if present in current_requests) ---
_popular_callable = None
try:
    from bot.db.current_requests import popular_systems as _popular_callable  # type: ignore
except Exception:
    _popular_callable = None
if _popular_callable is None:
    try:
        from bot.db.current_requests import get_popular_systems as _popular_callable  # type: ignore
    except Exception:
        _popular_callable = None


# ---------------------------
# helpers
# ---------------------------

def _ensure_new_game(dm: DialogManager) -> Dict[str, Any]:
    dm.dialog_data.setdefault("new_game", {})
    return dm.dialog_data["new_game"]  # type: ignore[return-value]


async def _get_popular_systems(dm: DialogManager) -> Sequence[Dict[str, Any]]:
    if _popular_callable is None:
        return []
    try:
        maybe = _popular_callable(dm)
        return await maybe if hasattr(maybe, "__await__") else maybe  # sync/async
    except Exception:
        return []


# ---------------------------
# getters
# ---------------------------

async def get_creation_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """
    Returns current fields of the new game being created and a list of popular systems.
    """
    new_game = _ensure_new_game(dialog_manager)
    systems = await _get_popular_systems(dialog_manager)
    return {
        "title": new_game.get("title"),
        "description": new_game.get("description"),
        "system": new_game.get("system"),
        "format": new_game.get("format"),
        "place": new_game.get("place"),
        "cost": new_game.get("cost"),
        "popular_systems": systems,
    }


# ---------------------------
# input handlers
# ---------------------------

def _text_setter(field: str, next_states: Dict[str, Optional[Any]]):
    async def handle(message: Message, _: MessageInput, dm: DialogManager):
        ng = _ensure_new_game(dm)
        ng[field] = message.text
        await switch_state(dm, next_states)
    return handle


def _html_setter(field: str, next_states: Dict[str, Optional[Any]]):
    async def handle(message: Message, _: MessageInput, dm: DialogManager):
        ng = _ensure_new_game(dm)
        ng[field] = message.html_text
        await switch_state(dm, next_states)
    return handle


# ---------------------------
# click handlers
# ---------------------------

async def choose_system(callback: CallbackQuery, widget: Select, dm: DialogManager, item_id: Any):
    if item_id is None:
        await raise_keyboard_error(callback, "система")
        return
    ng = _ensure_new_game(dm)
    # try to resolve display name by id from the popular list
    systems = await _get_popular_systems(dm)
    name = None
    for it in systems:
        if str(it.get("id")) == str(item_id):
            name = it.get("name") or it.get("system") or str(item_id)
            break
    ng["system"] = name or str(item_id)
    await switch_state(dm, {"edit": None, "register": GameCreation.choosing_format})


async def choose_format(callback: CallbackQuery, button: Button, dm: DialogManager):
    fmt_by_id = {
        "format_online": "online",
        "format_offline": "offline",
        "format_hybrid": "hybrid",
    }
    fmt = fmt_by_id.get(button.widget_id)
    if fmt is None:
        await raise_keyboard_error(callback, "формат")
        return
    _ensure_new_game(dm)["format"] = fmt
    await switch_state(dm, {"edit": None, "register": GameCreation.choosing_place})


async def choose_cost_model(callback: CallbackQuery, button: Button, dm: DialogManager):
    cost_by_id = {
        "cost_free": "Бесплатно",
        "cost_paid": "Платно",
    }
    base = cost_by_id.get(button.widget_id)
    if base is None:
        await raise_keyboard_error(callback, "стоимость")
        return

    ng = _ensure_new_game(dm)
    ng["cost"] = base
    # if paid — ask for details; if free — jump to confirming
    next_states = {"edit": None, "register": (GameCreation.typing_cost if base == "Платно" else GameCreation.confirming)}
    await switch_state(dm, next_states)


async def finalize_cost(message: Message, _: MessageInput, dm: DialogManager):
    ng = _ensure_new_game(dm)
    # append extra cost details
    ng["cost"] = (ng.get("cost") or "") + (". " if ng.get("cost") else "") + message.text
    await switch_state(dm, {"edit": None, "register": GameCreation.confirming})


async def confirm_creation(callback: CallbackQuery, button: Button, dm: DialogManager):
    """
    Persist the new game into DB (games table), auto-creating the current user if missing.
    """
    ng = _ensure_new_game(dm)

    # Basic validation
    title = (ng.get("title") or "").strip()
    if not title:
        await raise_keyboard_error(callback, "название игры")
        return

    # Grab AsyncSession from middleware
    session = dm.middleware_data.get("db_session")
    if session is None:
        await raise_keyboard_error(callback, "подключение к базе")
        return

    # Identify current user (by Telegram ID)
    tg_id = callback.from_user.id
    display_name = callback.from_user.full_name

    # Ensure user exists (INSERT if not found)
    # NOTE: this is a minimal upsert; your real registration flow can provide richer fields.
    res = await session.execute(
        text("SELECT id FROM users WHERE telegram_id = :tg_id"),
        {"tg_id": tg_id},
    )
    user_id = res.scalar_one_or_none()
    if user_id is None:
        res = await session.execute(
            text(
                """
                INSERT INTO users (telegram_id, name, role, game_format)
                VALUES (:tg_id, :name, :role, :fmt)
                RETURNING id
                """
            ),
            {
                "tg_id": tg_id,
                "name": display_name,
                "role": "master",
                "fmt": ng.get("format") or "online",
            },
        )
        user_id = res.scalar_one()

    # Insert game
    res = await session.execute(
        text(
            """
            INSERT INTO games (title, description, system, format, place, cost, master_user_id, is_open)
            VALUES (:title, :description, :system, :format, :place, :cost, :uid, TRUE)
            RETURNING id
            """
        ),
        {
            "title": ng.get("title") or "Без названия",
            "description": ng.get("description") or "",
            "system": ng.get("system") or "",
            "format": ng.get("format") or "",
            "place": ng.get("place") or "",
            "cost": ng.get("cost") or "",
            "uid": user_id,
        },
    )
    game_id = res.scalar_one()
    await session.commit()

    # Keep the new id in memory for UI (optional)
    ng["id"] = str(game_id)

    # Done, close dialog
    await dm.done()


# ---------------------------
# dialog
# ---------------------------

game_creation_dialog = Dialog(
    # 1) Title
    Window(
        Multi(
            Const("Введите название игры:"),
            Jinja("\n<b>Текущее</b>: {{ title }}", when=lambda d, w, m: bool(d.get("title"))),
        ),
        MessageInput(_html_setter("title", {"edit": None, "register": GameCreation.typing_description}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.typing_title,
    ),

    # 2) Description
    Window(
        Multi(
            Const("Добавьте краткое описание:"),
            Jinja("\n<b>Текущее</b>: {{ description }}", when=lambda d, w, m: bool(d.get("description"))),
        ),
        MessageInput(_html_setter("description", {"edit": None, "register": GameCreation.choosing_system}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.typing_description,
    ),

    # 3) System (list if available)
    Window(
        Multi(
            Const("Выберите систему из списка или отправьте сообщением.\n"),
            Jinja("<b>Текущая</b>: {{ system or '—' }}"),
        ),
        Group(
            Select(
                Format("{item[name]}"),
                id="system_select",
                item_id_getter=lambda x: x["id"],
                items="popular_systems",
                on_click=choose_system,
            ),
            width=1,
            when=lambda d, w, m: bool((d.get("popular_systems") or [])),
        ),
        MessageInput(_text_setter("system", {"edit": None, "register": GameCreation.choosing_format}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.choosing_system,
    ),

    # 4) Format
    Window(
        Multi(
            Const("Выберите формат проведения:"),
            Jinja("\n<b>Текущий</b>: {{ format or '—' }}"),
        ),
        Row(
            Button(Const("Онлайн"), id="format_online", on_click=choose_format),
            Button(Const("Оффлайн"), id="format_offline", on_click=choose_format),
            Button(Const("Гибрид"), id="format_hybrid", on_click=choose_format),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.choosing_format,
    ),

    # 5) Place
    Window(
        Multi(
            Const("Укажите место (город/клуб) или онлайн-платформу:"),
            Jinja("\n<b>Текущее</b>: {{ place or '—' }}"),
        ),
        MessageInput(_text_setter("place", {"edit": None, "register": GameCreation.choosing_cost}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.choosing_place,
    ),

    # 6) Cost
    Window(
        Multi(
            Const("Стоимость участия:"),
            Jinja("\n<b>Текущая</b>: {{ cost or '—' }}"),
        ),
        Row(
            Button(Const("Бесплатно"), id="cost_free", on_click=choose_cost_model),
            Button(Const("Платно"), id="cost_paid", on_click=choose_cost_model),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.choosing_cost,
    ),

    # 6.1) Paid cost details
    Window(
        Const("Уточните условия оплаты (например, «500 ₽ за 3 часа»):"),
        MessageInput(finalize_cost, content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.typing_cost,
    ),

    # 7) Confirm
    Window(
        Multi(
            Const("Проверьте детали будущей игры:\n"),
            Jinja("<b>Название</b>: {{ title or '—' }}"),
            Jinja("\n<b>Описание</b>: {{ description or '—' }}"),
            Jinja("\n<b>Система</b>: {{ system or '—' }}"),
            Jinja("\n<b>Формат</b>: {{ format or '—' }}"),
            Jinja("\n<b>Место</b>: {{ place or '—' }}"),
            Jinja("\n<b>Стоимость</b>: {{ cost or '—' }}"),
        ),
        Row(
            Button(Const("Создать игру"), id="confirm_creation", on_click=confirm_creation),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=get_creation_data,
        state=GameCreation.confirming,
    ),
)
