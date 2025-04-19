import logging
from typing import Optional

from aiogram.fsm.state import State
from aiogram.types import Message, Game
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Group, Row, PrevPage, CurrentPage, NextPage
from aiogram_dialog.widgets.text import List, Format, Const, Multi, Jinja

from bot.db.current_requests import user, games, default_game, MAX_AGE, MIN_AGE, MIN_PLAYERS_NUMBER, \
    MAX_PLAYERS_NUMBER
from bot.dialogs.general_tools import switch_state, need_to_display_current_value
from bot.states.games_states import GameCreation, GameInspection

# WIDGETS
def generate_games_list_title_status(elements: str):
    games_list = List(
        Format("{pos}. {item[title]} - {item[status]}"),
        items="games",
        page_size=10,
        id="scroll_games_{}".format(elements),
    )

    return games_list


def generate_games_list_title(elements: str):
    games_list = List(
        Format("{pos}. {item[title]}"),
        items="games",
        page_size=10,
        id="scroll_games_{}".format(elements),
    )

    return games_list


def generate_games_navigation(elements: str):
    games_navigation = Group(
        Row(
            PrevPage("scroll_games_{}".format(elements), text=Const("<")),
            CurrentPage("scroll_games_{}".format(elements), text=Format("{current_page1}/{pages}")),
            NextPage("scroll_games_{}".format(elements), text=Const(">"))
        ),
    )

    return games_navigation


def generate_game_description(show_status: bool) -> Multi:
    def is_need_display_status(data: dict, widget: Whenable, dialog_manager: DialogManager):
        return show_status

    game_description = Multi(
        Jinja(
            text="<i>Статус: {{status}}</i>\n\n",
            when=is_need_display_status,
        ),
        Jinja(
            "<b>{{title}}</b>\n" +
            "<b>Цена</b>: {{cost}}\n" +
            "<b>Формат</b>: {{format}}\n"
        ),
        Jinja(
            text="<b>Место проведения</b>: {{place}}\n",
            when=is_game_offline,
        ),
        Jinja(
            text="<b>Платформа</b>: {{platform}}\n",
            when=is_game_online,
        ),
        Jinja(
            text="<b>Время проведения</b>: {{time}}\n\n",
        ),
        Jinja("<b>Число игроков</b>: {{min_players_number}}-{{max_players_number}}\n", when=min_and_max_provided_players_number),
        Jinja("<b>Число игроков</b>: {{min_players_number}}+\n", when=only_min_provided_players_number),
        Jinja("<b>Число игроков</b>: {{max_players_number}}-\n", when=only_max_provided_players_number),
        Jinja("<b>Число игроков</b>: Отсутствуют\n", when=nothing_provided_players_number),
        Jinja(
            "<b>Тип</b>: {{type}}\n" +
            "<b>Система и издание</b>: {{system}}\n" +
            "<b>Описание</b>:\n {{description}}\n\n"
        ),

        Jinja("<b>Возраст игроков</b>: {{min_age}}-{{max_age}}\n",
              when=min_and_max_provided_age),
        Jinja("<b>Возраст игроков</b>: {{min_age}}+\n",
              when=only_min_provided_age),
        Jinja("<b>Возраст игроков</b>: {{max_age}}-\n",
              when=only_max_provided_age),
        Jinja("<b>Возраст игроков</b>: Любой\n",
              when=nothing_provided_age),
        Jinja(
            "<b>Требования к игрокам</b>: {{requirements}}\n"
        ),
        sep='\n',
    )

    return game_description


# HELPER FUNCTION
# HELPERS
async def is_default_value_not_empty(dialog_manager: DialogManager, value: str):
    default_value = await get_default_value(dialog_manager, value)

    return default_value != ""


async def is_default_settings_value(dialog_manager: DialogManager, value: str):
    return dialog_manager.dialog_data.get("default_settings") == value


async def is_need_to_be_skipped(dialog_manager: DialogManager, value: str):
    return await is_default_settings_value(dialog_manager, "all") and await is_default_value_not_empty(dialog_manager, value)


async def get_default_value(dialog_manager: DialogManager, value: str):
    default_data = dialog_manager.dialog_data.get("default_data")
    if default_data is None:
        logging.critical("no default data was provided")
        await dialog_manager.done()
        return

    try:
        default_value = default_data[value]
    except KeyError:
        logging.critical("{} was not provided".format(value))
        await dialog_manager.done()
        return

    return default_value



async def get_game_by_id(dialog_manager: DialogManager, game_id: Optional[str]):
    if game_id is None:
        logging.critical("cannot find game id {}".format(game_id))
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


