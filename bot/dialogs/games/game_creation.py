import logging
from typing import Any, Optional

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, games, default_game, popular_systems, user, \
    MIN_AGE, MAX_AGE, MIN_PLAYERS_NUMBER, MAX_PLAYERS_NUMBER
from bot.dialogs.games.games_tools import generate_game_description, generate_save_message_from_user_no_formatting_game, \
    get_game_by_id_in_dialog_data, get_game_id_in_dialog_data, generate_save_diapason_from_user, \
    get_game_by_id_in_dialog_data_not_async, \
    need_to_display_current_value_and_min_and_max_provided_players_number, \
    need_to_display_current_value_and_only_min_provided_players_number, \
    need_to_display_current_value_and_only_max_provided_players_number, \
    need_to_display_current_value_and_nothing_provided_players_number, \
    need_to_display_current_value_and_min_and_max_provided_age, need_to_display_current_value_and_only_min_provided_age, \
    need_to_display_current_value_and_only_max_provided_age, need_to_display_current_value_and_nothing_provided_age, \
    get_default_value, is_need_to_be_skipped
from bot.dialogs.general_tools import need_to_display_current_value, go_back_when_edit_mode, switch_state, \
    generate_random_id, is_register_mode, raise_keyboard_error, get_item_by_key
from bot.dialogs.registration.registration import get_cities
from bot.states.games_states import AllGames, GameInspection, GameCreation


# Passing arguments to the dialog (GETTERS)
async def get_default_cost(dialog_manager: DialogManager, **kwargs):
    default_cost = await get_default_value(dialog_manager, "default_cost")
    return {"default_cost": default_cost}


async def get_default_place(dialog_manager: DialogManager, **kwargs):
    default_place = await get_default_value(dialog_manager, "default_place")
    return {"default_place": default_place}


async def get_default_platform(dialog_manager: DialogManager, **kwargs):
    default_platform = await get_default_value(dialog_manager, "default_platform")
    return {"default_platform": default_platform}


async def get_default_requirements(dialog_manager: DialogManager, **kwargs):
    default_requirements = await get_default_value(dialog_manager, "default_requirements")
    return {"default_requirements": default_requirements}


async def get_systems(**kwargs):
    return {
        "popular_systems": popular_systems,
    }


async def get_editions(**kwargs):
    dnd_editions = [
        {"edition": "D&D 2024", "id": "edition_dnd_2024"},
        {"edition": "D&D 5", "id": "edition_dnd_5"},
        {"edition": "D&D 4", "id": "edition_dnd_4"},
        {"edition": "D&D 3.5", "id": "edition_dnd_3_5"},
        {"edition": "D&D 3", "id": "edition_dnd_3"},
        {"edition": "D&D 2", "id": "edition_dnd_2"},
        {"edition": "Advanced D&D", "id": "edition_dnd_advanced"},
        {"edition": "Classic D&D", "id": "edition_dnd_classic"},
    ]
    return {
        "dnd_editions": dnd_editions,
    }


async def get_players_number_requirements(**kwargs):
    players_number_requirements = [
        {"players_number": "1", "id": "players_number_1", "minimum": 1, "maximum": 1},
        {"players_number": "2", "id": "players_number_2", "minimum": 2, "maximum": 2},
        {"players_number": "3", "id": "players_number_3", "minimum": 3, "maximum": 3},
        {"players_number": "4", "id": "players_number_4", "minimum": 4, "maximum": 4},
        {"players_number": "5", "id": "players_number_5", "minimum": 5, "maximum": 5},
        {"players_number": "6", "id": "players_number_6", "minimum": 6, "maximum": 6},
        {"players_number": "2-3", "id": "players_number_2_3", "minimum": 2, "maximum": 3},
        {"players_number": "3-4", "id": "players_number_3_4", "minimum": 3, "maximum": 4},
        {"players_number": "3-5", "id": "players_number_3_5", "minimum": 3, "maximum": 5},
        {"players_number": "4-6", "id": "players_number_4_6", "minimum": 4, "maximum": 6},
    ]
    return {
        "players_number_requirements": players_number_requirements,
    }


