import logging
from typing import Any

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode, ChatEvent
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, List, Multi, Jinja
from aiogram_dialog.widgets.kbd import Button, Row, Column, Back, SwitchTo, Select, Group, Cancel, Start, Multiselect, \
    ManagedMultiselect, Checkbox

from bot.dialogs.general_tools import need_to_display_current_value, go_back_when_edit_mode, switch_state, \
    raise_keyboard_error, raise_dialog_data_error, get_item_by_key
from bot.dialogs.registration.registration_tools import generate_save_user_experience
from bot.states.registration_states import PlayerForm

from bot.db.current_requests import user, get_user_player, get_user_general


# On start
async def set_current_systems(start_data: Any, dialog_manager: DialogManager):
    dialog_manager.dialog_data["current_systems"] = set()


# Passing arguments to the dialog (GETTERS)
async def get_systems(dialog_manager: DialogManager, **kwargs):
    # These are ttrpgs from top of the list of ORR Roll20 report Q3 | 2021, maybe some other systems should be added:
    # Star Wars, Blades in the Dark, Apocalypse World System, Mutants and Masterminds, Shadowrun, Savage Worlds, Vampire: The Masquerade (as separate from World of Darkness category)
    popular_systems = [
        {"system": "D&D", "id": "system_dnd"},
        {"system": "Зов Ктулху", "id": "system_call_of_cthulhu"},
        {"system": "Pathfinder", "id": "system_pathfinder"},
        {"system": "Warhammer", "id": "system_warhammer"},
        {"system": "Мир Тьмы", "id": "system_world_of_darkness"},
        {"system": "Starfinder", "id": "system_starfinder"},
        {"system": "FATE", "id": "system_fate"},
        {"system": "Savage Worlds", "id": "system_savage_worlds"},
        {"system": "Cyberpunk", "id": "system_cyberpunk"},
        {"system": "GURPS", "id": "system_gurps"},
    ]
    return {
        "current_systems": dialog_manager.dialog_data.get("current_systems", []),
        "popular_systems": popular_systems,
    }


# Saving player form settings (ONCLICK)
save_experience_player = generate_save_user_experience("player", PlayerForm.choosing_payment)


