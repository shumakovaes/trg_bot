from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from aiogram_dialog import DialogManager, StartMode

from bot.dialogs.registration import Registration

# from bot.keyboards.kb_start import make_new_form_keyboard
from bot.states.general_states import Registration

router = Router()

@router.message(CommandStart())
async def start_message(message: Message):
    await message.answer(
        "Привет! Я бот по подбору сессий для настольных игр.\n"
        "Чтобы продолжить работу, вам необходимо заполнить небольшую анкету.\n\n"
        "Для регистрации введите команду /register",
    )

# TODO: check if profile is already exist
@router.message(Command("register"))
async def register_profile(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(Registration.typing_nickname)