async def get_age_requirements(**kwargs):
    age_requirements = [
        {"age": "Любой", "id": "age_14_99", "minimum": 14, "maximum": 99},
        {"age": "14-17", "id": "age_14_17", "minimum": 14, "maximum": 17},
        {"age": "18+", "id": "age_18_99", "minimum": 18, "maximum": 99},
        {"age": "18-25", "id": "age_18_25", "minimum": 18, "maximum": 25},
        {"age": "25+", "id": "age_25_99", "minimum": 25, "maximum": 99},
    ]
    return {
        "age_requirements": age_requirements,
    }


# Create new game (ONSTART)
async def create_new_game_if_needed(data: dict[str, Any], dialog_manager: DialogManager):
    mode = dialog_manager.start_data.get("mode")
    if mode != "register":
        old_game_id = dialog_manager.start_data.get("game_id")
        if old_game_id is None:
            logging.critical("no game id was provided")
            await dialog_manager.done()
            return

        dialog_manager.dialog_data["game_id"] = old_game_id
        dialog_manager.dialog_data["mode"] = mode
        return

    # TODO: this can cause some bugs
    new_game_id = await generate_random_id()
    while not games.get(new_game_id) is None:
        new_game_id = await generate_random_id()

    dialog_manager.dialog_data["game_id"] = new_game_id
    games[new_game_id] = default_game
    user["master"]["games"].append(new_game_id)

    dialog_manager.dialog_data["default_data"] = {}
    dialog_manager.dialog_data["default_settings"] = "no"


# SELECTORS
def is_dnd_chosen(data: Optional[dict], widget: Optional[Whenable], dialog_manager: Optional[DialogManager]):
    current_game = get_game_by_id_in_dialog_data_not_async(dialog_manager)
    if current_game is None:
        return False

    return current_game.get("system") == "D&D"


def generate_need_to_display_default_value(value: str):
    def need_to_display_default_value(data: Optional[dict], widget: Optional[Whenable],
                                 dialog_manager: Optional[DialogManager]):
        default_data = dialog_manager.dialog_data.get("default_data")
        if default_data is None:
            logging.critical("no default data was provided")
            return False

        default_settings = dialog_manager.dialog_data.get("default_settings")
        if default_settings is None:
            logging.critical("no default settings was provided")
            return False

        return default_settings == "choose" and default_data.get(f"default_{value}", "") != ""

    return need_to_display_default_value


need_to_display_default_cost = generate_need_to_display_default_value("cost")


need_to_display_default_place = generate_need_to_display_default_value("place")


need_to_display_default_platform = generate_need_to_display_default_value("platform")


need_to_display_default_requirements = generate_need_to_display_default_value("requirements")