async def save_payment(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    payment_by_id = {
        "payment_free": "Только бесплатные",
        "payment_paid": "Только платные",
        "payment_both": "Бесплатные и платные",
    }
    payment = payment_by_id.get(button.widget_id)

    if payment is None:
        await raise_keyboard_error(callback, "оплата (игрок)")
        return
    user["player"]["payment"] = payment

    next_states = {"edit": None, "register": PlayerForm.choosing_systems}
    await switch_state(dialog_manager, next_states)


async def save_systems_from_user(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    if dialog_manager.dialog_data.get("current_systems") is None:
        await raise_dialog_data_error(dialog_manager, "current_systems", message)
        return

    user_systems = list(message.text.split(','))
    user_systems = [system.strip(" \'\";,") for system in user_systems]

    data = await get_systems(dialog_manager)
    # TODO: detect synonyms to systems, e. g. D&D - DnD
    for system in user_systems:
        item = await get_item_by_key(data, "popular_systems", "system", system, message, "системы", True, True)

        if not item is None:
            multiselect: ManagedMultiselect = dialog_manager.find("systems_multiselect")
            await multiselect.set_checked(item["id"], True)
        else:
            dialog_manager.dialog_data["current_systems"].add(system)


async def save_systems_and_exit(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    if dialog_manager.dialog_data.get("current_systems") is None:
        await raise_dialog_data_error(dialog_manager, "current_systems", callback)
        return

    multiselect: ManagedMultiselect = dialog_manager.find("systems_multiselect")
    data = await get_systems(dialog_manager)
    systems = data["popular_systems"]

    for system in systems:
        if multiselect.is_checked(system["id"]):
            dialog_manager.dialog_data["current_systems"].add(system["system"])

    user["player"]["systems"] = dialog_manager.dialog_data.get("current_systems")
    await dialog_manager.done()


# Player form
player_form_dialog = Dialog(
    # Checking profile
    Window(
        Multi(
            Jinja(
                "Это ваша анкета игрока, заполнив её, вы дадите мастерам лучше узнать ваши вкусы и интересы. Этим вы повысите шанс, что вашу заявку примет мастер.\n\n" +
                "<b>Опыт</b>: {{experience}}\n" +
                "<b>Оплата</b>: {{payment}}\n" +
                "<b>Системы</b>: "
            ),
            List(
                Jinja("{{item}}"),
                items="systems",
                sep=", "
            ),
            sep="",
        ),

        SwitchTo(Const("Редактировать анкету"), state=PlayerForm.choosing_what_to_edit, id="edit_form_player",
                 show_mode=ShowMode.SEND),
        Cancel(Const("Выйти")),

        state=PlayerForm.checking_info,
    ),
    # Editing profile
    Window(
        Const("Выберите, что хотите отредактировать."),

        Start(Const("Опыт"), state=PlayerForm.choosing_experience, id="edit_experience_player", data={"mode": "edit"}),
        Start(Const("Оплата"), state=PlayerForm.choosing_payment, id="edit_payment_player", data={"mode": "edit"}),
        Start(Const("Системы"), state=PlayerForm.choosing_systems, id="edit_systems_player", data={"mode": "edit"}),
        Start(Const("Заполнить анкету заново"), state=PlayerForm.choosing_experience, id="register_again_player",
              data={"mode": "register"}),
        Back(Const("Назад"), id="back_to_checking_info_player"),

        state=PlayerForm.choosing_what_to_edit,
    ),
    # Getting experience
    Window(
        # TODO: ? give user capability to write it in free form
        Const("Каков ваш опыт в НРИ в качестве игрока?"),
        Jinja("\n<b>Текущее значение</b>: {{payment}}", when=need_to_display_current_value),

        Button(Const("Менее 3 месяцев"), id="experience_0_player", on_click=save_experience_player),
        Button(Const("От 3 месяцев до 1 года"), id="experience_1_player", on_click=save_experience_player),
        Button(Const("От 1 до 3 лет"), id="experience_2_player", on_click=save_experience_player),
        Button(Const("От 3 до 10 лет"), id="experience_3_player", on_click=save_experience_player),
        Button(Const("Более 10 лет"), id="experience_4_player", on_click=save_experience_player),

        go_back_when_edit_mode,
        state=PlayerForm.choosing_experience,
    ),
    # Getting payment
    Window(
        Const("Какие игры вы рассматриваете?"),
        Jinja("\n<b>Текущее значение</b>: {{payment}}", when=need_to_display_current_value),

        Row(
            Button(Const("Только бесплатные"), id="payment_free", on_click=save_payment),
            Button(Const("Только платные"), id="payment_paid", on_click=save_payment),
        ),
        Button(Const("Бесплатные и платные"), id="payment_both", on_click=save_payment),

        go_back_when_edit_mode,
        state=PlayerForm.choosing_payment,
    ),
    # # Getting systems
    Window(
        Const(
            "Выберите интересующие вас системы.\nВсе системы, которых нет в списке, вы можете указать, отправив их ответным сообщением через запятую."),
        Multi(
            Format("\n<b>Текущее значение</b>: "),
            List(
                Jinja("{{item}}"),
                items="systems",
                sep=", "
            ),
            sep="",
            when=need_to_display_current_value,
        ),
        Multi(
            Format("<b>Добавленные вручную системы</b>: "),
            List(
                Jinja("{{item}}"),
                items="current_systems",
                sep=", "
            ),
            sep="",
        ),

        Column(Multiselect(
            checked_text=Format("✓ {item[system]}"),
            unchecked_text=Format("{item[system]}"),
            id="systems_multiselect",
            item_id_getter=lambda item: item["id"],
            items="popular_systems",
        )),
        Button(Const("Сохранить"), id="save_systems_and_exit", on_click=save_systems_and_exit),
        MessageInput(func=save_systems_from_user, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        getter=get_systems,
        state=PlayerForm.choosing_systems,
    ),
    getter=get_user_player,
    on_start=set_current_systems,
)
