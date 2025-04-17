import logging
from typing import Any

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, games, user, users
from bot.dialogs.games.games_tools import generate_game_description, get_game_by_id_in_start_data, \
    get_game_by_id_in_dialog_data, get_game_by_id, is_game_offline, is_game_online, get_game_id_in_dialog_data
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


# SELECTORS
# Master statuses
def is_user_master(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master"


def is_status_public(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and dialog_manager.dialog_data.get("status") == "Набор игроков открыт"


def is_status_private(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and dialog_manager.dialog_data.get("status") == "Набор игроков закрыт"


def is_status_not_done(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and not dialog_manager.dialog_data.get("status") == "Игра проведена"


def is_status_done(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("rights") == "master" and dialog_manager.dialog_data.get("status") == "Игра проведена"


def is_folder_games(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("folder") == "games"


def is_folder_archive(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.dialog_data.get("folder") == "archive"


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

        await callback.answer(text="Статус успешно изменён!", show_alert=True)

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

    await message.answer("Для подтверждения действия ваше сообщение должно совпадать с названием игры.")


async def change_game_folder(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id, rights = await get_game_id_and_rights(dialog_manager)
    old_folder = await get_folder(dialog_manager)

    next_folder = {"games": "archive", "archive": "games"}
    new_folder = next_folder[old_folder]

    # TODO: detect user id
    user_id = "id_000000"
    await delete_game_from_user(user_id, rights, old_folder, game_id, dialog_manager)

    # ----------This code is temperate------------
    try:
        user[rights][old_folder].remove(game_id)
    except ValueError:
        logging.critical("missing {} in user {} games".format(game_id, user_id))
        await dialog_manager.done()
    except KeyError:
        logging.critical("missing expected parameters in user by id: {}".format(user_id))
        await dialog_manager.done()
    # ---------------------------------------------

    await add_game_to_user(user_id, rights, new_folder, game_id, dialog_manager)

    if new_folder == "archive":
        await callback.answer("Игра перемещена в архив.", show_alert=True)
    if new_folder == "games":
        await callback.answer("Игра перемещена из архива.", show_alert=True)

    await dialog_manager.done()


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

            # ----------This code is temperate------------
            user_id = "id_000000"
            try:
                user["master"][folder].remove(game_id)
            except ValueError:
                logging.critical("missing {} in user {} master games".format(game_id, user_id))
                await dialog_manager.done()
            except KeyError:
                logging.critical("missing expected parameters in user by id: {}".format(user_id))
                await dialog_manager.done()
            # ---------------------------------------------

            games.pop(game_id, None)

        if rights == "player":
            # TODO: detect user id
            user_id = "id_000000"
            await delete_game_from_user(user_id, "player", folder, game_id, dialog_manager)

            # ----------This code is temperate------------
            try:
                user["player"][folder].remove(game_id)
            except ValueError:
                logging.critical("missing {} in user {} player games".format(game_id, user_id))
                await dialog_manager.done()
            except KeyError:
                logging.critical("missing expected parameters in user by id: {}".format(user_id))
                await dialog_manager.done()
            # ---------------------------------------------

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
        SwitchTo(text=Const("Открыть набор игроков"), id="set_status_to_public", state=GameInspection.set_status_public_confirmation, when=is_status_private),
        Button(text=Const("Завершить набор игроков"), id="set_status_to_private", on_click=generate_set_status("Набор игроков закрыт"), when=is_status_public),
        SwitchTo(text=Const("Отметить игру проведённой"), id="set_status_to_done", state=GameInspection.set_status_done_confirmation, when=is_status_not_done),

        Cancel(Const("Назад")),
        getter=get_game_by_id_in_dialog_data,
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
        Jinja("Вы будете исключены из игроков, а заявка будет удалена.", when=is_user_player),
        Jinja("Все игроки будут исключены из группы, а игра удалена из вашего списка.", when=is_user_master),
        Jinja("Чтобы подтвердить это действие, отправьте ответным сообщение название игры: <b>{{title}}</b>"),

        MessageInput(func=delete_game, content_types=[ContentType.TEXT]),

        SwitchTo(Const("Назад"), id="back_to_checking_game_delete_canceled", state=GameInspection.checking_game),
        getter=get_game_by_id_in_dialog_data,
        state=GameInspection.delete_game_confirmation,
    ),
    on_start=copy_data_to_dialog_data,
)
