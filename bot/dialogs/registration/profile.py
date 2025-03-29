from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.kbd import Button, Row, Column, Back, SwitchTo, Select, Group, Cancel, Start

from bot.states.registration_states import Registration, Profile, PlayerForm, MasterForm

from bot.db.current_requests import user, get_user_general

# Profile dialog
dialog = Dialog(
    # Checking profile
    Window(
        Jinja(
            "Это ваш профиль, в нём указана основная информация о вас. \nЕё увидят игроки, если вы опубликуете игру, и мастера, если вы откликнитесь на существующую заявку.  \n\n" +
            "<b>Имя</b>: {{name}}\n" +
            "<b>Возраст</b>: {{age}}\n" +
            "<b>Город</b>: {{city}}\n" +
            "<b>Часовой пояс</b>: {{time_zone}}\n" +
            "<b>Роль</b>: {{role}}\n" +
            "<b>Формат игры</b>: {{format}}\n" +
            "<b>О себе</b>: {{about_info}}\n",
        ),

        SwitchTo(Const("Редактировать анкету"), state=Profile.choosing_what_to_edit, id="edit_form",
                 show_mode=ShowMode.SEND),
        Row(Start(Const("Анкета игрока"), state=PlayerForm.checking_info, id="player_form_from_profile"),
            Start(Const("Анкета мастера"), state=MasterForm.checking_info, id="master_form_from_profile"), ),
        Cancel(Const("Выйти")),

        getter=get_user_general,
        state=Profile.checking_info,
    ),
    # Editing profile
    Window(
        Const("Выберите, что хотите отредактировать."),

        Start(Const("Имя"), state=Registration.typing_nickname, id="edit_nickname_general", data={"mode": "edit"}),
        Start(Const("Возраст"), state=Registration.typing_age, id="edit_age_general", data={"mode": "edit"}),
        Start(Const("Город"), state=Registration.choosing_city, id="edit_city_general", data={"mode": "edit"}),
        # TODO: ? forbid changing time zone than city is default
        Start(Const("Часовой пояс"), state=Registration.choosing_time_zone, id="edit_time_zone_general", data={"mode": "edit"}),
        Start(Const("Роль"), state=Registration.choosing_role, id="edit_role_general", data={"mode": "edit"}),
        Start(Const("Формат игры"), state=Registration.choosing_format, id="edit_format_general", data={"mode": "edit"}),
        Start(Const("О себе"), state=Registration.typing_about_information, id="edit_about_info_general",
              data={"mode": "edit"}),
        Start(Const("Пройти регистрацию заново"), state=Registration.typing_nickname, id="register_again_general",
              data={"mode": "register"}),
        Back(Const("Назад"), id="back_to_checking_info_general"),

        state=Profile.choosing_what_to_edit,
    ),
)
