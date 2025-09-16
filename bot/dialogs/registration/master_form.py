# bot/dialogs/registration/master_form.py
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

from bot.states.registration_states import MasterForm
from bot.dialogs.general_tools import (
    need_to_display_current_value,
    switch_state,
    raise_keyboard_error,
)

# ===== Optional integrations with current_requests (safe imports) =====
get_user_master = None
get_user_general = None
_get_popular = None
try:
    from bot.db.current_requests import get_user_master as _gum  # type: ignore
    get_user_master = _gum
except Exception:
    pass
try:
    from bot.db.current_requests import get_user_general as _gug  # type: ignore
    get_user_general = _gug
except Exception:
    pass
try:
    from bot.db.current_requests import get_popular_systems as _gps  # type: ignore
    _get_popular = _gps
except Exception:
    pass
if _get_popular is None:
    try:
        from bot.db.current_requests import popular_systems as _gps2  # type: ignore
        _get_popular = _gps2
    except Exception:
        _get_popular = None


# ===== Helpers =====

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


# compatibility shim for need_to_display_current_value
async def _show_current_value(dm: DialogManager, field: str, value: Any):
    try:
        return await need_to_display_current_value(dm, field, value)
    except TypeError:
        try:
            return await need_to_display_current_value(field, dm, value)
        except Exception:
            return False
    except Exception:
        return False


# ===== on_start & getter =====

async def mark_form_as_filled(start_data: Dict[str, Any], dialog_manager: DialogManager) -> None:
    """
    Correct aiogram-dialog 2.x signature: (start_data, dialog_manager)
    Initialize dialog_data and preload existing profiles.
    """
    dd = dialog_manager.dialog_data
    _ensure(dd, "edit_mode", False)
    _ensure(dd, "master_profile", {})
    _ensure(dd, "general_profile", {})
    _ensure(dd, "popular_systems", [])

    # Respect incoming mode if provided
    mode = (start_data or {}).get("mode")
    if isinstance(mode, str) and mode:
        dd["mode"] = mode

    # Load master profile
    if get_user_master:
        try:
            mp = await get_user_master(dialog_manager)
            if mp:
                dd["master_profile"] = mp
        except Exception:
            pass

    # Load general profile (for shared fields like name/city if needed)
    if get_user_general:
        try:
            gp = await get_user_general(dialog_manager)
            if gp:
                dd["general_profile"] = gp
        except Exception:
            pass

    # Load systems
    systems = await _load_popular(dialog_manager)
    if systems:
        dd["popular_systems"] = systems