# Saving game settings (ONCLICK)
async def save_default_settings(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    _, default_settings = button.widget_id.split("_", 1)
    allowed_defaults = ["all", "choose", "no"]

    if not default_settings in allowed_defaults:
        await raise_keyboard_error(callback, "применение значений по умолчанию")
        return

    dialog_manager.dialog_data["default_settings"] = default_settings
    if default_settings != "no":
        try:
            dialog_manager.dialog_data["default_data"] = {
                "default_cost": user["master"]["cost"],
                "default_place": user["master"]["place"],
                "default_platform": user["master"]["platform"],
                "default_requirements": user["master"]["requirements"]
            }
        except KeyError:
            logging.critical("cannot get default settings")
            await dialog_manager.done()
            return

    next_states = {"edit": None, "register": GameCreation.typing_title}
    await switch_state(dialog_manager, next_states)


async def save_title(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    try:
        games[game_id]["title"] = message.text
    except KeyError:
        logging.critical("cannot set game title")
        await dialog_manager.done()
        return

    next_states = {"edit": None, "register": GameCreation.choosing_cost}
    if await is_need_to_be_skipped(dialog_manager, "default_cost"):
        default_cost = await get_default_cost(dialog_manager)

        games[game_id]["cost"] = default_cost
        next_states = {"edit": None, "register": GameCreation.choosing_format}

    await switch_state(dialog_manager, next_states)


async def save_cost(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    next_states = {"edit": None, "register": None}

    game_id = await get_game_id_in_dialog_data(dialog_manager)
    if button.widget_id == "cost_free":
        games[game_id]["cost"] = "Бесплатно"
        next_states = {"edit": None, "register": GameCreation.choosing_format}
    elif button.widget_id == "cost_paid":
        games[game_id]["cost"] = "Платно"
        next_states = {"edit": GameCreation.typing_cost, "register": GameCreation.typing_cost}
    elif button.widget_id == "cost_default":
        default_cost = await get_default_cost(dialog_manager)

        games[game_id]["cost"] = default_cost
        next_states = {"edit": None, "register": GameCreation.choosing_format}
    else:
        await raise_keyboard_error(callback, "стоимость")
        return

    await switch_state(dialog_manager, next_states)


async def save_cost_number(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)
    games[game_id]["cost"] = games[game_id]["cost"] + ". " + message.text

    next_states = {"edit": None, "register": GameCreation.choosing_format}
    await switch_state(dialog_manager, next_states)


async def save_format(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    format_by_id = {
        "format_online_game": "Онлайн",
        "format_offline_game": "Оффлайн",
        "format_text_game": "Текстовая игра",
    }
    session_format = format_by_id.get(button.widget_id)

    if session_format is None:
        await raise_keyboard_error(callback, "формат")
        return
    games[game_id]["format"] = session_format

    if session_format == "Оффлайн":
        next_states = {"edit": GameCreation.typing_place, "register": GameCreation.typing_place}
        if await is_need_to_be_skipped(dialog_manager, "default_place"):
            default_place = await get_default_place(dialog_manager)

            games[game_id]["place"] = default_place
            next_states = {"edit": None, "register": GameCreation.typing_time}
    else:
        next_states = {"edit": GameCreation.typing_platform, "register": GameCreation.typing_platform}
        if await is_need_to_be_skipped(dialog_manager, "default_platform"):
            default_platform = await get_default_platform(dialog_manager)

            games[game_id]["platform"] = default_platform
            next_states = {"edit": None, "register": GameCreation.typing_time}

    await switch_state(dialog_manager, next_states)


save_place = generate_save_message_from_user_no_formatting_game("place", {"edit": None, "register": GameCreation.typing_time})


# TODO: generate default savers
async def save_default_place(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    default_place = await get_default_place(dialog_manager)

    games[game_id]["place"] = default_place
    next_states = {"edit": None, "register": GameCreation.typing_time}

    await switch_state(dialog_manager, next_states)


save_platform = generate_save_message_from_user_no_formatting_game("platform", {"edit": None, "register": GameCreation.typing_time})


async def save_default_platform(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    default_platform = await get_default_platform(dialog_manager)

    games[game_id]["platform"] = default_platform
    next_states = {"edit": None, "register": GameCreation.typing_time}

    await switch_state(dialog_manager, next_states)


save_time = generate_save_message_from_user_no_formatting_game("time", {"edit": None, "register": GameCreation.choosing_type})


async def save_type(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    type_by_id = {
        "type_oneshot_game": "Ваншот",
        "type_campaign_game": "Кампания",
    }
    session_type = type_by_id.get(button.widget_id)

    if session_type is None:
        await raise_keyboard_error(callback, "тип")
        return
    games[game_id]["type"] = session_type

    next_states = {"edit": None, "register": GameCreation.choosing_system}
    await switch_state(dialog_manager, next_states)


async def save_system(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, item_id: str):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    data = await get_systems()
    item = await get_item_by_key(data, "popular_systems", "id", item_id, callback, "систему", False, False)
    games[game_id]["system"] = item["system"]

    next_states = {"edit": GameCreation.choosing_edition, "register": GameCreation.choosing_edition}
    await switch_state(dialog_manager, next_states)



async def save_system_from_user(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)
    user_system = message.text.strip(". \"\'")

    data = await get_systems()
    item = await get_item_by_key(data, "popular_systems", "system", user_system, message, "город", True, True)

    if not item is None:
        games[game_id]["system"] = item["system"]
    else:
        games[game_id]["system"] = user_system

    next_states = {"edit": GameCreation.choosing_edition, "register": GameCreation.choosing_edition}
    await switch_state(dialog_manager, next_states)


async def save_edition(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, item_id: str):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    data = await get_editions()
    item = await get_item_by_key(data, "dnd_editions", "id", item_id, callback, "издание", False, False)
    games[game_id]["system"] = item["edition"]

    next_states = {"edit": None, "register": GameCreation.choosing_players_number}
    await switch_state(dialog_manager, next_states)


async def save_edition_from_user(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    user_edition = message.text.strip(". \"\'")
    current_system = games.get(game_id, {}).get("system", "")
    games[game_id]["system"] = current_system + "; " + user_edition

    next_states = {"edit": None, "register": GameCreation.choosing_players_number}
    await switch_state(dialog_manager, next_states)


async def save_players_number(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, item_id: str):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    data = await get_players_number_requirements()
    item = await get_item_by_key(data, "players_number_requirements", "id", item_id, callback, "число игроков", False, False)
    games[game_id]["min_players_number"] = item["minimum"]
    games[game_id]["max_players_number"] = item["maximum"]

    next_states = {"edit": None, "register": GameCreation.choosing_age}
    await switch_state(dialog_manager, next_states)


save_players_number_from_user = generate_save_diapason_from_user(MIN_PLAYERS_NUMBER, MAX_PLAYERS_NUMBER, "min_players_number", "max_players_number", {"edit": None, "register": GameCreation.choosing_age}, False)


async def save_age(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, item_id: str):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    data = await get_age_requirements()
    item = await get_item_by_key(data, "age_requirements", "id", item_id, callback, "возрастные ограничения", False, False)
    games[game_id]["min_age"] = item["minimum"]
    games[game_id]["max_age"] = item["maximum"]

    next_states = {"edit": None, "register": GameCreation.typing_requirements}
    if await is_need_to_be_skipped(dialog_manager, "default_requirements"):
        game_id = await get_game_id_in_dialog_data(dialog_manager)

        default_requirements = await get_default_requirements(dialog_manager)

        games[game_id]["requirements"] = default_requirements
        next_states = {"edit": None, "register": GameCreation.typing_description}

    await switch_state(dialog_manager, next_states)


save_age_from_user = generate_save_diapason_from_user(MIN_AGE, MAX_AGE, "min_age", "max_age", {"edit": None, "register": GameCreation.typing_requirements}, True)


save_requirements = generate_save_message_from_user_no_formatting_game("requirements", {"edit": None, "register": GameCreation.typing_description})


async def save_default_requirements(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    default_requirements = await get_default_requirements(dialog_manager)

    games[game_id]["requirements"] = default_requirements
    next_states = {"edit": None, "register": GameCreation.typing_description}

    await switch_state(dialog_manager, next_states)

save_description = generate_save_message_from_user_no_formatting_game("description", {"edit": None, "register": None})


# Delete game if needed (ONCLICK)
async def delete_current_game(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    try:
        user["master"]["games"].remove(game_id)
    except ValueError:
        logging.critical("missing game_id ({}) in user games".format(game_id))

    games.pop(game_id, None)


# Game registration dialog
game_creation_dialog = Dialog(
    Window(
        Const("При заполнении анкеты мастера, вы установили значения по умолчанию.\nДля каких полей их использовать? "),
        Button(Const("Для всех"), id="default_all", on_click=save_default_settings),
        Button(Const("Выбирать для каждого поля"), id="default_choose", on_click=save_default_settings),
        Button(Const("Ни для каких"), id="default_no", on_click=save_default_settings),
        state=GameCreation.choosing_default,
    ),
    Window(
        Const("Введите название для вашей игры."),
        Jinja("\n<b>Текущее значение</b>: {{title}}", when=need_to_display_current_value),

        MessageInput(func=save_title, content_types=[ContentType.TEXT]),

        Cancel(Const("Отменить"), on_click=delete_current_game, when=is_register_mode),
        go_back_when_edit_mode,
        state=GameCreation.typing_title,
    ),
    Window(
        Const("Какие игры вы планируете проводить?"),
        Jinja("\n<b>Текущее значение</b>: {{cost}}", when=need_to_display_current_value),
        Jinja("\n<b>Значение по умолчанию</b>: {{default_cost}}", when=need_to_display_default_cost),

        Button(Const("Бесплатные"), id="cost_free", on_click=save_cost),
        Button(Const("Платные"), id="cost_paid", on_click=save_cost),
        Button(Const("Использовать значение по умолчанию"), id="cost_default", on_click=save_cost, when=need_to_display_default_cost),

        go_back_when_edit_mode,
        state=GameCreation.choosing_cost,
        getter=get_default_cost,
    ),
    Window(
        Const("Сколько вы планируете брать за проведение сессии? Введите ответ в свободной форме."),
        Jinja("\n<b>Текущее значение</b>: {{cost}}", when=need_to_display_current_value),

        MessageInput(func=save_cost_number, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=GameCreation.typing_cost,
    ),
    Window(
        Const("В каком формате будет проводиться игра?"),
        Jinja("\n<b>Текущее значение</b>: {{format}}", when=need_to_display_current_value),

        Button(Const("Онлайн"), id="format_online_game", on_click=save_format),
        Button(Const("Оффлайн"), id="format_offline_game", on_click=save_format),
        Button(Const("Текстовая игра"), id="format_text_game", on_click=save_format),

        go_back_when_edit_mode,
        state=GameCreation.choosing_format,
    ),
    Window(
        Const("Где вы планируете проводить игры?\nПожалуйста, не приглашайте игроков к себе домой, это может быть опасно, сессии нужно проводить в публичных местах.\nТакже не стоит указывать точный адрес, эта информация будет доступна всем пользователям бота. Лучше всего указать район."),
        Jinja("\n<b>Текущее значение</b>: {{place}}", when=need_to_display_current_value),
        Jinja("\n<b>Значение по умолчанию</b>: {{default_place}}", when=need_to_display_default_place),

        MessageInput(func=save_place, content_types=[ContentType.TEXT]),
        Button(Const("Использовать значение по умолчанию"), id="place_default", on_click=save_default_place, when=need_to_display_default_place),

        go_back_when_edit_mode,
        state=GameCreation.typing_place,
        getter=get_default_place,
    ),
    Window(
        Const("Какую платформу вы будете использовать для проведения игр? Укажите её и способ общения во время игры."),
        Jinja("\n<b>Текущее значение</b>: {{platform}}", when=need_to_display_current_value),
        Jinja("\n<b>Значение по умолчанию</b>: {{default_platform}}", when=need_to_display_default_platform),

        MessageInput(func=save_platform, content_types=[ContentType.TEXT]),
        Button(Const("Использовать значение по умолчанию"), id="platform_default", on_click=save_default_platform, when=need_to_display_default_platform),

        go_back_when_edit_mode,
        state=GameCreation.typing_platform,
        getter=get_default_platform,
    ),
    Window(
        Const("Когда вы планируете проводить сессии? Напишите удобное для вас время в свободной форме."),
        Jinja("\n<b>Текущее значение</b>: {{time}}", when=need_to_display_current_value),

        MessageInput(func=save_time, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=GameCreation.typing_time,
    ),
    Window(
        Const("Сколько сессий вы планируете провести? Будет ли это ваншот или полноценная кампания?"),
        Jinja("\n<b>Текущее значение</b>: {{type}}", when=need_to_display_current_value),

        Button(Const("Ваншот"), id="type_oneshot_game", on_click=save_type),
        Button(Const("Кампания"), id="type_campaign_game", on_click=save_type),

        go_back_when_edit_mode,
        state=GameCreation.choosing_type,
    ),
    Window(
        Const("По какой системе вы будете вести игру?"),
        Jinja("\n<b>Текущее значение</b>: {{system}}", when=need_to_display_current_value),

        Column(Select(
            text=Format("{item[system]}"),
            id="systems_select_game_creation",
            item_id_getter=lambda item: item["id"],
            on_click=save_system,
            items="popular_systems",
        )),
        MessageInput(func=save_system_from_user, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        getter=get_systems,
        state=GameCreation.choosing_system,
    ),
    Window(
        Multi(
            Const("Какое издание вы планируете использовать? Введите ответ в свободной форме"),
            Const("или выберите один из предоставленных вариантов", when=is_dnd_chosen),
            Const("."),
            sep='',
        ),
        Jinja("\n<b>Текущее значение</b>: {{system}}", when=need_to_display_current_value),

        Column(Select(
            text=Format("{item[edition]}"),
            id="edition_select_game_creation",
            item_id_getter=lambda item: item["id"],
            on_click=save_edition,
            items="dnd_editions",
            when=is_dnd_chosen,
        )),
        MessageInput(func=save_edition_from_user, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        getter=get_editions,
        state=GameCreation.choosing_edition,
    ),
    Window(
        Const("На сколько игроков рассчитано ваше приключение? Выберите одну из предоставленных опций или укажите свою.\nВведите минимальное и максимальное количество через черту, например: 3-5, 2+, 6-"),
        Jinja("\n<b>Текущее значение</b>: {{min_players_number}}-{{max_players_number}}", when=need_to_display_current_value_and_min_and_max_provided_players_number),
        Jinja("\n<b>Текущее значение</b>: {{min_players_number}}+", when=need_to_display_current_value_and_only_min_provided_players_number),
        Jinja("\n<b>Текущее значение</b>: {{max_players_number}}-", when=need_to_display_current_value_and_only_max_provided_players_number),
        Jinja("\n<b>Текущее значение</b>: Отсутствуют", when=need_to_display_current_value_and_nothing_provided_players_number),

        Column(Select(
            text=Format("{item[players_number]}"),
            id="players_number_select_game_creation",
            item_id_getter=lambda item: item["id"],
            items="players_number_requirements",
            on_click=save_players_number,
        )),
        MessageInput(func=save_players_number_from_user, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=GameCreation.choosing_players_number,
        getter=get_players_number_requirements,
    ),
    Window(
        Const("Игроков какого возраста вы ищите? Выберите одну из предоставленных опций или укажите свою.\nВведите минимальный и максимальный возраст через черту, например: 30-35, 25+, 40-"),
        Jinja("\n<b>Текущее значение</b>: {{min_age}}-{{max_age}}", when=need_to_display_current_value_and_min_and_max_provided_age),
        Jinja("\n<b>Текущее значение</b>: {{min_age}}+", when=need_to_display_current_value_and_only_min_provided_age),
        Jinja("\n<b>Текущее значение</b>: {{max_age}}-", when=need_to_display_current_value_and_only_max_provided_age),
        Jinja("\n<b>Текущее значение</b>: Отсутствуют", when=need_to_display_current_value_and_nothing_provided_age),

        Column(Select(
            text=Format("{item[age]}"),
            id="age_select_game_creation",
            item_id_getter=lambda item: item["id"],
            items="age_requirements",
            on_click=save_age,
        )),
        MessageInput(func=save_age_from_user, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=GameCreation.choosing_age,
        getter=get_age_requirements,
    ),
    Window(
        Const("Каким требованиям должны удовлетворять игроки, которых вы ищите?"),
        Jinja("\n<b>Текущее значение</b>: {{requirements}}", when=need_to_display_current_value),
        Jinja("\n<b>Значение по умолчанию</b>: {{default_requirements}}", when=need_to_display_default_requirements),

        MessageInput(func=save_requirements, content_types=[ContentType.TEXT]),
        Button(Const("Использовать значение по умолчанию"), id="requirements_default", on_click=save_default_requirements, when=need_to_display_default_requirements),

        go_back_when_edit_mode,
        state=GameCreation.typing_requirements,
        getter=get_default_requirements,
    ),
    Window(
        Const("Что ждёт игроков? В каком сеттинге будут происходить действия? Дайте описание игры."),
        Jinja("\n<b>Текущее значение</b>: {{description}}", when=need_to_display_current_value),

        MessageInput(func=save_description, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=GameCreation.typing_description,
    ),
    on_start=create_new_game_if_needed,
    # getter=get_game_by_id_in_dialog_data,
)