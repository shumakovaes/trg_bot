from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Row, Column, Next, SwitchTo

from bot.states.general_states import Registration

# TODO: implement database
profile = {}

async def save_format(callback: CallbackQuery, button: Button, manager: DialogManager):
    profile["format"] = button.text

async def save_city(callback: CallbackQuery, button: Button, manager: DialogManager):
    profile["city"] = button.text

async def save_time_zone(callback: CallbackQuery, button: Button, manager: DialogManager):
    profile["time_zone"] = button.text

async def save_role(callback: CallbackQuery, button: Button, manager: DialogManager):
    profile["role"] = button.text

# TODO: change phrases, make them more friendly
# TODO: change Const to Jinja
dialog = Dialog(
    # TODO: this is stub
    Window(
        Const("Введите ваше имя или никнейм."),
        Next(text=Const("Next"), id="next"),
        state=Registration.typing_nickname
    ),
    Window(
        Const("Введите ваш возраст, число от 12 до 99."),
        Next(text=Const("Next"), id="next"),
        state=Registration.typing_age
    ),
    Window(
        Const("Выберете удобный для вас формат проведения игр.\n"
              "При создании игры это настройка будет применена по умолчанию, но вы сможете изменить её при создании сессии."),
        Row(SwitchTo(Const("Оффлайн"), state=Registration.choosing_city, id="format_offline", on_click=save_format),
            SwitchTo(Const("Онлайн"), state=Registration.choosing_city, id="format_online", on_click=save_format)),
        SwitchTo(Const("Оффлайн и Онлайн"), state=Registration.choosing_city, id="format_both", on_click=save_format),
        state=Registration.choosing_format
    ),
    # TODO: display not const, but the most popular cities
    Window(
        Const("Выберите город, в котором живёте. Если его нет в списке, то отправьте его название ответным сообщением."),
        Column(SwitchTo(text=Const("Москва"), state=Registration.choosing_role, id="city_moscow", on_click=save_city),
               SwitchTo(text=Const("Санкт-Петербург"), state=Registration.choosing_role, id="city_saint_petersburg", on_click=save_city),
               SwitchTo(text=Const("Новосибирск"), state=Registration.choosing_role, id="city_novosibirsk", on_click=save_city),
               SwitchTo(text=Const("Екатеринбург"), state=Registration.choosing_role, id="city_ekaterinburg", on_click=save_city),
               SwitchTo(text=Const("Казань"), state=Registration.choosing_role, id="city_kazan", on_click=save_city),
               SwitchTo(text=Const("Нижний Новгород"), state=Registration.choosing_role, id="city_nizhny_ovgorod", on_click=save_city)),
        state=Registration.choosing_city
    ),
    Window(
        Const("Выберете ваш часовой пояс."),
        Next(text=Const("Next"), id="next"),
        state=Registration.choosing_time_zone
    ),
    Window(
        Const("Выберете роль, в которой будете выступать."),
        Row(SwitchTo(Const("Игрок"), state=Registration.typing_about_information, id="role_player", on_click=save_role),
            SwitchTo(Const("Мастер"), state=Registration.typing_about_information, id="role_master", on_click=save_role)),
        SwitchTo(Const("Игрок и Мастер"), state=Registration.typing_about_information, id="role_player", on_click=save_role),
        state=Registration.choosing_role
    ),
    Window(
        Const("Расскажите немного о себе."),
        # MessageInput(),
        Next(text=Const("Next"), id="next"),
        state=Registration.typing_about_information
    )
)