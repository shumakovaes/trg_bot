import logging
from typing import Any

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage, ListGroup

from bot.db.current_requests import get_user_player, get_user_master, games, user, users, open_games
from bot.dialogs.games.games_tools import generate_game_description, get_game_by_id_in_start_data, \
    get_game_by_id_in_dialog_data, get_game_by_id, is_game_offline, is_game_online, get_game_id_in_dialog_data, \
    get_game_by_id_in_dialog_data_for_displaying, get_game_by_id_in_dialog_data_not_async
from bot.dialogs.general_tools import generate_player_description
from bot.states.games_states import AllGames, GameInspection, GameCreation


# HELPERS
async def get_game_id_and_rights(dialog_manager: DialogManager):
    game_id = dialog_manager.start_data.get("game_id")
    rights = dialog_manager.start_data.get("rights")

    if game_id is None:
        logging.critical("game_id is missing")
        return
    if rights is None:
        logging.critical("rights are missing")
        return

    return game_id, rights


async def get_folder(dialog_manager: DialogManager):
    folder = dialog_manager.dialog_data.get("folder")

    if folder is None:
        logging.critical("folder is missing")
        return

    return folder


async def delete_game_from_user(user_id: str, role: str, games_list: str, game_id: str, dialog_manager: DialogManager):
    try:
        users[user_id][role][games_list].remove(game_id)
    except ValueError:
        logging.critical(
            "cannot find user by id: {} or missing game id ({}) in {} games".format(user_id, game_id, role))
        await dialog_manager.done()
    except KeyError:
        logging.critical("missing expected parameters in user by id: {}".format(user_id))
        await dialog_manager.done()


async def add_game_to_user(user_id: str, role: str, games_list: str, game_id: str, dialog_manager: DialogManager):
    try:
        users[user_id][role][games_list].append(game_id)
    except KeyError:
        logging.critical("missing expected parameters in user by id: {}".format(user_id))
        await dialog_manager.done()


# ON START
async def copy_data_to_dialog_data(data: dict[str, Any], dialog_manager: DialogManager):
    game_id, rights = await get_game_id_and_rights(dialog_manager)
    folder = dialog_manager.start_data.get("folder")

    if folder is None:
        logging.critical("folder is missing")
        return

    dialog_manager.dialog_data["game_id"] = game_id
    dialog_manager.dialog_data["rights"] = rights
    dialog_manager.dialog_data["folder"] = folder

    current_game = await get_game_by_id(dialog_manager, game_id)
    dialog_manager.dialog_data["status"] = current_game["status"]


# GETTERS
async def get_players_by_game_id_in_dialog_data(dialog_manager: DialogManager, **kwargs):
    current_game = await get_game_by_id_in_dialog_data(dialog_manager)

    try:
        players = current_game["players"]
        players_list = [{"name": users[player]["general"]["name"], "id": player} for player in players]
    except KeyError:
        logging.critical("cannot access player list for or players name")
        await dialog_manager.done()
        return

    return {"players": players_list}


async def get_requests_by_game_id_in_dialog_data(dialog_manager: DialogManager, **kwargs):
    current_game = await get_game_by_id_in_dialog_data(dialog_manager)

    try:
        requests = current_game["requests"]
        requests_list = [{"name": users[request]["general"]["name"], "id": request} for request in requests]
    except KeyError:
        logging.critical("cannot access requests list or players name")
        await dialog_manager.done()
        return

    return {"requests": requests_list}


async def get_player_profile_by_id_in_dialog_data(dialog_manager: DialogManager, **kwargs):
    player_id = dialog_manager.dialog_data.get("request_player")
    if player_id is None:
        logging.critical("missing request_player in dialog data")
        await dialog_manager.done()
        return

    player = users.get(player_id)
    if player is None:
        logging.critical("cannot get user by id {}".format(player_id))
        await dialog_manager.done()

    player_form = {}
    try:
        master_form = {
            "name": player["general"]["name"],
            "age": player["general"]["age"],
            "city": player["general"]["city"],
            "time_zone": player["general"]["time_zone"],
            "role": player["general"]["role"],
            "format": player["general"]["format"],
            "about_info": player["general"]["about_info"],
            "experience": player["player"]["experience"],
            "payment": player["player"]["payment"],
            "systems": player["player"]["systems"],
            "rating": player["player"]["rating"],
            "experience_provided": player["player"]["experience"] != "",
            "payment_provided": player["player"]["payment"] != "",
            "systems_provided": player["player"]["systems"] != [],
            "has_rating": player["player"]["rating"] != 0,
        }
    except KeyError:
        logging.critical("cannot get player fields for user by id {}".format(player_id))

    return player_form


