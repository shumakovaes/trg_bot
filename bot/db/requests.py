from aiogram import Router, types, F
from aiogram.filters.command import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.db.models import User

router = Router()


@router.message(Command(commands=["profile"]))
async def show_profile(message: types.Message, session: AsyncSession):
    """
    Show user profile information

    :param message: Telegram message with /profile command
    :param session: SQLAlchemy DB session
    """
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalars().first()

    if not user:
        await message.answer("Вы еще не зарегистрированы. Используйте команду /register.")
        return

    profile_text = (
        f"<b>Ваш профиль</b>:\n"
        f"Имя: <b>{user.name}</b>\n"
        f"Возраст: <b>{user.age}</b>\n"
        f"Город: <b>{user.city}</b>\n"
        f"Часовой пояс: <b>{user.time_zone}</b>\n"
        f"Роль: <b>{user.role}</b>\n"
        f"Формат игры: <b>{user.format}</b>\n"
        f"О себе: <b>{user.about_info or 'Не указано'}</b>\n"
    )

    await message.answer(profile_text, parse_mode="HTML")


@router.message(Command(commands=["register"]))
async def register_user(message: types.Message, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalars().first()

    if user:
        await message.answer("Вы уже зарегистрированы! Используйте /profile для просмотра профиля.")
        return

    new_user = User(
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
        age=18,  # Можно обновить позже через команду
        format="Оффлайн и Онлайн",
        city="Не указан",
        time_zone="GMT+0",
        role="Игрок",
        about_info=""
    )
    session.add(new_user)
    await session.commit()

    await message.answer("Вы успешно зарегистрированы! Используйте /profile для просмотра профиля.")
