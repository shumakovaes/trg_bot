from typing import Optional

from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Group, Row, PrevPage, CurrentPage, NextPage
from aiogram_dialog.widgets.text import List, Format, Const, Multi, Jinja

from bot.db.current_requests import user, games
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


def generate_game_description_by_id(game_id: str):
    def is_game_online(data: Optional[dict], widget: Optional[Whenable], manager: Optional[DialogManager]):
        game_format = games[game_id]["format"].get("format")
        return game_format == "Онлайн"


    def is_game_offline(data: Optional[dict], widget: Optional[Whenable], manager: Optional[DialogManager]):
        game_format = games[game_id]["format"].get("format")
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
            "<b>Система</b>: {{system}}\n" +
            "<b>Редакция</b>: {{edition}}\n" +
            "<b>Сеттинг</b>: {{setting}}\n\n" +
            "<b>Описание</b>:\n {{description}}\n\n" +
            "<b>Возраст</b>: {{age}}\n" +
            "<b>Требования к игрокам</b>: {{requirements}}\n"
        ),
        sep='',
    )

    return game_description


# GETTERS
def get_game_by_id(game_id: str):
    return games[game_id]


# ONCLICK GENERATORS
def generate_check_game(rights: str):
    async def check_game(message: Message, message_input: MessageInput, manager: DialogManager):
        str_index = message.text.strip()
        if str_index is None or not str_index.isdigit():
            await message.answer("Вам необходимо ввести число.")
            return
        index = int(str_index)

        await manager.start(GameInspection.checking_game, data={"game_id":user[rights][index], "rights": rights})
