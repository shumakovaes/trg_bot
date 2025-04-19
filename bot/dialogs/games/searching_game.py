import logging
import operator
from typing import Optional, Any
from magic_filter import F

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager, ChatEvent
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage, Toggle, ManagedToggle, ManagedRadio, Multiselect, ManagedMultiselect

from bot.db.current_requests import get_user_player, get_user_master, get_player_games, get_master_games, \
    get_player_archive, get_master_archive, user, games, users, open_games, popular_systems
from bot.dialogs.games.games_tools import generate_games_list_title_status, generate_games_navigation, \
    generate_check_game, generate_games_list_title, generate_game_description, get_game_by_id_in_dialog_data, \
    get_game_id_in_dialog_data
from bot.dialogs.general_tools import start_game_creation, generate_master_description, get_item_by_key
from bot.states.games_states import AllGames, GameInspection, GameCreation, SearchingGame


# ON START
async def set_default_filters(data: dict[str, Any], dialog_manager: DialogManager):
    user_id = "id_000000"
    try:
        default_format = users[user_id]["general"]["format"]
        default_payment = users[user_id]["player"]["payment"]
        default_type = "Ваншот и кампания"
        default_age = users[user_id]["general"]["age"]
        default_systems = users[user_id]["player"]["systems"]
    except KeyError:
        logging.critical("cannot access user fields by id {}".format(user_id))
        await dialog_manager.done()
        return

    default_user_systems = set()
    wrapped_popular_systems = {"popular_systems": popular_systems}
    systems_multiselect: ManagedMultiselect = dialog_manager.find("systems_multiselect_filter")
    for system in default_systems:
        popular_system = await get_item_by_key(wrapped_popular_systems, "popular_systems", "system", system, None,"системы", True, False)
        if not popular_system is None:
            await systems_multiselect.set_checked(popular_system["id"], True)
        else:
            default_user_systems.add(system)

    dialog_manager.dialog_data["filters"] = {
        "format": default_format,
        "payment": default_payment,
        "type": default_type,
        "systems": default_systems,
        "user_systems": default_user_systems,
        "age": default_age
    }


    default_data = await get_default_options(dialog_manager)

    format_toggle: ManagedRadio = dialog_manager.find("format_choosing")
    if default_format == "":
        await format_toggle.set_checked("format_both_filter")
    else:
        format_filter = await get_item_by_key(default_data, "format_options", "format", default_format, None, "формат", False, False)
        await format_toggle.set_checked(format_filter["id"])


    payment_toggle: ManagedRadio = dialog_manager.find("payment_choosing")
    if default_payment == "":
        await payment_toggle.set_checked("payment_both_filter")
    else:
        payment_filter = await get_item_by_key(default_data, "payment_options", "payment", default_payment, None, "оплата", False, False)
        await payment_toggle.set_checked(payment_filter["id"])

    type_toggle: ManagedRadio = dialog_manager.find("type_choosing")
    if default_type == "":
        await type_toggle.set_checked("type_both_filter")
    else:
        type_filter = await get_item_by_key(default_data, "type_options", "type", default_type, None, "тип", False, False)
        await type_toggle.set_checked(type_filter["id"])

    age_toggle: ManagedRadio = dialog_manager.find("age_choosing")
    if default_age == 0:
        await age_toggle.set_checked("age_do_not_check_filter")
    else:
        await age_toggle.set_checked("age_check_filter")


