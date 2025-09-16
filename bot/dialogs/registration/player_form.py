# bot/dialogs/registration/player_form.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    Back,
    Cancel,
    SwitchTo,
    Select,
    Group,
)
from aiogram_dialog.widgets.text import Const, Jinja, Format, Multi

from bot.dialogs.general_tools import (
    need_to_display_current_value,
    go_back_when_edit_mode,
    switch_state,
    raise_keyboard_error,
)
from bot.states.registration_states import PlayerForm  # your states group


# ===== Optional integrations with current_requests (safe imports) =====
try:
    from bot.db.current_requests import get_user_player, get_user_general  # type: ignore
except Exception:
    get_user_player = None
    get_user_general = None

_get_popular = None
try:
    from bot.db.current_requests import get_popular_systems as _get_popular  # type: ignore
except Exception:
    _get_popular = None
if _get_popular is None:
    try:
        from bot.db.current_requests import popular_systems as _get_popular  # type: ignore
    except Exception:
        _get_popular = None


# ===== Helpers & Getters =====

def _ensure(dd: Dict[str, Any], key: str, default: Any) -> Any:
    if key not in dd:
        dd[key] = default
    return dd[key]


async def _load_popular(dm: DialogManager) -> Sequence[Dict[str, Any]]:
    if _get_popular is None:
        return []
    try:
        maybe = _get_popular(dm)
        return await maybe if hasattr(maybe, "__await__") else maybe
    except Exception:
        return []


async def set_current_systems(start_data: Dict[str, Any], manager: DialogManager):
    """
    aiogram-dialog 2.x on_start signature.
    Preload player/general profiles and popular systems into dialog_data.
    """
    dd = manager.dialog_data
    _ensure(dd, "player_profile", {})
    _ensure(dd, "general_profile", {})
    _ensure(dd, "popular_systems", [])
    _ensure(dd, "edit_mode", False)  # you can flip this from outside if needed

    # Pull player profile
    if get_user_player:
        try:
            player = await get_user_player(manager)
            if player:
                dd["player_profile"] = player
        except Exception:
            pass

    # Pull general profile
    if get_user_general:
        try:
            general = await get_user_general(manager)
            if general:
                dd["general_profile"] = general
        except Exception:
            pass

    # Popular systems (optional)
    systems = await _load_popular(manager)
    if systems:
        dd["popular_systems"] = systems