def get_game_by_id_in_dialog_data_not_async(dialog_manager: DialogManager, **kwargs):
    game_id = get_game_id_in_dialog_data_not_async(dialog_manager)

    current_game = games.get(game_id)
    if current_game is None:
        logging.critical("cannot find game with id {}".format(game_id))
        return None

    return current_game

def is_less(x: int, y: int) -> bool:
    return x < y


def is_less_or_equal(x: int, y: int) -> bool:
    return x <= y


def is_more(x: int, y: int) -> bool:
    return x > y


def is_more_or_equal(x: int, y: int) -> bool:
    return x >= y


# GETTERS
async def get_game_by_id_in_start_data(dialog_manager: DialogManager, **kwargs):
    game_id = dialog_manager.start_data.get("game_id")
    current_game = await get_game_by_id(dialog_manager, game_id)

    return current_game


async def get_game_by_id_in_dialog_data(dialog_manager: DialogManager, **kwargs):
    game_id = dialog_manager.dialog_data.get("game_id")
    current_game = await get_game_by_id(dialog_manager, game_id)

    return current_game


async def get_game_by_id_in_dialog_data_for_displaying(dialog_manager: DialogManager, **kwargs):
    current_game = await get_game_by_id_in_dialog_data(dialog_manager)

    rights = dialog_manager.dialog_data.get("rights")
    if rights is None:
        logging.critical("rights was not provided")
        await dialog_manager.done()
        return

    if rights == "player":
        user_id = "id_000000"

        if user_id in current_game["players"]:
            current_game["status"] = "Заявка принята"
        elif user_id in current_game["requests"]:
            current_game["status"] = "Заявка находится на рассмотрении"
        else:
            current_game["status"] = "Заявка отклонена"

    return current_game