async def getter_master_form(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    dd = dialog_manager.dialog_data
    mp = _ensure(dd, "master_profile", {})
    gp = _ensure(dd, "general_profile", {})
    systems = _ensure(dd, "popular_systems", [])
    edit_mode = bool(dd.get("edit_mode", False))

    # Normalize fields
    run_systems = mp.get("running_systems") or []
    if isinstance(run_systems, str):
        run_systems = [run_systems]

    return {
        "master": {
            "name": gp.get("name") or mp.get("name") or "",
            "city": gp.get("city") or mp.get("city") or "",
            "experience": mp.get("experience") or "",
            "about": mp.get("about") or "",
            "cost": mp.get("cost") or "",
            "running_systems": run_systems,
        },
        "popular_systems": systems,
        "edit_mode": edit_mode,
    }


# ===== Inputs (save text fields) =====

def _text_saver(field: str, next_states: Dict[str, Optional[Any]]):
    async def handle(message: Message, _: MessageInput, dm: DialogManager):
        dd = dm.dialog_data
        mp = _ensure(dd, "master_profile", {})
        text_val = (message.text or "").strip()
        mp[field] = text_val

        await _show_current_value(dm, field, text_val)
        await switch_state(dm, next_states)
    return handle


# ===== Click handlers =====

async def choose_system_from_list(cb: CallbackQuery, widget: Select, dm: DialogManager, item_id: Any):
    dd = dm.dialog_data
    mp = _ensure(dd, "master_profile", {})
    chosen: List[str] = mp.get("running_systems") or []
    if isinstance(chosen, str):
        chosen = [chosen]

    systems = _ensure(dd, "popular_systems", [])
    name: Optional[str] = None
    for s in systems:
        if str(s.get("id")) == str(item_id):
            name = s.get("name") or s.get("system") or str(item_id)
            break
    value = name or str(item_id)

    if value not in chosen:
        chosen.append(value)
    mp["running_systems"] = chosen

    await switch_state(dm, {"edit": None, "register": MasterForm.confirming})


async def add_custom_system(message: Message, _: MessageInput, dm: DialogManager):
    value = (message.text or "").strip()
    dd = dm.dialog_data
    mp = _ensure(dd, "master_profile", {})
    chosen: List[str] = mp.get("running_systems") or []
    if isinstance(chosen, str):
        chosen = [chosen]

    if value and value not in chosen:
        chosen.append(value)
    mp["running_systems"] = chosen

    await switch_state(dm, {"edit": None, "register": MasterForm.confirming})


async def select_free(cb: CallbackQuery, button: Button, dm: DialogManager):
    dd = dm.dialog_data
    mp = _ensure(dd, "master_profile", {})
    mp["cost"] = "free"
    await switch_state(dm, {"edit": None, "register": MasterForm.confirming})


async def select_paid(cb: CallbackQuery, button: Button, dm: DialogManager):
    dd = dm.dialog_data
    mp = _ensure(dd, "master_profile", {})
    mp["cost"] = "paid"
    await switch_state(dm, {"edit": None, "register": MasterForm.typing_cost_value})


async def save_master(cb: CallbackQuery, button: Button, dm: DialogManager):
    # Persist to DB here if you need (upsert). For now, just close dialog.
    await dm.done()


# ===== Dialog =====

master_form_dialog = Dialog(
    # 0) Overview
    Window(
        Multi(
            Const("Профиль ведущего (мастера) 🎲\n"),
            Jinja("<b>Имя</b>: {{ master.name or '—' }}"),
            Jinja("\n<b>Город</b>: {{ master.city or '—' }}"),
            Jinja("\n<b>Опыт</b>: {{ master.experience or '—' }}"),
            Jinja("\n<b>О себе</b>: {{ master.about or '—' }}"),
            Jinja("\n<b>Системы</b>: {{ ', '.join(master.running_systems) if master.running_systems else '—' }}"),
            Jinja("\n<b>Формат оплаты</b>: {{ master.cost or '—' }}"),
        ),
        Row(
            SwitchTo(Const("Опыт"), state=MasterForm.typing_experience, id="to_experience"),
            SwitchTo(Const("О себе"), state=MasterForm.typing_about, id="to_about"),
        ),
        Row(
            SwitchTo(Const("Системы"), state=MasterForm.choosing_systems, id="to_systems"),
            SwitchTo(Const("Оплата"), state=MasterForm.choosing_cost, id="to_cost"),
        ),
        Cancel(Const("Отмена")),
        getter=getter_master_form,
        state=MasterForm.checking_info,
    ),

    # 1) Experience
    Window(
        Multi(
            Const("Опишите ваш опыт мастерства:"),
            Jinja("\nТекущее: <b>{{ master.experience or '—' }}</b>"),
        ),
        MessageInput(_text_saver("experience", {"edit": None, "register": MasterForm.checking_info}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_master_form,
        state=MasterForm.typing_experience,
    ),

    # 2) About
    Window(
        Multi(
            Const("Пара слов о себе:"),
            Jinja("\nТекущее: <b>{{ master.about or '—' }}</b>"),
        ),
        MessageInput(_text_saver("about", {"edit": None, "register": MasterForm.checking_info}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_master_form,
        state=MasterForm.typing_about,
    ),

    # 3) Systems
    Window(
        Multi(
            Const("Выберите систему из списка или пришлите свою в сообщении:"),
            Jinja("\nТекущие: <b>{{ ', '.join(master.running_systems) if master.running_systems else '—' }}</b>"),
        ),
        Group(
            Select(
                Format("{item[name]}"),
                id="mf_systems_select",
                item_id_getter=lambda x: x["id"],
                items="popular_systems",
                on_click=choose_system_from_list,
            ),
            width=1,
            when=lambda d, w, m: bool((d.get("popular_systems") or [])),
        ),
        MessageInput(add_custom_system, content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_master_form,
        state=MasterForm.choosing_systems,
    ),

    # 4) Cost (free/paid)
    Window(
        Multi(
            Const("Выберите формат оплаты:"),
            Jinja("\nТекущий: <b>{{ master.cost or '—' }}</b>"),
        ),
        Row(
            Button(Const("Бесплатно"), id="mf_cost_free", on_click=select_free),
            Button(Const("Платно"), id="mf_cost_paid", on_click=select_paid),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_master_form,
        state=MasterForm.choosing_cost,
    ),

    # 5) Cost value (if paid)
    Window(
        Multi(
            Const("Введите стоимость (например, 500 руб/сессия):"),
            Jinja("\nТекущая: <b>{{ master.cost or '—' }}</b>"),
        ),
        MessageInput(_text_saver("cost", {"edit": None, "register": MasterForm.confirming}), content_types=[ContentType.TEXT]),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_master_form,
        state=MasterForm.typing_cost_value,
    ),

    # 6) Confirm
    Window(
        Multi(
            Const("Проверьте данные профиля мастера:\n"),
            Jinja("<b>Имя</b>: {{ master.name or '—' }}"),
            Jinja("\n<b>Город</b>: {{ master.city or '—' }}"),
            Jinja("\n<b>Опыт</b>: {{ master.experience or '—' }}"),
            Jinja("\n<b>О себе</b>: {{ master.about or '—' }}"),
            Jinja("\n<b>Системы</b>: {{ ', '.join(master.running_systems) if master.running_systems else '—' }}"),
            Jinja("\n<b>Оплата</b>: {{ master.cost or '—' }}"),
        ),
        Row(
            Button(Const("Сохранить"), id="mf_save", on_click=save_master),
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=getter_master_form,
        state=MasterForm.confirming,
    ),

    on_start=mark_form_as_filled,
)