async def get_players_and_masters_with_roles(dialog_manager: DialogManager, **kwargs):
    current_game = await get_game_by_id_in_dialog_data(dialog_manager)
    user_id = "id_000000"

    master_and_players = []
    try:
        players = current_game["players"]
        master_and_players = [{"name": users[player]["general"]["name"], "id": player, "system_role": "player", "role": "игрок"} for player in players if player != user_id]

        master = current_game["master"]
        if master != user_id:
            master_and_players.append({"name": users[master]["general"]["name"], "id": master, "system_role": "master", "role": "мастер"})
    except KeyError:
        logging.critical("cannot access players list or master")
        await dialog_manager.done()
        return

    return {"master_and_players": master_and_players}


async def get_rating_user_and_rates(dialog_manager: DialogManager, **kwargs):
    rating_user = dialog_manager.dialog_data.get("rating_user")
    if rating_user is None:
        logging.critical("missing rating_user in dialog data")
        await dialog_manager.done()
        return

    rating_user_and_rates = {
        "rates": [
            {"rate": "★", "id": "rate_1"},
            {"rate": "★★", "id": "rate_2"},
            {"rate": "★★★", "id": "rate_3"},
            {"rate": "★★★★", "id": "rate_4"},
            {"rate": "★★★★★", "id": "rate_5"},
        ],
        "name": rating_user["name"],
        "role": rating_user["role"],
    }

    return rating_user_and_rates