# ONCLICK GENERATORS
def generate_check_game(rights: str, folder: str):
    async def check_game(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        str_index = message.text.strip(" .;'\"")
        if str_index is None or not str_index.isdigit():
            await message.answer("Вам необходимо ввести число.")
            return

        index = int(str_index)
        games_number = len(user[rights][folder])
        if index > games_number or index < 0:
            await message.answer("Введите число, соответствующее индексу игры (от 1 до {}).".format(games_number))

        await dialog_manager.start(GameInspection.checking_game, data={"game_id": user[rights][folder][index - 1], "rights": rights, "folder": folder})

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


def generate_save_diapason_from_user(min_value: int, max_value: int, min_value_key: str, max_value_key: str, next_states: dict[str, Optional[State]], need_check_for_default_values: bool):
    async def save_diapason_from_user(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        if message.text is None:
            await message.answer("Сообщение не должно быть пустым.")
            return

        user_players_number = message.text.strip(". \"\'")
        if user_players_number == "":
            await message.answer("Сообщение не должно состоять из одних символов.")
            return
        game_id = await get_game_id_in_dialog_data(dialog_manager)

        if user_players_number[-1] == '-' or user_players_number[-1] == '+':
            sign_to_word = {"+": "плюсом", "-": "минусом"}
            sign = user_players_number[-1]
            word_sign = sign_to_word[sign]

            user_players_number = user_players_number[:-1]
            if not user_players_number.isdigit():
                await message.answer("Значение перед {} должно быть числом.".format(word_sign))
                return

            user_players_number_int = int(user_players_number)
            if user_players_number_int > max_value or user_players_number_int < min_value:
                await message.answer("Значение перед {} должно быть числом между {} и {}.".format(word_sign, min_value, max_value))
                return

            if sign == '-':
                games[game_id][min_value_key] = min_value
                games[game_id][max_value_key] = user_players_number_int
                await switch_state(dialog_manager, next_states)
                return
            elif sign == '+':
                games[game_id][min_value_key] = user_players_number_int
                games[game_id][max_value_key] = max_value
                await switch_state(dialog_manager, next_states)
                return
            else:
                logging.critical("unexpected sign: {}".format(sign))
                await message.answer("Что-то пошло не так.")
                await dialog_manager.done()
                return

        user_players_number_list = list(user_players_number.split("-"))
        if len(user_players_number_list) != 2:
            await message.answer("Используйте ровно один дефис.")
            return
        if not user_players_number_list[0].isdigit() or not user_players_number_list[1].isdigit():
            await message.answer("Введите числа через дефис.")
            return

        min_players_number, max_players_number = map(int, user_players_number_list)
        if min_players_number < min_value or max_players_number < min_value or min_players_number > max_value or max_players_number > max_value:
            await message.answer("Числа должны лежать в диапазоне от {} до {}.".format(min_value, max_value))
            return
        if min_players_number > max_players_number:
            min_players_number, max_players_number = max_players_number, min_players_number

        games[game_id][min_value_key] = min_players_number
        games[game_id][max_value_key] = max_players_number

        if need_check_for_default_values and await is_need_to_be_skipped(dialog_manager, "default_requirements"):
            game_id = await get_game_id_in_dialog_data(dialog_manager)

            default_requirements = await get_default_value(dialog_manager, "default_requirements")

            games[game_id]["requirements"] = default_requirements
            next_states_skipped = {"edit": None, "register": GameCreation.typing_description}

            await switch_state(dialog_manager, next_states_skipped)

        await switch_state(dialog_manager, next_states)

    return save_diapason_from_user


# SELECTORS GENERATORS
def generate_generate_is_diapason_provided(min_comparator, max_comparator):
    def generate_is_diapason_provided(min_parameter: str, max_parameter: str, min_value: int, max_value: int):
        def is_diapason_provided(data: dict, widget: Whenable, dialog_manager: DialogManager):
            current_game = get_game_by_id_in_dialog_data_not_async(dialog_manager)
            if current_game is None:
                return False

            current_min_value = current_game.get(min_parameter)
            current_max_value = current_game.get(max_parameter)

            if current_min_value is None:
                logging.critical("cannot get game parameter: {}".format(min_parameter))
                return False
            if current_max_value is None:
                logging.critical("cannot get game parameter: {}".format(max_parameter))
                return False

            return min_comparator(min_value, current_min_value) and max_comparator(current_max_value, max_value)

        return is_diapason_provided

    return generate_is_diapason_provided


def add_check_of_need_to_display_current_value(selector):
    def need_to_display_current_value_selector(data: dict, widget: Whenable, dialog_manager: DialogManager):
        return need_to_display_current_value(data, widget, dialog_manager) and selector(data, widget, dialog_manager)

    return need_to_display_current_value_selector


generate_min_and_max_provided = generate_generate_is_diapason_provided(is_less, is_more)


generate_only_min_provided = generate_generate_is_diapason_provided(is_less, is_less_or_equal)


generate_max_provided = generate_generate_is_diapason_provided(is_more_or_equal, is_more)


generate_nothing_provided = generate_generate_is_diapason_provided(is_more_or_equal, is_less_or_equal)


# SELECTORS
min_and_max_provided_players_number = generate_min_and_max_provided("min_players_number", "max_players_number", MIN_PLAYERS_NUMBER, MAX_PLAYERS_NUMBER)
need_to_display_current_value_and_min_and_max_provided_players_number = add_check_of_need_to_display_current_value(min_and_max_provided_players_number)


only_min_provided_players_number = generate_only_min_provided("min_players_number", "max_players_number", MIN_PLAYERS_NUMBER, MAX_PLAYERS_NUMBER)
need_to_display_current_value_and_only_min_provided_players_number = add_check_of_need_to_display_current_value(only_min_provided_players_number)


only_max_provided_players_number = generate_max_provided("min_players_number", "max_players_number", MIN_PLAYERS_NUMBER, MAX_PLAYERS_NUMBER)
need_to_display_current_value_and_only_max_provided_players_number = add_check_of_need_to_display_current_value(only_max_provided_players_number)


nothing_provided_players_number = generate_nothing_provided("min_players_number", "max_players_number", MIN_PLAYERS_NUMBER, MAX_PLAYERS_NUMBER)
need_to_display_current_value_and_nothing_provided_players_number = add_check_of_need_to_display_current_value(nothing_provided_players_number)


min_and_max_provided_age = generate_min_and_max_provided("min_age", "max_age", MIN_AGE, MAX_AGE)
need_to_display_current_value_and_min_and_max_provided_age = add_check_of_need_to_display_current_value(min_and_max_provided_age)


only_min_provided_age = generate_only_min_provided("min_age", "max_age", MIN_AGE, MAX_AGE)
need_to_display_current_value_and_only_min_provided_age = add_check_of_need_to_display_current_value(only_min_provided_age)


only_max_provided_age = generate_max_provided("min_age", "max_age", MIN_AGE, MAX_AGE)
need_to_display_current_value_and_only_max_provided_age = add_check_of_need_to_display_current_value(only_max_provided_age)


nothing_provided_age = generate_nothing_provided("min_age", "max_age", MIN_AGE, MAX_AGE)
need_to_display_current_value_and_nothing_provided_age = add_check_of_need_to_display_current_value(nothing_provided_age)


def is_game_online(data: Optional[dict], widget: Optional[Whenable], dialog_manager: Optional[DialogManager]):
    current_game = get_game_by_id_in_dialog_data_not_async(dialog_manager)
    if current_game is None:
        return False

    return current_game.get("format") == "Онлайн"


def is_game_offline(data: Optional[dict], widget: Optional[Whenable], dialog_manager: Optional[DialogManager]):
    current_game = get_game_by_id_in_dialog_data_not_async(dialog_manager)
    if current_game is None:
        return False

    return current_game.get("format") == "Оффлайн"