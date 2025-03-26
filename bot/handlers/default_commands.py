from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from aiogram_dialog import DialogManager, StartMode

# from bot.keyboards.kb_start import make_new_form_keyboard
from bot.states.general_states import Registration, Profile, MasterForm, PlayerForm

router = Router()


# TODO: change description, make in more informative
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
    await dialog_manager.start(Registration.typing_nickname, data={"mode": "register"})


@router.message(Command("profile"))
async def check_profile(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(Profile.checking_info)


@router.message(Command("player"))
async def check_profile(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(PlayerForm.player_form)


@router.message(Command("master"))
async def check_profile(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MasterForm.master_form)

# TODO: add command /about with description of all commands
# TODO: add notifications when unknown command used, maybe notification about successful operations (like profile update)
