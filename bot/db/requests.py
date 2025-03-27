from aiogram import Router, types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.db.models import User
from bot.db.models import UserModel

router = Router()


async def get_user(session: AsyncSession, message: types.Message) -> [UserModel | None]:
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalars().first()
    if not user:
        await message.answer("Сначала зарегистрируйтесь с помощью /register")
        return None
    return UserModel(user)


async def register_user(user: UserModel, session: AsyncSession):
    new_user = user.get_user()
    session.add(new_user)
    await session.commit()


"""
class EditProfile(StatesGroup):
    choosing_field = State()
    editing_name = State()
    editing_age = State()
    editing_city = State()
    editing_game_format = State()
    editing_preferred_systems = State()
    editing_about = State()


class EditPlayer(StatesGroup):
    choosing_field = State()
    editing_experience = State()
    editing_availability = State()


class EditMaster(StatesGroup):
    choosing_field = State()
    editing_style = State()

@router.message(Command(commands=["profile"]))
async def show_profile(message: types.Message, session: AsyncSession):
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

@router.message(Command(commands=["edit"]))
async def edit_profile_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Что вы хотите изменить?",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Имя")],
                [types.KeyboardButton(text="Возраст")],
                [types.KeyboardButton(text="Город")],
                [types.KeyboardButton(text="Формат игры")],
                [types.KeyboardButton(text="Предпочитаемые системы")],
                [types.KeyboardButton(text="О себе")],
                [types.KeyboardButton(text="Анкету Мастера")],
                [types.KeyboardButton(text="Анкету Игрока")],
                [types.KeyboardButton(text="Отмена")],
            ],
            resize_keyboard=True,
        )
    )
    await state.set_state(EditProfile.choosing_field)


@router.message(EditProfile.choosing_field, F.text.casefold() == "Отмена")
async def edit_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Изменения отменены", reply_markup=ReplyKeyboardRemove())


@router.message(EditProfile.choosing_field)
async def edit_field_chosen(message: types.Message, state: FSMContext, session: AsyncSession):
    field = message.text.lower()
    if field == "Имя":
        await state.set_state(EditProfile.editing_name)
        await message.answer("Введите новое имя:", reply_markup=ReplyKeyboardRemove())
    elif field == "Возраст":
        await state.set_state(EditProfile.editing_age)
        await message.answer("Введите ваш возраст:")
    elif field == "Город":
        await state.set_state(EditProfile.editing_city)
        await message.answer("Введите ваш город:")
    elif field == "Формат игры":
        await state.set_state(EditProfile.editing_game_format)
        await message.answer("Выберите формат игры:",
                             reply_markup=types.ReplyKeyboardMarkup(
                                 keyboard=[
                                     [types.KeyboardButton(text="Оффлайн")],
                                     [types.KeyboardButton(text="Онлайн")],
                                     [types.KeyboardButton(text="Оффлайн и Онлайн")],
                                 ],
                                 resize_keyboard=True,
                             )
                             )
    elif field == "О себе":
        await state.set_state(EditProfile.editing_about)
        await message.answer("Напишите о себе:", reply_markup=ReplyKeyboardRemove())


# Обработчики для каждого поля
@router.message(EditProfile.editing_name, F.text)
async def name_chosen(message: types.Message, state: FSMContext, session: AsyncSession):
    await session.execute(
        update(User)
        .where(User.telegram_id == message.from_user.id)
        .values(name=message.text)
    )
    await session.commit()
    await state.clear()
    await message.answer("Имя успешно обновлено!")


@router.message(EditProfile.editing_age, F.text)
async def age_chosen(message: types.Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("Введите число!")
        return
    await session.execute(
        update(User)
        .where(User.telegram_id == message.from_user.id)
        .values(age=int(message.text))
    )
    await session.commit()
    await state.clear()
    await message.answer("Возраст успешно обновлён!")


@router.message(EditProfile.editing_city, F.text)
async def city_chosen(message: types.Message, state: FSMContext, session: AsyncSession):
    await session.execute(
        update(User)
        .where(User.telegram_id == message.from_user.id)
        .values(city=message.text)
    )
    await session.commit()
    await state.clear()
    await message.answer("Город успешно обновлён!")


@router.message(EditProfile.editing_about, F.text)
async def about_chosen(message: types.Message, state: FSMContext, session: AsyncSession):
    await session.execute(
        update(User)
        .where(User.telegram_id == message.from_user.id)
        .values(about=message.text)
    )
    await session.commit()
    await state.clear()
    await message.answer("Информация о вас успешно обновлёна!")


# Аналогичные обработчики для других полей...

@router.message(Command(commands=["edit", "player"]))
async def edit_player_start(message: types.Message, state: FSMContext, session: AsyncSession):
    user = await get_user_or_respond(session, message)
    if not user:
        return

    if not user.player_profile:
        # Создаём профиль игрока если его нет
        player = Player(id=user.id)
        session.add(player)
        await session.commit()

    await message.answer(
        "Что вы хотите изменить в анкете игрока?",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Системы")],
                [types.KeyboardButton(text="Опыт")],
                [types.KeyboardButton(text="Доступность")],
                [types.KeyboardButton(text="Отмена")],
            ],
            resize_keyboard=True,
        )
    )
    await state.set_state(EditPlayer.choosing_field)


@router.message(EditPlayer.editing_systems, F.text)
async def player_systems_chosen(message: types.Message, state: FSMContext, session: AsyncSession):
    systems = [s.strip() for s in message.text.split(",")]
    valid_systems = {'DnD', 'Pathfinder'}

    if not all(s in valid_systems for s in systems):
        await message.answer("Допустимые системы: DnD, Pathfinder")
        return

    await session.execute(
        update(Player)
        .where(Player.id == message.from_user.id)
        .values(preferred_systems=systems)
    )
    await session.commit()
    await state.clear()
    await message.answer("Системы обновлены!")


# Аналогично для мастеров...

@router.message(Command(commands=["edit", "master"]))
async def edit_master_start(message: types.Message, state: FSMContext, session: AsyncSession):
    user = await get_user_or_respond(session, message)
    if not user:
        return

    if not user.master_profile:
        master = Master(id=user.id)
        session.add(master)
        await session.commit()

    await message.answer(
        "Что вы хотите изменить в анкете мастера?",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Системы")],
                [types.KeyboardButton(text="Стиль")],
                [types.KeyboardButton(text="Отмена")],
            ],
            resize_keyboard=True,
        )
    )
    await state.set_state(EditMaster.choosing_field)
"""
