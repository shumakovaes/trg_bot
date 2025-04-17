from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand

from aiogram_dialog import DialogManager, StartMode

from bot.dialogs.general_tools import start_game_creation
# from bot.keyboards.kb_start import make_new_form_keyboard
from bot.states.registration_states import Registration, Profile, MasterForm, PlayerForm
from bot.states.games_states import AllGames, GameCreation

router = Router()


async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/register",
                   description="Регистрация"),
        BotCommand(command="/profile",
                   description="Просмотр и редактирование профиля"),
        BotCommand(command="/player",
                   description="Анкета игрока"),
        BotCommand(command="/master",
                   description="Анкета мастера"),
        BotCommand(command="/games",
                   description="Просмотр статуса и создание игр"),
        BotCommand(command="/create",
                   description="Создать новую игру"),
    ]

    await bot.set_my_commands(main_menu_commands)


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
    await dialog_manager.start(PlayerForm.checking_info)


@router.message(Command("master"))
async def check_profile(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MasterForm.checking_info)


@router.message(Command("games"))
async def check_profile(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(AllGames.checking_games)


@router.message(Command("create"))
async def check_profile(message: Message, dialog_manager: DialogManager):
    await start_game_creation(dialog_manager)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, dialog_manager: DialogManager):
    if dialog_manager.has_context():
        await dialog_manager.done()
        await message.answer(text="Действие отменено.")
    else:
        await message.answer(text="Вы находитесь в состоянии по умолчанию, /cancel не оказывает никакого действия.")


# TODO: add command /about with description of all commands
# TODO: add notifications when unknown command used, maybe notification about successful operations (like profile update)