# SELECTORS
# Master statuses
def is_user_master(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master"


def is_status_public_and_rights_master(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and dialog_manager.dialog_data.get("status") == "Набор игроков открыт"


def is_status_private_and_rights_master(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and dialog_manager.dialog_data.get("status") == "Набор игроков закрыт"


def is_status_not_done_and_rights_master(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and not dialog_manager.dialog_data.get("status") == "Игра проведена"


def is_status_done_and_rights_master(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and dialog_manager.dialog_data.get("status") == "Игра проведена"


def is_folder_games(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("folder") == "games"


def is_folder_archive(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("folder") == "archive"


def is_status_done_and_user_is_participate(data: dict, widget: Whenable, dialog_manager: DialogManager):
    if not dialog_manager.dialog_data.get("status") == "Игра проведена":
        return False

    user_id = "id_000000"
    current_game = get_game_by_id_in_dialog_data_not_async(dialog_manager)

    try:
        if user_id == current_game["master"] or user_id in current_game["players"]:
            return True
    except KeyError:
        logging.critical("cannot access game fields")

    return False



# Player statuses
def is_user_player(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "player"


# ONCLICK
def generate_set_status(new_status: str):
    async def set_status(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
        game_id = await get_game_id_in_dialog_data(dialog_manager)

        dialog_manager.dialog_data["status"] = new_status
        try:
            games[game_id]["status"] = new_status
        except KeyError:
            logging.critical("game by {} is missing".format(game_id))
            await dialog_manager.done()
            return

        if new_status == "Набор игроков открыт":
            open_games.add(game_id)
        if new_status == "Набор игроков закрыт":
            try:
                open_games.remove(game_id)
            except ValueError:
                logging.critical("game by {} is missing in open games".format(game_id))
                await dialog_manager.done()
                return

        await callback.answer(text="Статус успешно изменён!")

    return set_status



def generate_start_edit_game_field(edit_state: State):
    async def start_edit_game_field(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
        game_id = await get_game_id_in_dialog_data(dialog_manager)
        await dialog_manager.start(state=edit_state, data={"game_id": game_id, "mode": "edit"})

    return start_edit_game_field


async def set_status_done(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    user_title = message.text
    current_game = await get_game_by_id_in_dialog_data(dialog_manager)

    if current_game is None:
        await message.answer("Что-то пошло не так, обратитесь в поддержку.")
        return

    if user_title == current_game.get("title"):
        new_status = "Игра проведена"

        game_id = await get_game_id_in_dialog_data(dialog_manager)
        dialog_manager.dialog_data["status"] = new_status

        try:
            games[game_id]["status"] = new_status
        except KeyError:
            logging.critical("game by {} is missing".format(game_id))
            await dialog_manager.done()
            return

        await message.answer("Статус успешно изменён!")
        await dialog_manager.switch_to(GameInspection.checking_game)
        return

    await message.answer("Для подтверждения действия ваше сообщение должно совпадать с названием игры.")


async def change_game_folder(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id, rights = await get_game_id_and_rights(dialog_manager)
    old_folder = await get_folder(dialog_manager)

    next_folder = {"games": "archive", "archive": "games"}
    new_folder = next_folder[old_folder]

    # TODO: detect user id
    user_id = "id_000000"
    await delete_game_from_user(user_id, rights, old_folder, game_id, dialog_manager)

    await add_game_to_user(user_id, rights, new_folder, game_id, dialog_manager)

    if new_folder == "archive":
        await callback.answer("Игра перемещена в архив.")
    if new_folder == "games":
        await callback.answer("Игра перемещена из архива.")


async def delete_game(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    user_title = message.text
    current_game = await get_game_by_id_in_dialog_data(dialog_manager)

    if current_game is None:
        await message.answer("Что-то пошло не так, обратитесь в поддержку.")
        return

    if user_title == current_game.get("title"):
        game_id, rights = await get_game_id_and_rights(dialog_manager)
        folder = await get_folder(dialog_manager)

        if rights == "master":
            master_id = current_game["master"]
            players_id = current_game["players"]

            await delete_game_from_user(master_id, "master", folder, game_id, dialog_manager)
            for player_id in players_id:
                await delete_game_from_user(player_id, "player", folder, game_id, dialog_manager)

            games.pop(game_id, None)

        if rights == "player":
            # TODO: detect user id
            user_id = "id_000000"
            await delete_game_from_user(user_id, "player", folder, game_id, dialog_manager)

            try:
                games[game_id]["players"].remove(user_id)
            except ValueError:
                logging.critical("missing {} in players of game by id {}".format(user_id, game_id))
                await dialog_manager.done()
            except KeyError:
                logging.critical("missing expected parameters in user by id: {}".format(user_id))
                await dialog_manager.done()


        await message.answer("Игра удалена.")
        await dialog_manager.done()
        return

    await message.answer("Для подтверждения действия ваше сообщение должно совпадать с названием игры.")


async def kick_player(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    str_index = message.text.strip(" .;'\"")
    if str_index is None or not str_index.isdigit():
        await message.answer("Вам необходимо ввести число.")
        return

    index = int(str_index)
    data = await get_players_by_game_id_in_dialog_data(dialog_manager)
    players = data["players"]
    players_number = len(players)
    if index > players_number or index < 0:
        await message.answer("Введите число, соответствующее индексу игры (от 1 до {}).".format(players_number))

    dialog_manager.dialog_data["kicking_player"] = players[index - 1]["id"]
    await dialog_manager.switch_to(GameInspection.kick_confirmation)


async def kick_player_by_id_in_dialog_data(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    player_id = dialog_manager.dialog_data.get("kicking_player")
    if player_id is None:
        logging.critical("missing kicking_player in dialog data")
        await dialog_manager.done()
        return

    game_id = await get_game_id_in_dialog_data(dialog_manager)
    try:
        games[game_id]["players"].remove(player_id)
    except ValueError:
        logging.critical("missing player by id {} in game by id {}".format(player_id, game_id))
        await dialog_manager.done()
        return
    except KeyError:
        logging.critical("cannot access players for game by id {}".format(game_id))
        await dialog_manager.done()
        return


async def check_request(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    str_index = message.text.strip(" .;'\"")
    if str_index is None or not str_index.isdigit():
        await message.answer("Вам необходимо ввести число.")
        return

    index = int(str_index)
    data = await get_requests_by_game_id_in_dialog_data(dialog_manager)
    requests = data["requests"]
    requests_number = len(requests)
    if index > requests_number or index < 0:
        await message.answer("Введите число, соответствующее индексу игры (от 1 до {}).".format(requests_number))

    dialog_manager.dialog_data["request_player"] = requests[index - 1]["id"]
    await dialog_manager.switch_to(GameInspection.checking_request)


async def accept_request(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    player_id = dialog_manager.dialog_data.get("request_player")
    if player_id is None:
        logging.critical("missing request_player in dialog data")
        await dialog_manager.done()
        return

    game_id = await get_game_id_in_dialog_data(dialog_manager)
    try:
        games[game_id]["requests"].remove(player_id)
        games[game_id]["players"].append(player_id)
    except ValueError:
        logging.critical("missing requests by id {} in game by id {}".format(player_id, game_id))
        await dialog_manager.done()
        return
    except KeyError:
        logging.critical("cannot access requests for game by id {}".format(game_id))
        await dialog_manager.done()
        return


async def decline_request(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    player_id = dialog_manager.dialog_data.get("request_player")
    if player_id is None:
        logging.critical("missing request_player in dialog data")
        await dialog_manager.done()
        return

    game_id = await get_game_id_in_dialog_data(dialog_manager)
    try:
        games[game_id]["requests"].remove(player_id)
    except ValueError:
        logging.critical("missing requests by id {} in game by id {}".format(player_id, game_id))
        await dialog_manager.done()
        return
    except KeyError:
        logging.critical("cannot access requests for game by id {}".format(game_id))
        await dialog_manager.done()
        return


async def rate_user(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    str_index = message.text.strip(" .;'\"")
    if str_index is None or not str_index.isdigit():
        await message.answer("Вам необходимо ввести число.")
        return

    index = int(str_index)
    data = await get_players_and_masters_with_roles(dialog_manager)
    master_and_players = data["master_and_players"]
    master_and_players_number = len(master_and_players)
    if index > master_and_players_number or index < 0:
        await message.answer("Введите число, соответствующее индексу игры (от 1 до {}).".format(master_and_players_number))

    dialog_manager.dialog_data["rating_user"] = master_and_players[index - 1]
    await dialog_manager.switch_to(GameInspection.rating_user)


async def save_rating(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, item_id: str):
    _, rate = item_id.split("_")
    rate = int(rate)

    user_id = "id_000000"

    rated_user = dialog_manager.dialog_data.get("rating_user")
    if rated_user is None:
        logging.critical("missing rating_user in dialog data")
        await dialog_manager.done()
        return


    try:
        users[rated_user["id"]][rated_user["system_role"]]["reviews"][user_id] = rate
        rates = users[rated_user["id"]][rated_user["system_role"]]["reviews"].values()
        sum_rating = sum(rates)
        rate_number = len(rates)
        users[rated_user["id"]][rated_user["system_role"]]["rating"] = sum_rating / rate_number
    except KeyError:
        logging.critical("cannot access ratings for user with id {}".format(rated_user["id"]))
        await dialog_manager.done()
        return

    await dialog_manager.switch_to(GameInspection.choosing_who_to_rate)


# Game inspection dialog
game_inspection_dialog = Dialog(
    Window(
        generate_game_description(show_status=True),

        SwitchTo(text=Const("Редактировать"), id="edit_game", state=GameInspection.choosing_what_to_edit, when=is_user_master, show_mode=ShowMode.SEND),
        Row(
            SwitchTo(text=Const("Удалить"), id="delete_game", state=GameInspection.delete_game_confirmation),
            SwitchTo(text=Const("Архивировать"), id="archive_game", state=GameInspection.change_game_folder_confirmation, when=is_folder_games),
            SwitchTo(text=Const("Разархивировать"), id="dearchive_game", state=GameInspection.change_game_folder_confirmation, when=is_folder_archive),
        ),
        Row(
            SwitchTo(text=Const("Управлять группой"), id="managing_group", state=GameInspection.managing_group),
            SwitchTo(text=Const("Заявки на игру"), id="checking_requests", state=GameInspection.checking_all_requests),
            when=is_status_not_done_and_rights_master,
        ),
        SwitchTo(text=Const("Открыть набор игроков"), id="set_status_to_public", state=GameInspection.set_status_public_confirmation, when=is_status_private_and_rights_master),
        Button(text=Const("Завершить набор игроков"), id="set_status_to_private", on_click=generate_set_status("Набор игроков закрыт"), when=is_status_public_and_rights_master),
        SwitchTo(text=Const("Отметить игру проведённой"), id="set_status_to_done", state=GameInspection.set_status_done_confirmation, when=is_status_not_done_and_rights_master),
        SwitchTo(Const("Оставить отзыв"), id="choosing_who_to_rate", state=GameInspection.choosing_who_to_rate, when=is_status_done_and_user_is_participate),

        Cancel(Const("Назад")),
        getter=get_game_by_id_in_dialog_data_for_displaying,
        state=GameInspection.checking_game,
    ),
    Window(
        Const("Выберите, что хотите отредактировать."),

        Button(Const("Название"), id="edit_title_game", on_click=generate_start_edit_game_field(GameCreation.typing_title)),
        Button(Const("Цена"), id="edit_cost_game", on_click=generate_start_edit_game_field(GameCreation.choosing_cost)),
        Button(Const("Формат"), id="edit_format_game", on_click=generate_start_edit_game_field(GameCreation.choosing_format)),
        Button(Const("Место проведения"), id="edit_place_game", on_click=generate_start_edit_game_field(GameCreation.typing_place), when=is_game_offline),
        Button(Const("Платформа"), id="edit_platform_game", on_click=generate_start_edit_game_field(GameCreation.typing_platform), when=is_game_online),
        Button(Const("Время проведения"), id="edit_time_game", on_click=generate_start_edit_game_field(GameCreation.typing_time)),
        Button(Const("Число игроков"), id="edit_players_number_game", on_click=generate_start_edit_game_field(GameCreation.choosing_players_number)),
        Button(Const("Система и издание"), id="edit_system_game", on_click=generate_start_edit_game_field(GameCreation.choosing_system)),
        Button(Const("Тип"), id="edit_type_game", on_click=generate_start_edit_game_field(GameCreation.choosing_type)),
        Button(Const("Описание"), id="edit_description_game", on_click=generate_start_edit_game_field(GameCreation.typing_description)),
        Button(Const("Возраст игроков"), id="edit_age_game", on_click=generate_start_edit_game_field(GameCreation.choosing_age)),
        Button(Const("Требования к игрокам"), id="edit_requirements_game", on_click=generate_start_edit_game_field(GameCreation.typing_requirements)),

        SwitchTo(Const("Назад"), id="back_to_checking_game", state=GameInspection.checking_game),
        state=GameInspection.choosing_what_to_edit,
    ),
    Window(
        Const("Вы точно хотите опубликовать игру?\nБудьте осторожны, при подтверждении игра окажется в открытом доступе, и <b>её смогут просматривать другие пользователи</b>."),

        SwitchTo(Const("Подтвердить"), id="back_to_checking_game_public_confirmed", state=GameInspection.checking_game, on_click=generate_set_status("Набор игроков открыт")),

        SwitchTo(Const("Отмена"), id="back_to_checking_game_public_canceled", state=GameInspection.checking_game),
        state=GameInspection.set_status_public_confirmation,
    ),
    Window(
        Jinja("Вы точно хотите отметить игру как проведённую? <b>Это действие нельзя будет отменить.</b>\nВы потеряете возможность набирать игроков и управлять группой и откроете доступ игрокам и себе к оцениванию.\nЧтобы подтвердить это действие, отправьте ответным сообщение название игры: <b>{{title}}</b>"),

        MessageInput(func=set_status_done, content_types=[ContentType.TEXT]),

        SwitchTo(Const("Назад"), id="back_to_checking_game_done_canceled", state=GameInspection.checking_game),
        getter=get_game_by_id_in_dialog_data,
        state=GameInspection.set_status_done_confirmation,
    ),
    Window(
        Const("Вы точно хотите архивировать игру?\nИгра будет скрыта, однако вы всегда сможете её вернуть из архива.", when=is_folder_games),
        Const("Вы точно хотите разархивировать игру?\nИгра будет удалена из архива и помещена в основной список.", when=is_folder_archive),

        SwitchTo(Const("Подтвердить"), id="back_to_checking_game_archive_confirmed", state=GameInspection.checking_game, on_click=change_game_folder),

        SwitchTo(Const("Отмена"), id="back_to_checking_game_archive_canceled", state=GameInspection.checking_game),
        state=GameInspection.change_game_folder_confirmation,
    ),
    Window(
        Jinja("Вы точно хотите удалить игру? <b>Это действие нельзя будет отменить.</b>"),
        Jinja("Вы будете исключены из игроков (если вы в нём были), а заявка будет удалена.", when=is_user_player),
        Jinja("Все игроки будут исключены из группы, а игра удалена из вашего списка.", when=is_user_master),
        Jinja("Чтобы подтвердить это действие, отправьте ответным сообщение название игры: <b>{{title}}</b>"),

        MessageInput(func=delete_game, content_types=[ContentType.TEXT]),

        SwitchTo(Const("Назад"), id="back_to_checking_game_delete_canceled", state=GameInspection.checking_game),
        getter=get_game_by_id_in_dialog_data,
        state=GameInspection.delete_game_confirmation,
    ),
    Window(
        Const("Это ваши игроки. Вы можете исключить кого-то их них из группы, введя его номер"),
        List(
            Format("{pos}. {item[name]}"),
            items="players",
            id="players_list",
        ),

        MessageInput(func=kick_player, content_types=[ContentType.TEXT]),

        SwitchTo(Const("Назад"), id="back_to_checking_game_from_managing_group", state=GameInspection.checking_game),
        getter=get_players_by_game_id_in_dialog_data,
        state=GameInspection.managing_group,
    ),
    Window(
        Const("Вы точно хотите исключить игрока?\nБудьте осторожны, <b>добавить его обратно получиться, только если он снова подаст заявку</b>."),

        SwitchTo(Const("Подтвердить"), id="back_to_managing_group_kick_confirmed", state=GameInspection.managing_group, on_click=kick_player_by_id_in_dialog_data),

        SwitchTo(Const("Отмена"), id="back_to_managing_group_kick_canceled", state=GameInspection.managing_group),
        state=GameInspection.kick_confirmation,
    ),
    Window(
        Const("Это все заявки, поданные на игру. Чтобы просмотреть профиль игрока и принять или отклонить заявку, введите его номер"),
        List(
            Format("{pos}. {item[name]}"),
            items="requests",
            id="requests_list",
        ),

        MessageInput(func=check_request, content_types=[ContentType.TEXT]),

        SwitchTo(Const("Назад"), id="back_to_checking_game_from_checking_requests", state=GameInspection.checking_game),
        getter=get_requests_by_game_id_in_dialog_data,
        state=GameInspection.checking_all_requests,
    ),
    Window(
        Const("Профиль игрока:\n"),
        generate_player_description(),

        Row(
            SwitchTo(Const("Принять заявку"), id="back_to_checking_all_requests_request_accepted", state=GameInspection.checking_all_requests, on_click=accept_request),
            SwitchTo(Const("Отклонить заявку"), id="back_to_checking_all_requests_request_accepted", state=GameInspection.checking_all_requests, on_click=decline_request),
        ),

        getter=get_player_profile_by_id_in_dialog_data,
        state=GameInspection.checking_request,
    ),
    Window(
        Const("Выберите, кого вы хотите оценить. Для этого введите номер пользователя."),
        List(
            Format("{pos}. {item[name]} - {item[role]}"),
            items="master_and_players",
            id="master_and_players_list",
        ),

        MessageInput(func=rate_user, content_types=[ContentType.TEXT]),

        SwitchTo(Const("Назад"), id="back_to_checking_game_from_choosing_who_to_rate", state=GameInspection.checking_game),
        getter=get_players_and_masters_with_roles,
        state=GameInspection.choosing_who_to_rate,
    ),
    Window(
        Const("Оцените, на сколько приятным было взаимодействие с этим пользователем."),
        Format("{name} - {role}"),

        Column(
            Select(
                Format("{item[rate]}"),
                id="select_rate",
                item_id_getter=lambda item: item["id"],
                items="rates",
                on_click=save_rating
            )
        ),

        SwitchTo(Const("Назад"), id="back_to_choosing_who_to_rate_from_rating_user", state=GameInspection.choosing_who_to_rate),
        getter=get_rating_user_and_rates,
        state=GameInspection.rating_user,
    ),
    on_start=copy_data_to_dialog_data,
)
