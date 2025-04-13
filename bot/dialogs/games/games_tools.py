import logging
from typing import Optional

from aiogram.fsm.state import State
from aiogram.types import Message, Game
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Group, Row, PrevPage, CurrentPage, NextPage
from aiogram_dialog.widgets.text import List, Format, Const, Multi, Jinja

from bot.db.current_requests import user, games, default_game
from bot.dialogs.general_tools import switch_state
from bot.states.games_states import GameCreation, GameInspection

# WIDGETS
# TODO: add filters
games_list = List(
    Format("{pos}. {item[title]} - {item[status]}"),
    items="games",
    page_size=10,
    id="scroll_games",
)

games_navigation = Group(
    Row(
        PrevPage("scroll_games", text=Const("<")),
        CurrentPage("scroll_games", text=Format("{current_page1}/{pages}")),
        NextPage("scroll_games", text=Const(">"))
    ),
)


def generate_game_description() -> Multi:
    game_format = Format("{format}").text
    def is_game_online(data: Optional[dict], widget: Optional[Whenable], dialog_manager: Optional[DialogManager]):
        return game_format == "Онлайн"


    def is_game_offline(data: Optional[dict], widget: Optional[Whenable], dialog_manager: Optional[DialogManager]):
        return game_format == "Оффлайн"


    game_description = Multi(
        Jinja(
            "<i>Статус: {{status}}</i>\n\n" +
            "<b>{{title}}</b>\n" +
            "<b>Формат</b>: {{format}}\n" +
            "<b>Цена</b>: {{cost}}\n" +
            "<b>Количество игроков</b>: {{number_of_players}}\n" +
            "<b>Время проведения</b>: {{time}}\n\n"
        ),
        Jinja(
            text="<b>Место проведения</b>: {{place}}",
            when=is_game_offline,
        ),
        Jinja(
            text="<b>Платформа</b>: {{platform}}",
            when=is_game_online,
        ),
        Jinja(
            "<b>Тип</b>: {{type}}\n" +
            "<b>Система и издание</b>: {{system}}\n" +
            "<b>Описание</b>:\n {{description}}\n\n" +
            "<b>Возраст</b>: {{age}}\n" +
            "<b>Требования к игрокам</b>: {{requirements}}\n"
        ),
        sep='',
    )

    return game_description


# HELPER FUNCTION
async def get_game_by_id(dialog_manager: DialogManager, game_id: Optional[str]):
    if game_id is None:
        logging.critical("cannot find game id in start data")
        await dialog_manager.done()
        return None

    current_game = games.get(game_id)
    if current_game is None:
        logging.critical("cannot find game with id {}".format(game_id))
        await dialog_manager.done()
        return None

    return current_game


async def get_game_id_in_dialog_data(dialog_manager: DialogManager):
    game_id = dialog_manager.dialog_data.get("game_id")
    if game_id is None:
        logging.critical("no game id was provided")
        await dialog_manager.done()
        return None

    return game_id


def get_game_id_in_dialog_data_not_async(dialog_manager: DialogManager):
    game_id = dialog_manager.dialog_data.get("game_id")
    if game_id is None:
        logging.critical("no game id was provided")

    return game_id



# GETTERS
async def get_game_by_id_in_start_data(dialog_manager: DialogManager, **kwargs):
    game_id = dialog_manager.start_data.get("game_id")
    current_game = await get_game_by_id(dialog_manager, game_id)

    return current_game


async def get_game_by_id_in_dialog_data(dialog_manager: DialogManager, **kwargs):
    game_id = dialog_manager.dialog_data.get("game_id")
    current_game = await get_game_by_id(dialog_manager, game_id)

    return current_game


# ONCLICK GENERATORS
def generate_check_game(rights: str):
    async def check_game(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        str_index = message.text.strip(" .;'\"")
        if str_index is None or not str_index.isdigit():
            await message.answer("Вам необходимо ввести число.")
            return
        index = int(str_index)

        await dialog_manager.start(GameInspection.checking_game, data={"game_id": user[rights]["games"][index - 1], "rights": rights})

    return check_game


def generate_save_message_from_user_no_formatting_game(parameter: str, next_states: dict[str, Optional[State]]):
    async def save_message_from_user_no_formatting(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        game_id = dialog_manager.dialog_data.get("game_id")
        if game_id is None:
            logging.critical("cannot find game id in start data")
            await message.answer(text="Что-то пошло не так, обратитесь в поддержку.")
            await dialog_manager.done()
            return

        games[game_id][parameter] = message.text

        await switch_state(dialog_manager, next_states)

    return save_message_from_user_no_formatting


def generate_save_diapason_from_user(min_value: int, max_value: int, min_value_key: str, max_value_key: str, next_states: dict[str, Optional[State]]):
    async def save_diapason_from_user(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        if message.text is None:
            await message.answer("Сообщение не должно быть пустым.")
            return

        user_number_of_players = message.text.strip(". \"\'")
        if user_number_of_players == "":
            await message.answer("Сообщение не должно состоять из одних символов.")
            return
        game_id = await get_game_id_in_dialog_data(dialog_manager)

        if user_number_of_players[-1] == '-' or user_number_of_players[-1] == '+':
            sign_to_word = {"+": "плюсом", "-": "минусом"}
            sign = user_number_of_players[-1]
            word_sign = sign_to_word[sign]

            user_number_of_players = user_number_of_players[:-1]
            if not user_number_of_players.isdigit():
                await message.answer("Значение перед {} должно быть числом.".format(word_sign))
                return

            user_number_of_players_int = int(user_number_of_players)
            if user_number_of_players_int > max_value or user_number_of_players_int < min_value:
                await message.answer("Значение перед {} должно быть числом между {} и {}.".format(word_sign, min_value, max_value))
                return

            if sign == '-':
                games[game_id][min_value_key] = min_value
                games[game_id][max_value_key] = user_number_of_players_int
                await switch_state(dialog_manager, next_states)
            elif sign == '+':
                games[game_id][min_value_key] = user_number_of_players_int
                games[game_id][max_value_key] = max_value
                await switch_state(dialog_manager, next_states)
            else:
                logging.critical("unexpected sign: {}".format(sign))
                await message.answer("Что-то пошло не так.")
                await dialog_manager.done()
                return

        user_number_of_players_list = list(user_number_of_players.split("-"))
        if len(user_number_of_players_list) != 2:
            await message.answer("Используйте ровно один дефис.")
            return
        if not user_number_of_players_list[0].isdigit() or not user_number_of_players_list[1].isdigit():
            await message.answer("Введите числа через дефис.")
            return

        min_number_of_players, max_number_of_players = map(int, user_number_of_players_list)
        if min_number_of_players < min_value or max_number_of_players < min_value or min_number_of_players > max_value or max_number_of_players > max_value:
            await message.answer("Числа должны лежать в диапазоне от {} до {}.".format(min_value, max_value))
            return
        if min_number_of_players > max_number_of_players:
            min_number_of_players, max_number_of_players = max_number_of_players, min_number_of_players

        games[game_id][min_value_key] = min_number_of_players
        games[game_id][max_value_key] = max_number_of_players
        await switch_state(dialog_manager, next_states)

    return save_diapason_from_user
