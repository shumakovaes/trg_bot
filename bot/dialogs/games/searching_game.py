import logging
import operator
from typing import Optional, Any
from magic_filter import F

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, get_player_games, get_master_games, \
    get_player_archive, get_master_archive, user, games, users, open_games
from bot.dialogs.games.games_tools import generate_games_list_title_status, generate_games_navigation, \
    generate_check_game, generate_games_list_title, generate_game_description, get_game_by_id_in_dialog_data, \
    get_game_id_in_dialog_data
from bot.dialogs.general_tools import start_game_creation, generate_master_description
from bot.states.games_states import AllGames, GameInspection, GameCreation, SearchingGame


# ON START
async def set_default_filters(data: dict[str, Any], dialog_manager: DialogManager):
    user_id = "id_000000"
    try:
        default_format = users[user_id]["general"]["format"]
        default_payment = users[user_id]["player"]["payment"]
        default_type = "Ваншот и компания"
        default_systems = users[user_id]["player"]["systems"]
        default_age = users[user_id]["general"]["age"]

        dialog_manager.dialog_data["filters"] = {
            "format": default_format,
            "payment": default_payment,
            "type": default_type,
            "systems": default_systems,
            "age": default_age
        }
    except KeyError:
        logging.critical("cannot access user fields by id {}".format(user_id))
        await dialog_manager.done()
        return


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
    if filter_type != "Ваншот и компания" and filter_type != "" and filter_type != game_type:
        return False
    if len(filter_systems) != 0 and not game_system in filter_systems:
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
        games[game_id]["requests"].add(user_id)
    except KeyError:
        logging.critical("cannot get requests for game by id {}".format(game_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    try:
        user["player"]["games"].add(game_id)
    except KeyError:
        logging.critical("cannot get games for user by id {}".format(user_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    # TODO: send notifications to master


# GETTERS
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
            "experience_provided": master["master"]["experience"] != "",
        }
    except KeyError:
        logging.critical("cannot get master fields for user by id {}".format(master_id))

    return {"master_form": master_form}


# Choosing game dialog
searching_game_dialog = Dialog(
    Window(
        Const("Чтобы посмотреть про игру подробнее, введите текстом её номер."),
        generate_games_list_title("available_games"),

        MessageInput(func=check_game_by_id, content_types=[ContentType.TEXT]),

        generate_games_navigation("available_games"),
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
    on_start=set_default_filters,
)