async def getter_player_form(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """
    Getter must accept 'dialog_manager' named exactly like this in aiogram-dialog 2.x.
    """
    dd = dialog_manager.dialog_data
    pp = _ensure(dd, "player_profile", {})
    gp = _ensure(dd, "general_profile", {})
    systems = _ensure(dd, "popular_systems", [])
    edit_mode = bool(dd.get("edit_mode", False))

    # Normalize for UI
    preferred = pp.get("preferred_systems") or []
    if isinstance(preferred, str):
        preferred = [preferred]
    return {
        "player": {
            "name": gp.get("name") or pp.get("name") or "",
            "age": gp.get("age") or pp.get("age") or "",
            "city": gp.get("city") or pp.get("city") or "",
            "game_format": gp.get("game_format") or pp.get("game_format") or "",
            "preferred_systems": preferred,
        },
        "popular_systems": systems,
        "edit_mode": edit_mode,
    }


# ===== Compatibility shim for need_to_display_current_value =====
async def _show_current_value(dm: DialogManager, field: str, value: Any):
    """
    Try both known signatures:
      1) need_to_display_current_value(dialog_manager, item_type, current_value)
      2) need_to_display_current_value(item_type, dialog_manager, current_value)
    If both fail, we just continue without raising.
    """
    try:
        return await need_to_display_current_value(dm, field, value)
    except TypeError:
        try:
            return await need_to_display_current_value(field, dm, value)
        except Exception:
            return False
    except Exception:
        return False


# ===== Inputs (save text fields) =====

def _text_saver(field: str, next_states: Dict[str, Optional[Any]]):
    async def handle(message: Message, _: MessageInput, dm: DialogManager):
        dd = dm.dialog_data
        pp = _ensure(dd, "player_profile", {})
        gp = _ensure(dd, "general_profile", {})
        text_val = (message.text or "").strip()

        # Save both to keep them aligned for now
        pp[field] = text_val
        gp[field] = text_val

        # Use the compatibility shim
        await _show_current_value(dm, field, text_val)

        # Go next
        await switch_state(dm, next_states)
    return handle


# ===== Click handlers =====

async def choose_format(callback: CallbackQuery, button: Button, dm: DialogManager):
    fmt_map = {
        "fmt_online": "online",
        "fmt_offline": "offline",
        "fmt_hybrid": "hybrid",
    }
    fmt = fmt_map.get(button.widget_id)
    if not fmt:
        await raise_keyboard_error(callback, "формат")
        return

    dd = dm.dialog_data
    pp = _ensure(dd, "player_profile", {})
    gp = _ensure(dd, "general_profile", {})

    pp["game_format"] = fmt
    gp["game_format"] = fmt

    await switch_state(dm, {"edit": None, "register": PlayerForm.choosing_systems})


async def add_system_by_select(callback: CallbackQuery, widget: Select, dm: DialogManager, item_id: Any):
    dd = dm.dialog_data
    pp = _ensure(dd, "player_profile", {})
    preferred: List[str] = pp.get("preferred_systems") or []
    if isinstance(preferred, str):
        preferred = [preferred]

    # resolve display name from popular list
    systems = _ensure(dd, "popular_systems", [])
    name: Optional[str] = None
    for s in systems:
        if str(s.get("id")) == str(item_id):
            name = s.get("name") or s.get("system") or str(item_id)
            break
    value = name or str(item_id)

    if value not in preferred:
        preferred.append(value)
    pp["preferred_systems"] = preferred

    await switch_state(dm, {"edit": None, "register": PlayerForm.confirming})


async def add_system_by_message(message: Message, _: MessageInput, dm: DialogManager):
    value = (message.text or "").strip()
    if not value:
        await switch_state(dm, {"edit": None, "register": PlayerForm.confirming})
        return

    dd = dm.dialog_data
    pp = _ensure(dd, "player_profile", {})
    preferred: List[str] = pp.get("preferred_systems") or []
    if isinstance(preferred, str):
        preferred = [preferred]
    if value not in preferred:
        preferred.append(value)
    pp["preferred_systems"] = preferred

    await switch_state(dm, {"edit": None, "register": PlayerForm.confirming})


async def finish_profile(callback: CallbackQuery, button: Button, dm: DialogManager):
    """
    Here you could persist the profile to DB if you want (upsert).
    For now we just close the dialog.
    """
    await dm.done()


# ===== Dialog =====

player_form_dialog = Dialog(
    # 0) Start/check
    Window(
        Const("Давайте заполним профиль игрока 👇"),
        Row(
            SwitchTo(Const("Ввести имя"), state=PlayerForm.typing_name, id="to_name"),
            SwitchTo(Const("Возраст"), state=PlayerForm.typing_age, id="to_age"),
        ),
        Row(
            SwitchTo(Const("Город"), state=PlayerForm.typing_city, id="to_city"),
            SwitchTo(Const("Формат"), state=PlayerForm.choosing_format, id="to_format"),
        ),
        Row(
            SwitchTo(Const("Системы"), state=PlayerForm.choosing_systems, id="to_systems"),
        ),
        Cancel(Const("Отмена")),
        getter=getter_player_form,
        state=PlayerForm.checking_info,
    ),

    # 1) Name
    Window(
        Multi(
            Const("Введите ваше имя:"),
            Jinja("\nТекущее: <b>{{ player.name or '—' }}</b>"),
        ),
        MessageInput(_text_saver("name", {"edit": None, "register": PlayerForm.typing_age}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_player_form,
        state=PlayerForm.typing_name,
    ),

    # 2) Age
    Window(
        Multi(
            Const("Введите возраст:"),
            Jinja("\nТекущий: <b>{{ player.age or '—' }}</b>"),
        ),
        MessageInput(_text_saver("age", {"edit": None, "register": PlayerForm.typing_city}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_player_form,
        state=PlayerForm.typing_age,
    ),

    # 3) City
    Window(
        Multi(
            Const("Введите город:"),
            Jinja("\nТекущий: <b>{{ player.city or '—' }}</b>"),
        ),
        MessageInput(_text_saver("city", {"edit": None, "register": PlayerForm.choosing_format}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_player_form,
        state=PlayerForm.typing_city,
    ),

    # 4) Game format
    Window(
        Multi(
            Const("Выберите предпочитаемый формат игр:"),
            Jinja("\nТекущий: <b>{{ player.game_format or '—' }}</b>"),
        ),
        Row(
            Button(Const("Онлайн"), id="fmt_online", on_click=choose_format),
            Button(Const("Оффлайн"), id="fmt_offline", on_click=choose_format),
            Button(Const("Гибрид"), id="fmt_hybrid", on_click=choose_format),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_player_form,
        state=PlayerForm.choosing_format,
    ),

    # 5) Preferred systems
    Window(
        Multi(
            Const("Выберите систему из списка или пришлите свою в сообщении:"),
            Jinja("\nТекущие: <b>{{ ', '.join(player.preferred_systems) if player.preferred_systems else '—' }}</b>"),
        ),
        Group(
            Select(
                Format("{item[name]}"),
                id="systems_select",
                item_id_getter=lambda x: x["id"],
                items="popular_systems",
                on_click=add_system_by_select,
            ),
            width=1,
            when=lambda d, w, m: bool((d.get("popular_systems") or [])),
        ),
        MessageInput(add_system_by_message, content_types=[ContentType.TEXT]),
        Row(
            SwitchTo(Const("К подтверждению"), state=PlayerForm.confirming, id="to_confirm"),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_player_form,
        state=PlayerForm.choosing_systems,
    ),

    # 6) Confirm
    Window(
        Multi(
            Const("Проверьте данные профиля:\n"),
            Jinja("<b>Имя</b>: {{ player.name or '—' }}"),
            Jinja("\n<b>Возраст</b>: {{ player.age or '—' }}"),
            Jinja("\n<b>Город</b>: {{ player.city or '—' }}"),
            Jinja("\n<b>Формат</b>: {{ player.game_format or '—' }}"),
            Jinja("\n<b>Системы</b>: {{ ', '.join(player.preferred_systems) if player.preferred_systems else '—' }}"),
        ),
        Row(
            Button(Const("Сохранить"), id="save_profile", on_click=finish_profile),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_player_form,
        state=PlayerForm.confirming,
    ),

    on_start=set_current_systems,
)
