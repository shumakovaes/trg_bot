import logging
from typing import Any

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, games, default_game
from bot.dialogs.games.games_tools import generate_game_description, generate_save_message_from_user_no_formatting_game, \
    get_game_by_id_in_dialog_data
from bot.dialogs.general_tools import need_to_display_current_value, go_back_when_edit_mode, switch_state, \
    generate_random_id, is_register_mode
from bot.dialogs.registration.registration import save_age
from bot.states.games_states import AllGames, GameInspection, GameCreation


# Create new game (ONSTART)
async def create_new_game_if_needed(data: dict[str, Any], dialog_manager: DialogManager):
    if dialog_manager.start_data.get("mode") != "register":
        old_game_id = dialog_manager.start_data.get("game_id")
        if old_game_id is None:
            logging.critical("no game id was provided")
            await dialog_manager.done()
            return

        dialog_manager.dialog_data["game_id"] = old_game_id
        return

    # TODO: this can cause some bugs
    new_game_id = await generate_random_id()
    while not games.get(new_game_id) is None:
        new_game_id = await generate_random_id()

    dialog_manager.dialog_data["game_id"] = new_game_id
    games[new_game_id] = default_game


# Saving game settings (ONCLICK)
save_title = generate_save_message_from_user_no_formatting_game("title", {"edit": None, "register": GameCreation.choosing_cost})


# Delete game if  (ONCLICK)
async def delete_current_game(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    game_id = dialog_manager.dialog_data.get("game_id")
    games.pop(game_id, None)


# DO NOT DELETE COMMENTED CODE, IT IS JUST UNFINISHED
# Game registration dialog
game_creation_dialog = Dialog(
    # Window(
    #     Const(""),
    #     Button(Const("Использовать "), id="format_both", on_click=save_default_settings),
    #     state=GameCreation.choosing_default,
    # ),
    Window(
        Const("Введите название для вашей игры."),
        # Jinja("\n<b>Текущее значение</b>: {{title}}", when=need_to_display_current_value),

        # MessageInput(func=save_title, content_types=[ContentType.TEXT]),

        Cancel(Const("Отменить"), on_click=delete_current_game, when=is_register_mode),
        go_back_when_edit_mode,
        state=GameCreation.typing_title,
    ),
    # Window(
    #     Const("Какие игры вы планируете проводить?"),
    #     Jinja("\n<b>Текущее значение</b>: {{cost}}", when=need_to_display_current_value),
    #
    #     Button(Const("Бесплатные"), id="cost_free", on_click=save_cost),
    #     Button(Const("Платные"), id="cost_paid", on_click=save_cost),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.choosing_cost,
    # ),
    # Window(
    #     Const("Сколько вы планируете брать за проведение сессии? Введите ответ в свободной форме."),
    #     Jinja("\n<b>Текущее значение</b>: {{cost}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_cost_number, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.typing_cost,
    # ),
    # Window(
    #     Const("В каком формате будет проводиться игра?"),
    #     Jinja("\n<b>Текущее значение</b>: {{format}}", when=need_to_display_current_value),
    #
    #     Button(Const("Онлайн"), id="format_online_game", on_click=save_format),
    #     Button(Const("Оффлайн"), id="format_offline_game", on_click=save_format),
    #     Button(Const("Текстовая игра"), id="format_text_game", on_click=save_format),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.choosing_format,
    # ),
    # Window(
    #     Const("Где вы планируете проводить игры?\nПожалуйста, не приглашайте игроков к себе домой, это может быть опасно, сессии нужно проводить в публичных местах.\nТакже не стоит указывать точный адрес, эта информация будет доступна всем пользователям бота. Лучше всего указать район."),
    #     Jinja("\n<b>Текущее значение</b>: {{place}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_place, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.typing_place,
    # ),
    # Window(
    #     Const("Какую платформу вы будете использовать для проведения игр? Укажите её и способ общения во время игры."),
    #     Jinja("\n<b>Текущее значение</b>: {{platform}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_platform, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.typing_platform,
    # ),
    # Window(
    #     Const("Когда вы планируете проводить сессии? Напишите удобное для вас время в свободной форме."),
    #     Jinja("\n<b>Текущее значение</b>: {{time}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_time, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.typing_time,
    # ),
    # Window(
    #     Const("Сколько сессий вы планируете провести? Будет ли это ваншот или полноценная компания?"),
    #     Jinja("\n<b>Текущее значение</b>: {{type}}", when=need_to_display_current_value),
    #
    #     Button(Const("Ваншот"), id="type_oneshot_game", on_click=save_type),
    #     Button(Const("Компания"), id="type_company_game", on_click=save_format),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.choosing_type,
    # ),
    # Window(
    #     Const("По какой системе вы будете вести игру?"),
    #     Jinja("\n<b>Текущее значение</b>: {{system}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_system_from_user, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.choosing_system,
    # ),
    # Window(
    #     Multi(
    #         Const("Какое издание вы планируете использовать? Введите ответ в свободной форме"),
    #         Const("или выберите один из предоставленных вариантов", when=is_dnd_chosen),
    #         Const("."),
    #         sep='',
    #     ),
    #     Jinja("\n<b>Текущее значение</b>: {{system}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_edition_from_user, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.choosing_edition,
    # ),
    # Window(
    #     Const("На сколько игроков рассчитано ваше приключение? Выберите одну из предоставленных опций или укажите свою.\nВведите минимальное и максимальное количество через черту, например: 3-5"),
    #     Jinja("\n<b>Текущее значение</b>: {{number_of_players}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_number_of_players_from_user, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.choosing_number_of_players,
    # ),
    # Window(
    #     Const("Игроков какого возраста вы ищите? Выберите одну из предоставленных опций или укажите свою.\nВведите минимальный и максимальный возраст через черту, например: 30-35, 25+, 40-"),
    #     Jinja("\n<b>Текущее значение</b>: {{age}}", when=need_to_display_current_value),
    #
    #
    #     MessageInput(func=save_age_from_user, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.choosing_age,
    # ),
    # Window(
    #     Const("Каким требованиям должны удовлетворять игроки, которых вы ищите?"),
    #     Jinja("\n<b>Текущее значение</b>: {{requirements}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_requirements, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.typing_requirements,
    # ),
    # Window(
    #     Const("Что ждёт игроков? В каком сеттинге будут происходить действия? Дайте описание игры."),
    #     Jinja("\n<b>Текущее значение</b>: {{description}}", when=need_to_display_current_value),
    #
    #     MessageInput(func=save_description, content_types=[ContentType.TEXT]),
    #
    #     go_back_when_edit_mode,
    #     state=GameCreation.typing_description,
    # ),
    on_start=create_new_game_if_needed,
    # getter=get_game_by_id_in_dialog_data,
)