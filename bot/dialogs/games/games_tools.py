import logging
from typing import Optional

from aiogram.fsm.state import State
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Group, Row, PrevPage, CurrentPage, NextPage
from aiogram_dialog.widgets.text import List, Format, Const, Multi, Jinja

from bot.db.current_requests import user, games
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



# GETTERS
async def get_game_by_id_in_start_data(dialog_manager: DialogManager, **kwargs):
    game_id = dialog_manager.start_data.get("game_id")
    if game_id is None:
        logging.critical("cannot find game id in start data")
        await dialog_manager.done()
        return

    current_game = games.get(game_id)
    if current_game is None:
        logging.critical("cannot find game with id {}".format(game_id))
        await dialog_manager.done()
        return

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


def generate_save_message_from_user_no_formatting_game(field: str, parameter: str, next_states: dict[str, Optional[State]]):
    async def save_message_from_user_no_formatting(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        games[field][parameter] = message.text

        await switch_state(dialog_manager, next_states)

    return save_message_from_user_no_formatting