# HELPERS
async def is_passes_filters(dialog_manager: DialogManager, game_id: str):
    try:
        filter_format = dialog_manager.dialog_data["filters"]["format"]
        filter_payment = dialog_manager.dialog_data["filters"]["payment"]
        filter_type = dialog_manager.dialog_data["filters"]["type"]
        filter_systems = dialog_manager.dialog_data["filters"]["systems"]
        filter_age = dialog_manager.dialog_data["filters"]["age"]
    except KeyError:
        logging.critical("filters are missing")
        await dialog_manager.done()
        return

    try:
        game_format = games[game_id]["format"]
        game_cost = games[game_id]["cost"]
        game_type = games[game_id]["type"]
        game_system = games[game_id]["system"]
        game_min_age = games[game_id]["min_age"]
        game_max_age = games[game_id]["max_age"]
    except KeyError:
        logging.critical("cannot access game fields by id".format(game_id))
        await dialog_manager.done()
        return

    if filter_format != "Оффлайн и Онлайн" and filter_format != "" and filter_format != game_format:
        return False
    if filter_payment != "Бесплатные и платные" and filter_payment != "":
        if game_cost == "Бесплатно":
            if game_format == "Только платные":
                return False
        else:
            if filter_payment == "Только бесплатные":
                return False
    if filter_type != "Ваншот и кампания" and filter_type != "" and filter_type != game_type:
        return False
    if len(filter_systems) != 0 and not game_system in filter_systems and not ("D&D" in game_system and "D&D" in filter_systems):
        return False
    if filter_age != 0 and (filter_age < game_min_age or filter_age > game_max_age):
        return False

    return True


# GETTERS
async def get_available_games(dialog_manager: DialogManager, **kwargs):
    available_games = []
    user_id = "id_000000"

    try:
        user_systems = users[user_id]["player"]["systems"]
        user_age = users[user_id]["general"]["age"]
        user_format = users[user_id]["general"]["format"]
        user_payment = users[user_id]["player"]["payment"]
        user_city = users[user_id]["general"]["city"]
    except KeyError:
        logging.critical("data for user by id {} is missing".format(user_id))
        await dialog_manager.done()
        return


    async def get_distance_from_user_to_game(game_id: str):
        dist = 0

        try:
            master_id = games[game_id]["master"]
            master_rating = users[master_id]["master"]["rating"]
            master_city = users[master_id]["general"]["city"]
            game_format = games[game_id]["format"]
            game_cost = games[game_id]["cost"]
            game_system = games[game_id]["system"]
            game_min_age = games[game_id]["min_age"]
            game_max_age = games[game_id]["max_age"]
        except KeyError:
            logging.critical("games data for game by id {} is missing".format(game_id))
            await dialog_manager.done()
            return

        if game_format == "Оффлайн":
            if user_format == "Онлайн":
                dist += 5
            if master_city != user_city:
                dist += 10
        if game_format == "Онлайн" and user_format == "Оффлайн":
                dist += 4

        if user_age > game_max_age:
            dist += min(10, user_age - game_max_age)
        if user_age < game_min_age:
            dist += min(10, game_min_age - user_age)

        if user_payment == "Только бесплатные" and game_cost != "Бесплатно":
            dist += 6
        if user_payment == "Только платные" and game_cost == "Бесплатно":
            dist += 3

        if master_rating > 4.0:
            dist -= 1
        if master_rating > 4.5:
            dist -= 2
        if master_rating != 0:
            if master_rating <= 2.0:
                dist += 2
            if master_rating <= 3.0:
                dist += 2

        if "D&D" in game_system and "D&D" in user_systems:
            dist -= 4
        if game_system in user_systems:
            dist -= 4

        return dist


    for game_id in open_games:
        if await is_passes_filters(dialog_manager, game_id):
            game_distance_and_title = (await get_distance_from_user_to_game(game_id), {"title": games[game_id]["title"], "id": game_id})
            available_games.append(game_distance_and_title)

    available_games.sort(key=operator.itemgetter(0))

    available_games_ids = [item[1]["id"] for item in available_games]
    dialog_manager.dialog_data["available_games_ids"] = available_games_ids

    return {"games": [item[1] for item in available_games]}


