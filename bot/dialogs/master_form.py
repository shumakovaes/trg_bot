from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Column, Back, SwitchTo, Select, Group, Cancel, Start

from bot.states.general_states import Registration, Profile, PlayerForm, MasterForm

# TODO: change to database query
from bot.dialogs.registration import  user

# TODO: implement player form
# Master form
dialog = Dialog(
    Window(
        Const("Анкета мастера."),
        Cancel(Const("Завершить.")),
        state=MasterForm.master_form,
    ),
)