async def get_master_by_game_id_in_dialog_data(dialog_manager: DialogManager, **kwargs):
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    try:
        master_id = games[game_id]["master"]
    except KeyError:
        logging.critical("cannot get master for game by id {}".format(game_id))
        await dialog_manager.done()
        return

    master = users.get(master_id)
    if master is None:
        logging.critical("cannot get user by id {}".format(master_id))
        await dialog_manager.done()

    master_form = {}
    try:
        master_form = {
            "name": master["general"]["name"],
            "age": master["general"]["age"],
            "city": master["general"]["city"],
            "time_zone": master["general"]["time_zone"],
            "role": master["general"]["role"],
            "format": master["general"]["format"],
            "about_info": master["general"]["about_info"],
            "experience": master["master"]["experience"],
            "rating": master["master"]["rating"],
            "experience_provided": master["master"]["experience"] != "",
            "has_rating": master["master"]["rating"] != 0,
        }
    except KeyError:
        logging.critical("cannot get master fields for user by id {}".format(master_id))

    return master_form


async def get_systems(dialog_manager: DialogManager, **kwargs):
    try:
        systems = {
            "user_systems": dialog_manager.dialog_data["filters"]["user_systems"],
            "popular_systems": popular_systems,
        }
    except KeyError:
        logging.critical("cannot access user_systems")
        await dialog_manager.done()
        return

    return systems


async def get_default_options(dialog_manager: DialogManager, **kwargs):
    format_options = [
        {"format": "Онлайн", "id": "format_online_filter"},
        {"format": "Оффлайн", "id": "format_offline_filter"},
        {"format": "Оффлайн и Онлайн", "id": "format_both_filter"},
    ]
    payment_options = [
        {"payment": "Только бесплатные", "id": "payment_free_filter"},
        {"payment": "Только платные", "id": "payment_paid_filter"},
        {"payment": "Бесплатные и платные", "id": "payment_both_filter"},
    ]
    type_options = [
        {"type": "Ваншот", "id": "type_oneshot_filter"},
        {"type": "Кампания", "id": "type_campaign_filter"},
        {"type": "Ваншот и кампания", "id": "type_both_filter"},
    ]
    age_options = [
        {"age": "Показывать только подходящие", "id": "age_check_filter"},
        {"age": "Показывать все", "id": "age_do_not_check_filter"},
    ]

    default_options = {
        "format_options": format_options,
        "payment_options": payment_options,
        "type_options": type_options,
        "age_options": age_options
    }

    return default_options


# ONCLICK
async def check_game_by_id(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    str_index = message.text.strip(" .;'\"")
    if str_index is None or not str_index.isdigit():
        await message.answer("Вам необходимо ввести число.")
        return

    index = int(str_index)
    try:
        games_number = len(dialog_manager.dialog_data["available_games_ids"])
    except KeyError:
        logging.critical("available_games_ids is missing in dialog data")
        await dialog_manager.done()
        return

    if index > games_number or index < 0:
        await message.answer("Введите число, соответствующее индексу игры (от 1 до {}).".format(games_number))

    dialog_manager.dialog_data["game_id"] = dialog_manager.dialog_data["available_games_ids"][index - 1]
    await dialog_manager.switch_to(SearchingGame.checking_specific_game)


async def send_request(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user_id = "id_000000"
    game_id = await get_game_id_in_dialog_data(dialog_manager)

    try:
        current_players = games[game_id]["players"]
        current_master = games[game_id]["master"]
    except KeyError:
        logging.critical("cannot get players for game id {}".format(game_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    if user_id in current_players:
        await callback.answer("Ваша заявка в эту игру уже была принята.")
        return
    if user_id == current_master:
        await callback.answer("Вы являетесь мастером этой игры.")
        return

    try:
        games[game_id]["requests"].append(user_id)
    except KeyError:
        logging.critical("cannot get requests for game by id {}".format(game_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    try:
        user["player"]["games"].append(game_id)
    except KeyError:
        logging.critical("cannot get games for user by id {}".format(user_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    # TODO: send notifications to master


async def save_filters(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data = await get_default_options(dialog_manager)

    format_toggle: ManagedRadio = dialog_manager.find("format_choosing")
    if format_toggle is None:
        logging.critical("cannot get format toggle")
        await dialog_manager.done()
        return
    format_id = format_toggle.get_checked()
    if not format_id is None:
        format_filter = await get_item_by_key(data, "format_options", "id", format_id, callback, "формат", False, False)
        dialog_manager.dialog_data["filters"]["format"] = format_filter["format"]

    payment_toggle: ManagedRadio = dialog_manager.find("payment_choosing")
    if payment_toggle is None:
        logging.critical("cannot get payment toggle")
        await dialog_manager.done()
        return
    payment_id = payment_toggle.get_checked()
    if not payment_id is None:
        payment_filter = await get_item_by_key(data, "payment_options", "id", payment_id, callback, "оплата", False, False)
        dialog_manager.dialog_data["filters"]["payment"] = payment_filter["payment"]

    type_toggle: ManagedRadio = dialog_manager.find("type_choosing")
    if type_toggle is None:
        logging.critical("cannot get type toggle")
        await dialog_manager.done()
        return
    type_id = type_toggle.get_checked()
    if not type_id is None:
        type_filter = await get_item_by_key(data, "type_options", "id", type_id, callback, "тип", False, False)
        dialog_manager.dialog_data["filters"]["type"] = type_filter["type"]

    age_toggle: ManagedRadio = dialog_manager.find("age_choosing")
    if age_toggle is None:
        logging.critical("cannot get age toggle")
        await dialog_manager.done()
        return
    age_id = age_toggle.get_checked()
    if not age_id is None:
        if age_id == "age_check_filter":
            user_id = "id_000000"
            try:
                dialog_manager.dialog_data["filters"]["age"] = users[user_id]["general"]["age"]
            except KeyError:
                logging.critical("cannot get age for user by id {}".format(user_id))
        elif age_id == "age_do_not_check_filter":
            dialog_manager.dialog_data["filters"]["age"] = 0
        else:
            logging.critical("unexpected age toggle id")
            await dialog_manager.done()
            return


async def clear_user_systems(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    try:
        dialog_manager.dialog_data["filters"]["user_systems"].clear()
    except KeyError:
        logging.critical("cannot access user_systems filter")
        await dialog_manager.done()
        return


async def clear_systems(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await clear_user_systems(callback, button, dialog_manager)

    systems_multiselect: ManagedMultiselect = dialog_manager.find("systems_multiselect_filter")
    await systems_multiselect.reset_checked()


async def save_user_systems(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    user_systems = list(message.text.split(','))
    user_systems = [system.strip(" \'\";,") for system in user_systems]

    data = await get_systems(dialog_manager)
    for system in user_systems:
        item = await get_item_by_key(data, "popular_systems", "system", system, message, "системы", True, True)

        if not item is None:
            systems_multiselect: ManagedMultiselect = dialog_manager.find("systems_multiselect_filter")
            await systems_multiselect.set_checked(item["id"], True)
        else:
            try:
                dialog_manager.dialog_data["filters"]["user_systems"].add(system)
            except KeyError:
                logging.critical("cannot access user_systems filter")
                await dialog_manager.done()
                return


async def save_systems(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    try:
        dialog_manager.dialog_data["filters"]["systems"] = {system for system in dialog_manager.dialog_data["filters"]["user_systems"]}
    except KeyError:
        logging.critical("cannot access systems filter")
        await dialog_manager.done()
        return

    systems_multiselect: ManagedMultiselect = dialog_manager.find("systems_multiselect_filter")
    data = await get_systems(dialog_manager)
    systems = data["popular_systems"]

    for system in systems:
        if systems_multiselect.is_checked(system["id"]):
            dialog_manager.dialog_data["filters"]["systems"].add(system["system"])


# Choosing game dialog
searching_game_dialog = Dialog(
    Window(
        Const("Чтобы посмотреть про игру подробнее, введите текстом её номер."),
        generate_games_list_title("available_games"),

        MessageInput(func=check_game_by_id, content_types=[ContentType.TEXT]),

        generate_games_navigation("available_games"),
        SwitchTo(Const("Настроить фильтры"), id="filters_settings", state=SearchingGame.checking_filters),
        Cancel(text=Const("Выйти")),
        getter=get_available_games,
        state=SearchingGame.checking_open_games,
    ),
    Window(
        generate_game_description(False),

        SwitchTo(Const("Анкета мастера"), id="master_form", state=SearchingGame.checking_master_form),
        Button(Const("Подать заявку"), id="send_request", on_click=send_request),

        SwitchTo(Const("Назад"), id="back_to_all_games_from_specific_game", state=SearchingGame.checking_open_games),
        getter=get_game_by_id_in_dialog_data,
        state=SearchingGame.checking_specific_game,
    ),
    Window(
        generate_master_description(),

        SwitchTo(Const("Описание игры"), id="game_description", state=SearchingGame.checking_specific_game),
        Button(Const("Подать заявку"), id="send_request", on_click=send_request),

        SwitchTo(Const("Назад"), id="back_to_all_games_from_master_form", state=SearchingGame.checking_open_games),
        getter=get_master_by_game_id_in_dialog_data,
        state=SearchingGame.checking_master_form,
    ),
    Window(
        Const("Это параметры, по которым происходит фильтрация игр. По умолчанию они установлены согласно вашему профилю."),
        Toggle(
            Format("Формат: {item[format]}"),
            id="format_choosing",
            items="format_options",
            item_id_getter=lambda item: item["id"],
        ),
        Toggle(
            Format("Оплата: {item[payment]}"),
            id="payment_choosing",
            items="payment_options",
            item_id_getter=lambda item: item["id"],
        ),
        Toggle(
            Format("Тип: {item[type]}"),
            id="type_choosing",
            items="type_options",
            item_id_getter=lambda item: item["id"],
        ),
        Toggle(
            Format("Возраст: {item[age]}"),
            id="age_choosing",
            items="age_options",
            item_id_getter=lambda item: item["id"],
        ),
        SwitchTo(Const("Выбрать системы"), id="checking_systems_filter", state=SearchingGame.checking_systems_filter),

        SwitchTo(Const("Сохранить"), id="save_filters_and_back_to_all_games_from_filters", on_click=save_filters, state=SearchingGame.checking_open_games),
        getter=get_default_options,
        state=SearchingGame.checking_filters,
    ),
    Window(
        Const(
            "Выберите системы, по которым будет проводиться фильтрация.\nВсе системы, которых нет в списке, вы можете указать, отправив их ответным сообщением через запятую."),

        Multi(
            Format("<b>Добавленные вручную системы</b>: "),
            List(
                Jinja("{{item}}"),
                items="user_systems",
                sep=", "
            ),
            sep="",
        ),
        Column(Multiselect(
            checked_text=Format("✓ {item[system]}"),
            unchecked_text=Format("{item[system]}"),
            id="systems_multiselect_filter",
            item_id_getter=lambda item: item["id"],
            items="popular_systems",
        )),
        Button(Const("Очистить добавленные вручную"), id="clear_user_systems", on_click=clear_user_systems),
        Button(Const("Очистить все"), id="clear_systems", on_click=clear_systems),
        SwitchTo(Const("Сохранить"), id="save_systems_and_back_to_checking_filters_from_systems", state=SearchingGame.checking_filters, on_click=save_systems),
        MessageInput(func=save_user_systems, content_types=[ContentType.TEXT]),

        getter=get_systems,
        state=SearchingGame.checking_systems_filter,
    ),
    on_start=set_default_filters,
)
