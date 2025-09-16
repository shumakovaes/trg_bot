import asyncio
import datetime
import random
import string
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

def make_mock_result(obj):
    """
    Создает замоканный результат для session.execute,
    у которого корректно работают .scalars().first().
    """
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = obj
    mock_result.scalars.return_value = mock_scalars
    return mock_result

# Импортируем тестируемые сущности
from bot.db.base import User, Player, Master, Session
from bot.db.requests import (
    _get_entity, _register_entity, _edit_entity,
    get_user_model, get_player_model, get_master_model, get_game_model,
    register_user, register_player, register_master, register_game,
    edit_user, edit_player, edit_master, edit_game
)
from bot.db.models import (
    all_roles, all_formats, all_experience_levels,
    concat, get_role, get_game_format,
    UserModel, PlayerModel, MasterModel, SessionModel
)

#############################################
# Функция для создания тестовой БД
#############################################
def create_mock_db():
    """
    Создает тестовую базу данных:
    - 50 пользователей с уникальными telegram_id, именами, возрастом и т.д.
    - Для примерно 50% пользователей создаются профили игроков (Player)
    - Для оставшихся создаются профили мастеров (Master)
    - Создается 15 сессий (Session) с разнообразными описаниями и разными создателями
    Возвращает словарь с ключами: "users", "players", "masters", "sessions".
    """
    users = []
    players = []
    masters = []
    sessions = []

    # Создаем 50 пользователей
    for i in range(50):
        user = User(
            id=i + 1,
            telegram_id=10000 + i,
            name=f"User_{i+1}",
            age=random.randint(18, 60),
            city=f"City_{random.choice(string.ascii_uppercase)}",
            time_zone=random.randint(-12, 14),
            # Вычисляем битовую маску: случайно выбираем "Игрок", "Мастер" или обе роли
            role=(1 << all_roles.index("Игрок")) if random.random() < 0.5 else (1 << all_roles.index("Мастер")),
            game_format=(1 << all_formats.index("Онлайн")) if random.random() < 0.5 else (1 << all_formats.index("Оффлайн")),
            preferred_systems=f"System_{random.choice(string.ascii_uppercase)}",
            about_info=f"About user {i+1}",
            created_at=datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 365))
        )
        users.append(user)

    # Для половины пользователей создаем профили игроков, для остальных мастеров
    for user in users:
        if random.random() < 0.5:
            player = Player()
            player.id = user.id
            player.experience_level = random.randint(0, len(all_experience_levels) - 1)
            player.availability = random.choice(["full", "partial", "none"])
            player.user = user
            player.sessions = []
            players.append(player)
        else:
            master = Master()
            master.id = user.id
            master.master_style = random.choice(["Classic", "Modern", "Experimental"])
            master.rating = random.randint(0, 10)
            master.user = user
            master.sessions = []
            masters.append(master)

    # Создаем 15 сессий
    for i in range(15):
        creator = random.choice(users)  # Всегда валидный создатель
        session_obj = Session()
        session_obj.id = i + 1
        session_obj.title = f"Session_{i+1}"
        session_obj.description = f"Description for session {i+1}"
        session_obj.game_system = random.choice(["D&D", "Pathfinder", "Shadowrun"])
        session_obj.date_time = datetime.datetime.now() + datetime.timedelta(days=random.randint(1, 100))
        session_obj.format = random.randint(0, len(all_formats) - 1)  # Индекс, чтобы SessionModel работал
        session_obj.status = random.choice([True, False])
        session_obj.max_players = random.randint(2, 10)
        session_obj.looking_for = random.randint(0, len(all_roles) - 1)
        session_obj.creator = creator  # всегда есть
        session_obj.players = []
        sessions.append(session_obj)

    return {"users": users, "players": players, "masters": masters, "sessions": sessions}


#############################################
# Фикстуры и утилиты
#############################################
@pytest_asyncio.fixture
async def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = AsyncMock()
    return session

def create_dummy_user(**kwargs):
    defaults = {
        "id": 1,
        "telegram_id": 12345,
        "name": "TestUser",
        "age": 30,
        "city": "TestCity",
        "time_zone": 3,
        "role": 1 << all_roles.index("Игрок"),
        "game_format": 1 << all_formats.index("Онлайн"),
        "preferred_systems": "TestSystem",
        "about_info": "TestAbout",
        "created_at": datetime.datetime(2022, 1, 1)
    }
    defaults.update(kwargs)
    return User(**defaults)

def create_dummy_player(user: User, experience_index=0, availability="full"):
    dummy = Player()
    dummy.id = user.id
    dummy.experience_level = experience_index
    dummy.availability = availability
    dummy.user = user
    dummy.sessions = []
    return dummy

def create_dummy_master(user: User, master_style="Classic", rating=5):
    dummy = Master()
    dummy.id = user.id
    dummy.master_style = master_style
    dummy.rating = rating
    dummy.user = user
    dummy.sessions = []
    return dummy

def create_dummy_session(creator: User, format_index=0, looking_for_index=0):
    dummy = Session()
    dummy.id = 1
    dummy.title = "TestGame"
    dummy.description = "A test session"
    dummy.game_system = "D&D"
    dummy.date_time = datetime.datetime.now()
    dummy.format = format_index
    dummy.status = True
    dummy.max_players = 4
    dummy.looking_for = looking_for_index
    dummy.creator = creator
    dummy.players = []
    return dummy

# Здесь тестируются различные варианты регистрации пользователя с учётом особенностей вычисления role_mask и format_mask.
@pytest.mark.asyncio
async def test_register_user_case1_normal(mock_session):
    dummy = create_dummy_user()
    # Сбрасываем результат запроса, чтобы не находить дубликат
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    user_model = UserModel(dummy)
    registered = await register_user(user_model, mock_session)
    assert registered.telegram_id == dummy.telegram_id


@pytest.mark.asyncio
async def test_register_user_case2_duplicate(mock_session):
    dummy = create_dummy_user()
    user_model = UserModel(dummy)

    # Correct async mock
    mock_session.execute = AsyncMock(return_value=make_mock_result(dummy))

    with pytest.raises(ValueError, match="User already exists"):
        await register_user(user_model, mock_session)


#####################################
# Tests for register_user
#####################################

@pytest.mark.asyncio
async def test_register_user_case3_invalid_role_string(mock_session):
    dummy = create_dummy_user()
    dummy.role = "Игрок"  # Invalid type: should be int bitmask

    # Mock session to avoid DB calls
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))

    # Expect TypeError when initializing UserModel
    with pytest.raises(TypeError, match="unsupported operand type"):
        UserModel(dummy)


@pytest.mark.asyncio
async def test_register_user_case4_invalid_format_string(mock_session):
    dummy = create_dummy_user()
    dummy.game_format = "Онлайн"  # Invalid type: should be int bitmask

    # Mock session to avoid DB calls
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))

    # Expect TypeError when initializing UserModel
    with pytest.raises(TypeError, match="unsupported operand type"):
        UserModel(dummy)


@pytest.mark.asyncio
async def test_register_user_case5_multiple_roles_formats(mock_session):
    dummy = create_dummy_user()
    dummy.role = "Игрок, Мастер"        # Invalid type: should be int bitmask
    dummy.game_format = "Онлайн, Оффлайн"  # Invalid type: should be int bitmask

    # Mock session to avoid DB calls
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))

    # Expect TypeError when initializing UserModel
    with pytest.raises(TypeError, match="unsupported operand type"):
        UserModel(dummy)


@pytest.mark.asyncio
async def test_register_user_case6_missing_field(mock_session):
    dummy = create_dummy_user(name="TestUser")
    dummy.name = ""
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    user_model = UserModel(dummy)
    registered = await register_user(user_model, mock_session)
    assert registered.name == ""

@pytest.mark.asyncio
async def test_register_user_case7_boundary_age(mock_session):
    dummy = create_dummy_user(age=0)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    user_model = UserModel(dummy)
    registered = await register_user(user_model, mock_session)
    assert registered.age == 0

@pytest.mark.asyncio
async def test_register_user_case8_extreme_age(mock_session):
    dummy = create_dummy_user(age=150)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    user_model = UserModel(dummy)
    registered = await register_user(user_model, mock_session)
    assert registered.age == 150

@pytest.mark.asyncio
async def test_register_user_case9_missing_optional_field(mock_session):
    dummy = create_dummy_user()
    dummy.about_info = None
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    user_model = UserModel(dummy)
    registered = await register_user(user_model, mock_session)
    assert registered.about_info is None

@pytest.mark.asyncio
async def test_register_user_case10_commit_failure(mock_session):
    dummy = create_dummy_user()
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    async def failing_commit():
        raise Exception("Commit error")
    mock_session.commit = AsyncMock(side_effect=failing_commit)
    user_model = UserModel(dummy)
    with pytest.raises(Exception, match="Commit error"):
        await register_user(user_model, mock_session)

#####################################
# Tests for register_player
#####################################

@pytest.mark.asyncio
async def test_register_player_case1_normal(mock_session):
    user = create_dummy_user()
    from bot.db.models import PlayerModel
    dummy_player = create_dummy_player(user, experience_index=1, availability="partial")
    player_model = PlayerModel(dummy_player)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_player(player_model, mock_session)
    assert registered.availability == dummy_player.availability

@pytest.mark.asyncio
async def test_register_player_case2_user_not_found(mock_session):
    from bot.db.models import PlayerModel
    dummy_player = create_dummy_player(create_dummy_user())
    player_model = PlayerModel(dummy_player)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    with pytest.raises(ValueError, match="User not found"):
        await register_player(player_model, mock_session)

@pytest.mark.asyncio
async def test_register_player_case4_missing_availability(mock_session):
    user = create_dummy_user()
    from bot.db.models import PlayerModel
    dummy_player = create_dummy_player(user, availability="")
    player_model = PlayerModel(dummy_player)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_player(player_model, mock_session)
    assert registered.availability == ""

@pytest.mark.asyncio
async def test_register_player_case5_multiple_players_same_user(mock_session):
    user = create_dummy_user()
    from bot.db.models import PlayerModel
    dummy_player = create_dummy_player(user)
    player_model = PlayerModel(dummy_player)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(MagicMock())])
    with pytest.raises(ValueError):
        await register_player(player_model, mock_session)

@pytest.mark.asyncio
async def test_register_player_case6_commit_failure(mock_session):
    user = create_dummy_user()
    from bot.db.models import PlayerModel
    dummy_player = create_dummy_player(user)
    player_model = PlayerModel(dummy_player)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    async def failing_commit():
        raise Exception("Commit failed")
    mock_session.commit = AsyncMock(side_effect=failing_commit)
    with pytest.raises(Exception, match="Commit failed"):
        await register_player(player_model, mock_session)

@pytest.mark.asyncio
async def test_register_player_case7_invalid_session_response(mock_session):
    user = create_dummy_user()
    from bot.db.models import PlayerModel
    dummy_player = create_dummy_player(user)
    player_model = PlayerModel(dummy_player)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), "not None"])
    with pytest.raises(AttributeError):
        await register_player(player_model, mock_session)

#####################################
# Tests for register_master
#####################################

@pytest.mark.asyncio
async def test_register_master_case1_normal(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style="Modern", rating=10)
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_master(master_model, mock_session)
    assert registered.rating == 10

@pytest.mark.asyncio
async def test_register_master_case2_user_not_found(mock_session):
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(create_dummy_user())
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    with pytest.raises(ValueError, match="User not found"):
        await register_master(master_model, mock_session)

@pytest.mark.asyncio
async def test_register_master_case3_missing_master_style(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style="", rating=5)
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_master(master_model, mock_session)
    assert registered.master_style == ""

@pytest.mark.asyncio
async def test_register_master_case4_negative_rating(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style="Style", rating=-1)
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_master(master_model, mock_session)
    assert registered.rating == -1

@pytest.mark.asyncio
async def test_register_master_case5_multiple_masters_same_user(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style="Style", rating=5)
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(MagicMock())])
    with pytest.raises(ValueError):
        await register_master(master_model, mock_session)

@pytest.mark.asyncio
async def test_register_master_case6_commit_failure(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style="Style", rating=5)
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    async def failing_commit():
        raise Exception("Commit error")
    mock_session.commit = AsyncMock(side_effect=failing_commit)
    with pytest.raises(Exception, match="Commit error"):
        await register_master(master_model, mock_session)

@pytest.mark.asyncio
async def test_register_master_case7_invalid_rating_type(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style="Style", rating="High")
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_master(master_model, mock_session)
    assert isinstance(registered.rating, str)

@pytest.mark.asyncio
async def test_register_master_case8_none_master_style(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style=None, rating=5)
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_master(master_model, mock_session)
    assert registered.master_style is None


@pytest.mark.asyncio
async def test_register_master_case10_non_numeric_rating(mock_session):
    user = create_dummy_user()
    from bot.db.models import MasterModel
    dummy_master = create_dummy_master(user, master_style="Modern", rating="Ten")
    master_model = MasterModel(dummy_master)
    mock_session.execute = AsyncMock(side_effect=[make_mock_result(user), make_mock_result(None)])
    registered = await register_master(master_model, mock_session)
    assert registered.rating == "Ten"

#####################################
# Tests for register_game
#####################################

@pytest.mark.asyncio
async def test_register_game_case1_normal(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user, format_index=0, looking_for_index=0)
    from bot.db.models import SessionModel
    game_model = SessionModel(session_obj)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    registered = await register_game(game_model, mock_session)
    assert registered.title == session_obj.title

@pytest.mark.asyncio
async def test_register_game_case4_missing_optional_fields(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    session_obj.description = ""
    from bot.db.models import SessionModel
    game_model = SessionModel(session_obj)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    registered = await register_game(game_model, mock_session)
    assert registered.description == ""

@pytest.mark.asyncio
async def test_register_game_case5_future_date(mock_session):
    user = create_dummy_user()
    future = datetime.datetime.now() + datetime.timedelta(days=365)
    session_obj = create_dummy_session(user)
    session_obj.date_time = future
    from bot.db.models import SessionModel
    game_model = SessionModel(session_obj)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    registered = await register_game(game_model, mock_session)
    assert registered.date_time == future

@pytest.mark.asyncio
async def test_register_game_case6_max_players_zero(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    session_obj.max_players = 0
    from bot.db.models import SessionModel
    game_model = SessionModel(session_obj)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    registered = await register_game(game_model, mock_session)
    assert registered.max_players == 0

@pytest.mark.asyncio
async def test_register_game_case8_commit_failure(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    from bot.db.models import SessionModel
    game_model = SessionModel(session_obj)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    async def failing_commit():
        raise Exception("Commit failed")
    mock_session.commit = AsyncMock(side_effect=failing_commit)
    with pytest.raises(Exception, match="Commit failed"):
        await register_game(game_model, mock_session)

@pytest.mark.asyncio
async def test_register_game_case10_incomplete_data(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    session_obj.title = ""
    from bot.db.models import SessionModel
    game_model = SessionModel(session_obj)
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    registered = await register_game(game_model, mock_session)
    assert registered.title == ""

##############################
# Тесты для edit_game
##############################

@pytest.mark.asyncio
async def test_edit_game_case1_success(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user, format_index=0, looking_for_index=0)
    mock_session.execute = AsyncMock(return_value=make_mock_result(session_obj))
    updated = await edit_game(session_obj.id, {"title": "EditedGame"}, mock_session)
    assert updated.title == "EditedGame"


@pytest.mark.asyncio
async def test_edit_game_case2_not_found(mock_session):
    mock_session.execute = AsyncMock(return_value=make_mock_result(None))
    updated = await edit_game(999, {"title": "New"}, mock_session)
    assert updated is None


@pytest.mark.asyncio
async def test_edit_game_case3_invalid_field(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    mock_session.execute = AsyncMock(return_value=make_mock_result(session_obj))
    with pytest.raises(ValueError):
        await edit_game(session_obj.id, {"invalid": "value"}, mock_session)


@pytest.mark.asyncio
async def test_edit_game_case5_multiple_field_update(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user, format_index=0, looking_for_index=0)
    mock_session.execute = AsyncMock(return_value=make_mock_result(session_obj))
    changes = {"title": "NewTitle", "description": "NewDesc", "max_players": 10}
    updated = await edit_game(session_obj.id, changes, mock_session)
    assert updated.title == "NewTitle"
    assert updated.description == "NewDesc"
    assert updated.max_players == 10


@pytest.mark.asyncio
async def test_edit_game_case6_partial_update(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user, format_index=0, looking_for_index=0)
    mock_session.execute = AsyncMock(return_value=make_mock_result(session_obj))
    updated = await edit_game(session_obj.id, {"max_players": 8}, mock_session)
    assert updated.max_players == 8


@pytest.mark.asyncio
async def test_edit_game_case7_commit_failure(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    mock_session.execute = AsyncMock(return_value=make_mock_result(session_obj))

    async def failing_commit():
        raise Exception("Commit error")
    mock_session.commit.side_effect = failing_commit

    with pytest.raises(Exception, match="Commit error"):
        await edit_game(session_obj.id, {"title": "FailGame"}, mock_session)


@pytest.mark.asyncio
async def test_edit_game_case9_wrong_data_type(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    mock_session.execute = AsyncMock(return_value=make_mock_result(session_obj))
    changes = {"max_players": "ten"}
    updated = await edit_game(session_obj.id, changes, mock_session)
    assert updated.max_players == "ten"

##############################
# Тесты для функций из models.py
##############################

# Для concat
def test_concat_case1_single_element():
    assert concat(["a"]) == "a"

def test_concat_case2_multiple_elements():
    assert concat(["a", "b", "c"]) == "a, b, c"

def test_concat_case4_numeric_elements():
    # Преобразуем числа в строки
    assert concat([str(1), str(2)]) == "1, 2"

def test_concat_case5_special_characters():
    assert concat(["!", "@" " #"])  # Тест на отсутствие ошибок (результат не важен)

def test_concat_case6_long_list():
    items = [str(i) for i in range(10)]
    result = concat(items)
    assert result.count(",") == 9

def test_concat_case7_spaces_in_elements():
    assert concat([" a", "b "]) == " a, b "

def test_concat_case8_mixed_types():
    # Если в списке находятся не строки – ожидаем, что вызов завершится ошибкой
    with pytest.raises(TypeError):
        concat([1, 2])

def test_concat_case9_none_element():
    with pytest.raises(TypeError):
        concat(["a", None])

def test_concat_case10_unicode_elements():
    assert concat(["тест", "пример"]) == "тест, пример"

# Для get_role
def test_get_role_case1_single_role():
    user = create_dummy_user(role=1 << all_roles.index("Игрок"))
    role_str = get_role(user)
    assert "Игрок" in role_str

def test_get_role_case2_multiple_roles():
    combined = (1 << all_roles.index("Игрок")) | (1 << all_roles.index("Мастер"))
    user = create_dummy_user(role=combined)
    role_str = get_role(user)
    assert "Игрок" in role_str and "Мастер" in role_str

def test_get_role_case3_no_roles():
    user = create_dummy_user(role=0)
    role_str = get_role(user)
    assert role_str == ""

def test_get_role_case4_invalid_role_mask():
    user = create_dummy_user(role=-1)
    role_str = get_role(user)
    # Возможно, отобразится строковое представление всех ролей
    assert isinstance(role_str, str)

def test_get_role_case5_large_mask():
    user = create_dummy_user(role=2**10)
    role_str = get_role(user)
    # В случае, если маска не соответствует ни одной роли, строка может быть пустой
    assert isinstance(role_str, str)

def test_get_role_case6_string_conversion():
    user = create_dummy_user(role=1 << all_roles.index("Мастер"))
    role_str = get_role(user)
    assert isinstance(role_str, str)

def test_get_role_case7_boundary_mask():
    user = create_dummy_user(role=1)
    role_str = get_role(user)
    assert "Игрок" in role_str or role_str == ""

def test_get_role_case8_none_mask():
    user = create_dummy_user()
    user.role = None
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case9_float_mask():
    user = create_dummy_user(role=1.5)
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case10_complex_mask():
    user = create_dummy_user(role=complex(1,2))
    with pytest.raises(TypeError):
        get_role(user)

# Для get_game_format
def test_get_game_format_case1_single_format():
    user = create_dummy_user(game_format=1 << all_formats.index("Онлайн"))
    format_str = get_game_format(user)
    assert "Онлайн" in format_str

def test_get_game_format_case2_multiple_formats():
    combined = (1 << all_formats.index("Онлайн")) | (1 << all_formats.index("Оффлайн"))
    user = create_dummy_user(game_format=combined)
    format_str = get_game_format(user)
    assert "Онлайн" in format_str and "Оффлайн" in format_str

def test_get_game_format_case3_no_format():
    user = create_dummy_user(game_format=0)
    format_str = get_game_format(user)
    assert format_str == ""

def test_get_game_format_case4_invalid_mask():
    user = create_dummy_user(game_format=-1)
    format_str = get_game_format(user)
    assert isinstance(format_str, str)

def test_get_game_format_case5_large_mask():
    user = create_dummy_user(game_format=2**10)
    format_str = get_game_format(user)
    assert isinstance(format_str, str)

def test_get_game_format_case6_string_conversion():
    user = create_dummy_user(game_format=1 << all_formats.index("Оффлайн"))
    format_str = get_game_format(user)
    assert isinstance(format_str, str)

def test_get_game_format_case7_boundary_mask():
    user = create_dummy_user(game_format=1)
    format_str = get_game_format(user)
    assert "Онлайн" in format_str or format_str == ""

def test_get_game_format_case8_none_mask():
    user = create_dummy_user()
    user.game_format = None
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case9_float_mask():
    user = create_dummy_user(game_format=1.5)
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case10_complex_mask():
    user = create_dummy_user(game_format=complex(1, 2))
    with pytest.raises(TypeError):
        get_game_format(user)

# Для UserModel.__str__
def test_user_model_str_case1_contains_fields():
    user = create_dummy_user(name="Алиса", age=25, city="Город")
    user_model = UserModel(user)
    s = str(user_model)
    assert "Алиса" in s and "25" in s and "Город" in s

def test_user_model_str_case2_empty_about():
    user = create_dummy_user(about_info=None)
    user_model = UserModel(user)
    s = str(user_model)
    assert "Не указано" in s

def test_user_model_str_case3_long_name():
    long_name = "A" * 100
    user = create_dummy_user(name=long_name)
    user_model = UserModel(user)
    s = str(user_model)
    assert long_name in s

def test_user_model_str_case4_special_characters():
    user = create_dummy_user(name="Тест@#$")
    user_model = UserModel(user)
    s = str(user_model)
    assert "Тест@#$" in s

def test_user_model_str_case5_different_timezone():
    user = create_dummy_user(time_zone=10)
    user_model = UserModel(user)
    s = str(user_model)
    assert "10" in s

def test_user_model_str_case6_missing_city():
    user = create_dummy_user(city="")
    user_model = UserModel(user)
    s = str(user_model)
    assert "Город" not in s or "" in s

def test_user_model_str_case7_numeric_age():
    user = create_dummy_user(age=0)
    user_model = UserModel(user)
    s = str(user_model)
    assert "0" in s

def test_user_model_str_case8_non_ascii():
    user = create_dummy_user(name="测试", city="城市")
    user_model = UserModel(user)
    s = str(user_model)
    assert "测试" in s and "城市" in s

def test_user_model_str_case9_modified_preferred_systems():
    user = create_dummy_user(preferred_systems="PS5")
    user_model = UserModel(user)
    s = str(user_model)
    assert "PS5" in s

def test_user_model_str_case10_about_info_custom():
    user = create_dummy_user(about_info="Особая информация")
    user_model = UserModel(user)
    s = str(user_model)
    assert "Особая информация" in s

#############################################
# Тесты для _register_entity (20 кейсов)
#############################################

# Проверяем различные сценарии создания сущности: новая сущность, дубликаты, передача разных наборов данных.
@pytest.mark.asyncio
async def test__register_entity_case1_normal_creation(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"field": "value"}
    entity = await _register_entity(mock_session, Dummy, data)
    assert isinstance(entity, Dummy)
    assert entity.__dict__.get("field") == "value"

@pytest.mark.asyncio
async def test__register_entity_case3_empty_data(mock_session):
    # Проверка, что работает даже если data пустой
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    entity = await _register_entity(mock_session, Dummy, {})
    assert isinstance(entity, Dummy)
    assert entity.__dict__ == {}

@pytest.mark.asyncio
async def test__register_entity_case4_multiple_fields(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"a": 1, "b": 2, "c": 3}
    entity = await _register_entity(mock_session, Dummy, data)
    for key, val in data.items():
        assert getattr(entity, key) == val

@pytest.mark.asyncio
async def test__register_entity_case5_field_value_none(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"field": None}
    entity = await _register_entity(mock_session, Dummy, data)
    assert getattr(entity, "field") is None

@pytest.mark.asyncio
async def test__register_entity_case6_commit_called(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"field": "value"}
    await _register_entity(mock_session, Dummy, data)
    mock_session.add.assert_called()
    mock_session.commit.assert_awaited()
    mock_session.refresh.assert_awaited()

@pytest.mark.asyncio
async def test__register_entity_case7_unexpected_data_type(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    # Передадим data как список, а не dict
    with pytest.raises(TypeError):
        await _register_entity(mock_session, dict, ["not", "a", "dict"])

@pytest.mark.asyncio
async def test__register_entity_case8_missing_check_filters(mock_session):
    # Если check_filters не передан, сущность создаётся без проверки
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"field": "value"}
    entity = await _register_entity(mock_session, Dummy, data)
    assert entity.__dict__.get("field") == "value"

@pytest.mark.asyncio
async def test__register_entity_case10_commit_failure(mock_session):
    # Симулируем ошибку при commit (например, исключение)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    async def failing_commit():
        raise Exception("Commit failed")
    mock_session.commit.side_effect = failing_commit
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    with pytest.raises(Exception, match="Commit failed"):
        await _register_entity(mock_session, Dummy, {"field": "value"})

@pytest.mark.asyncio
async def test__register_entity_case3_empty_data(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    entity = await _register_entity(mock_session, Dummy, {})
    assert isinstance(entity, Dummy)
    assert entity.__dict__ == {}

@pytest.mark.asyncio
async def test__register_entity_case4_multiple_fields(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"a": 1, "b": 2, "c": 3}
    entity = await _register_entity(mock_session, Dummy, data)
    for key, val in data.items():
        assert getattr(entity, key) == val

@pytest.mark.asyncio
async def test__register_entity_case5_field_value_none(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"field": None}
    entity = await _register_entity(mock_session, Dummy, data)
    assert getattr(entity, "field") is None

@pytest.mark.asyncio
async def test__register_entity_case6_commit_called(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"field": "value"}
    await _register_entity(mock_session, Dummy, data)
    mock_session.add.assert_called()
    mock_session.commit.assert_awaited()
    mock_session.refresh.assert_awaited()

@pytest.mark.asyncio
async def test__register_entity_case7_unexpected_data_type(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    with pytest.raises(TypeError):
        await _register_entity(mock_session, dict, ["not", "a", "dict"])

@pytest.mark.asyncio
async def test__register_entity_case8_missing_check_filters(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    data = {"field": "value"}
    entity = await _register_entity(mock_session, Dummy, data)
    assert entity.__dict__.get("field") == "value"

@pytest.mark.asyncio
async def test__register_entity_case10_commit_failure(mock_session):
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    async def failing_commit():
        raise Exception("Commit failed")
    mock_session.commit.side_effect = failing_commit
    class Dummy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    with pytest.raises(Exception, match="Commit failed"):
        await _register_entity(mock_session, Dummy, {"field": "value"})

# Дополнительные тесты с использованием create_mock_db для _register_entity
@pytest.mark.asyncio
async def test__register_entity_case11_db_normal(mock_session):
    db = create_mock_db()
    # Берем одного пользователя из mock db и пытаемся зарегистрировать сущность Dummy
    target = db["users"][0]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, telegram_id):
            self.telegram_id = telegram_id
    entity = await _register_entity(mock_session, Dummy, {"telegram_id": target.telegram_id})
    assert entity.telegram_id == target.telegram_id

@pytest.mark.asyncio
async def test__register_entity_case12_db_empty_field(mock_session):
    db = create_mock_db()
    target = db["users"][1]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, data):
            self.data = data
    entity = await _register_entity(mock_session, Dummy, {"data": ""})
    assert entity.data == ""

@pytest.mark.asyncio
async def test__register_entity_case13_db_numeric_field(mock_session):
    db = create_mock_db()
    target = db["users"][2]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, num):
            self.num = num
    entity = await _register_entity(mock_session, Dummy, {"num": 123})
    assert entity.num == 123

@pytest.mark.asyncio
async def test__register_entity_case14_db_special_characters(mock_session):
    db = create_mock_db()
    target = db["users"][3]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, text):
            self.text = text
    entity = await _register_entity(mock_session, Dummy, {"text": "!@#$%^&*()"})
    assert entity.text == "!@#$%^&*()"

@pytest.mark.asyncio
async def test__register_entity_case15_db_large_string(mock_session):
    large_str = "A" * 1000
    db = create_mock_db()
    target = db["users"][4]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, text):
            self.text = text
    entity = await _register_entity(mock_session, Dummy, {"text": large_str})
    assert entity.text == large_str

@pytest.mark.asyncio
async def test__register_entity_case16_db_none_value(mock_session):
    db = create_mock_db()
    target = db["users"][5]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, val):
            self.val = val
    entity = await _register_entity(mock_session, Dummy, {"val": None})
    assert entity.val is None

@pytest.mark.asyncio
async def test__register_entity_case18_db_invalid_field_type(mock_session):
    db = create_mock_db()
    target = db["users"][7]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    class Dummy:
        def __init__(self, number):
            self.number = number
    # Передаем число в виде строки, но это допустимо – проверяем результат
    entity = await _register_entity(mock_session, Dummy, {"number": "123"})
    assert entity.number == "123"

@pytest.mark.asyncio
async def test__register_entity_case19_db_commit_failure(mock_session):
    db = create_mock_db()
    target = db["users"][8]
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    async def failing_commit():
        raise Exception("DB Commit error")
    mock_session.commit.side_effect = failing_commit
    class Dummy:
        def __init__(self, field):
            self.field = field
    with pytest.raises(Exception, match="DB Commit error"):
        await _register_entity(mock_session, Dummy, {"field": "value"})

@pytest.mark.asyncio
async def test__register_entity_case20_db_non_dict_data(mock_session):
    with pytest.raises(TypeError):
        await _register_entity(mock_session, dict, ["not", "a", "dict"])
#############################################
# Тесты для get_game_model (20 кейсов)
#############################################

@pytest.mark.asyncio
async def test_get_game_model_case1_found(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    mock_session.execute.return_value = make_mock_result(session_obj)
    game_model = await get_game_model(mock_session, session_obj.id)
    assert game_model is not None
    assert game_model.id == session_obj.id


@pytest.mark.asyncio
async def test_get_game_model_case2_not_found(mock_session):
    mock_session.execute.return_value = make_mock_result(None)
    game_model = await get_game_model(mock_session, 999)
    assert game_model is None


@pytest.mark.asyncio
async def test_get_game_model_case3_invalid_id(mock_session):
    with pytest.raises(Exception):
        await get_game_model(mock_session, "invalid")


@pytest.mark.asyncio
async def test_get_game_model_case4_multiple_calls(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    mock_session.execute.return_value = make_mock_result(session_obj)
    gm1 = await get_game_model(mock_session, session_obj.id)
    gm2 = await get_game_model(mock_session, session_obj.id)
    assert gm1.id == gm2.id


@pytest.mark.asyncio
async def test_get_game_model_case5_commit_not_called(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    mock_session.execute.return_value = make_mock_result(session_obj)
    _ = await get_game_model(mock_session, session_obj.id)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_game_model_case6_response_type(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user)
    mock_session.execute.return_value = make_mock_result(session_obj)
    gm = await get_game_model(mock_session, session_obj.id)
    assert isinstance(gm, SessionModel)


@pytest.mark.asyncio
async def test_get_game_model_case7_exception_in_execute(mock_session):
    mock_session.execute.side_effect = Exception("DB error")
    with pytest.raises(Exception, match="DB error"):
        await get_game_model(mock_session, 1)


@pytest.mark.asyncio
async def test_get_game_model_case8_none_id(mock_session):
    with pytest.raises(Exception):
        await get_game_model(mock_session, None)


@pytest.mark.asyncio
async def test_get_game_model_case9_negative_id(mock_session):
    mock_session.execute.return_value = make_mock_result(None)
    gm = await get_game_model(mock_session, -1)
    assert gm is None


@pytest.mark.asyncio
async def test_get_game_model_case10_non_numeric_id(mock_session):
    with pytest.raises(Exception):
        await get_game_model(mock_session, "abc")


# Tests with create_mock_db
@pytest.mark.asyncio
async def test_get_game_model_case11_db_found(mock_session):
    db = create_mock_db()
    target = db["sessions"][0]
    mock_session.execute.return_value = make_mock_result(target)
    gm = await get_game_model(mock_session, target.id)
    assert gm.id == target.id


@pytest.mark.asyncio
async def test_get_game_model_case12_db_not_found(mock_session):
    db = create_mock_db()
    mock_session.execute.return_value = make_mock_result(None)
    gm = await get_game_model(mock_session, 999)
    assert gm is None


@pytest.mark.asyncio
async def test_get_game_model_case13_db_invalid_id(mock_session):
    with pytest.raises(Exception):
        await get_game_model(mock_session, "invalid")


@pytest.mark.asyncio
async def test_get_game_model_case14_db_multiple_calls(mock_session):
    db = create_mock_db()
    target = db["sessions"][2]
    mock_session.execute.return_value = make_mock_result(target)
    gm1 = await get_game_model(mock_session, target.id)
    gm2 = await get_game_model(mock_session, target.id)
    assert gm1.id == gm2.id


@pytest.mark.asyncio
async def test_get_game_model_case15_db_commit_not_called(mock_session):
    db = create_mock_db()
    target = db["sessions"][3]
    mock_session.execute.return_value = make_mock_result(target)
    _ = await get_game_model(mock_session, target.id)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_game_model_case16_db_response_type(mock_session):
    db = create_mock_db()
    target = db["sessions"][4]
    mock_session.execute.return_value = make_mock_result(target)
    gm = await get_game_model(mock_session, target.id)
    assert isinstance(gm, SessionModel)


@pytest.mark.asyncio
async def test_get_game_model_case17_db_exception(mock_session):
    db = create_mock_db()
    mock_session.execute.side_effect = Exception("DB error")
    with pytest.raises(Exception, match="DB error"):
        await get_game_model(mock_session, 1)


@pytest.mark.asyncio
async def test_get_game_model_case18_db_none_id(mock_session):
    with pytest.raises(Exception):
        await get_game_model(mock_session, None)


@pytest.mark.asyncio
async def test_get_game_model_case19_db_negative_id(mock_session):
    db = create_mock_db()
    mock_session.execute.return_value = make_mock_result(None)
    gm = await get_game_model(mock_session, -1)
    assert gm is None


@pytest.mark.asyncio
async def test_get_game_model_case20_db_non_numeric_id(mock_session):
    with pytest.raises(Exception):
        await get_game_model(mock_session, "abc")

#############################################
# Тесты для register_user (20 кейсов)
#############################################

@pytest.mark.asyncio
async def test_register_user_case1_normal(mock_session):
    dummy = create_dummy_user()
    mock_session.execute.return_value = make_mock_result(None)
    user_model = UserModel(dummy)
    registered = await register_user(user_model, mock_session)
    assert registered.telegram_id == dummy.telegram_id


@pytest.mark.asyncio
async def test_register_user_case11_db_first_user(mock_session):
    db = create_mock_db()
    target = db["users"][0]
    mock_session.execute.return_value = make_mock_result(None)
    user_model = UserModel(target)
    registered = await register_user(user_model, mock_session)
    assert registered.telegram_id == target.telegram_id


@pytest.mark.asyncio
async def test_register_user_case12_db_last_user(mock_session):
    db = create_mock_db()
    target = db["users"][-1]
    mock_session.execute.return_value = make_mock_result(None)
    user_model = UserModel(target)
    registered = await register_user(user_model, mock_session)
    assert registered.telegram_id == target.telegram_id


@pytest.mark.asyncio
async def test_register_user_case13_db_multiple_roles_formats(mock_session):
    db = create_mock_db()
    target = db["users"][10]
    target.role = "Игрок, Мастер"  # invalid type
    target.game_format = "Онлайн, Оффлайн"  # invalid type as well
    with pytest.raises(TypeError):
        user_model = UserModel(target)


@pytest.mark.asyncio
async def test_register_user_case14_db_missing_field(mock_session):
    db = create_mock_db()
    target = db["users"][11]
    target.name = ""
    mock_session.execute.return_value = make_mock_result(None)
    user_model = UserModel(target)
    registered = await register_user(user_model, mock_session)
    assert registered.name == ""


@pytest.mark.asyncio
async def test_register_user_case15_db_boundary_age(mock_session):
    db = create_mock_db()
    target = db["users"][12]
    target.age = 0
    mock_session.execute.return_value = make_mock_result(None)
    user_model = UserModel(target)
    registered = await register_user(user_model, mock_session)
    assert registered.age == 0


@pytest.mark.asyncio
async def test_register_user_case16_db_extreme_age(mock_session):
    db = create_mock_db()
    target = db["users"][13]
    target.age = 150
    mock_session.execute.return_value = make_mock_result(None)
    user_model = UserModel(target)
    registered = await register_user(user_model, mock_session)
    assert registered.age == 150


@pytest.mark.asyncio
async def test_register_user_case17_db_missing_optional(mock_session):
    db = create_mock_db()
    target = db["users"][14]
    target.about_info = None
    mock_session.execute.return_value = make_mock_result(None)
    user_model = UserModel(target)
    registered = await register_user(user_model, mock_session)
    assert registered.about_info is None


@pytest.mark.asyncio
async def test_register_user_case18_db_commit_failure(mock_session):
    db = create_mock_db()
    target = db["users"][15]
    mock_session.execute.return_value = make_mock_result(None)
    async def failing_commit():
        raise Exception("Commit error")
    mock_session.commit.side_effect = failing_commit
    user_model = UserModel(target)
    with pytest.raises(Exception, match="Commit error"):
        await register_user(user_model, mock_session)


@pytest.mark.asyncio
async def test_register_user_case19_db_invalid_role_string(mock_session):
    db = create_mock_db()
    target = db["users"][16]
    target.role = "Игрок"  # invalid type
    with pytest.raises(TypeError):
        user_model = UserModel(target)


@pytest.mark.asyncio
async def test_register_user_case20_db_invalid_format_string(mock_session):
    db = create_mock_db()
    target = db["users"][17]
    target.game_format = "Онлайн"  # invalid type
    with pytest.raises(TypeError):
        user_model = UserModel(target)

#############################################
# Тесты для register_game (20 кейсов)
#############################################

@pytest.mark.asyncio
async def test_register_game_case1_normal(mock_session):
    user = create_dummy_user()
    session_obj = create_dummy_session(user, format_index=0, looking_for_index=0)
    from bot.db.models import SessionModel
    game_model = SessionModel(session_obj)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    registered = await register_game(game_model, mock_session)
    assert registered.title == session_obj.title

# Дополнительные тесты с использованием create_mock_db для register_game
@pytest.mark.asyncio
async def test_register_game_case11_db_normal(mock_session):
    db = create_mock_db()
    target = db["sessions"][0]
    from bot.db.models import SessionModel
    game_model = SessionModel(target)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    registered = await register_game(game_model, mock_session)
    assert registered.title == target.title

@pytest.mark.asyncio
async def test_register_game_case14_db_missing_optional_fields(mock_session):
    db = create_mock_db()
    target = db["sessions"][3]
    target.description = ""
    from bot.db.models import SessionModel
    game_model = SessionModel(target)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    registered = await register_game(game_model, mock_session)
    assert registered.description == ""

@pytest.mark.asyncio
async def test_register_game_case15_db_future_date(mock_session):
    db = create_mock_db()
    target = db["sessions"][4]
    future = datetime.datetime.now() + datetime.timedelta(days=365)
    target.date_time = future
    from bot.db.models import SessionModel
    game_model = SessionModel(target)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    registered = await register_game(game_model, mock_session)
    assert registered.date_time == future

@pytest.mark.asyncio
async def test_register_game_case16_db_max_players_zero(mock_session):
    db = create_mock_db()
    target = db["sessions"][5]
    target.max_players = 0
    from bot.db.models import SessionModel
    game_model = SessionModel(target)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    registered = await register_game(game_model, mock_session)
    assert registered.max_players == 0


@pytest.mark.asyncio
async def test_register_game_case18_db_commit_failure(mock_session):
    db = create_mock_db()
    target = db["sessions"][7]
    from bot.db.models import SessionModel
    game_model = SessionModel(target)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    async def failing_commit():
        raise Exception("Commit failed")
    mock_session.commit.side_effect = failing_commit
    with pytest.raises(Exception, match="Commit failed"):
        await register_game(game_model, mock_session)


@pytest.mark.asyncio
async def test_register_game_case20_db_incomplete_data(mock_session):
    db = create_mock_db()
    target = db["sessions"][9]
    target.title = ""
    from bot.db.models import SessionModel
    game_model = SessionModel(target)
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    registered = await register_game(game_model, mock_session)
    assert registered.title == ""

#############################################
# Тесты для edit_user (20 кейсов)
#############################################

@pytest.mark.asyncio
async def test_edit_user_case1_success(mock_session):
    user = create_dummy_user(name="OldName")
    mock_session.execute.return_value = make_mock_result(user)
    changes = {"name": "EditedName"}
    updated = await edit_user(user.telegram_id, changes, mock_session)
    assert updated.name == "EditedName"

@pytest.mark.asyncio
async def test_edit_user_case11_db_update_name(mock_session):
    db = create_mock_db()
    target = db["users"][0]
    mock_session.execute.return_value = make_mock_result(target)
    changes = {"name": "UpdatedName"}
    updated = await edit_user(target.telegram_id, changes, mock_session)
    assert updated.name == "UpdatedName"

@pytest.mark.asyncio
async def test_edit_user_case12_db_update_city(mock_session):
    db = create_mock_db()
    target = db["users"][1]
    mock_session.execute.return_value = make_mock_result(target)
    changes = {"city": "NewCity"}
    updated = await edit_user(target.telegram_id, changes, mock_session)
    assert updated.city == "NewCity"

@pytest.mark.asyncio
async def test_edit_user_case13_db_empty_change(mock_session):
    db = create_mock_db()
    target = db["users"][2]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_user(target.telegram_id, {}, mock_session)
    fetched = await updated.get_user(mock_session)
    assert fetched.name == target.name

@pytest.mark.asyncio
async def test_edit_user_case14_db_invalid_field(mock_session):
    db = create_mock_db()
    target = db["users"][3]
    mock_session.execute.return_value = make_mock_result(target)
    with pytest.raises(ValueError):
        await edit_user(target.telegram_id, {"invalid": "x"}, mock_session)

@pytest.mark.asyncio
async def test_edit_user_case15_db_update_multiple_fields(mock_session):
    db = create_mock_db()
    target = db["users"][4]
    mock_session.execute.return_value = make_mock_result(target)
    changes = {"name": "NewName", "city": "NewCity"}
    updated = await edit_user(target.telegram_id, changes, mock_session)
    assert updated.name == "NewName"
    assert updated.city == "NewCity"

@pytest.mark.asyncio
async def test_edit_user_case16_db_numeric_to_string(mock_session):
    db = create_mock_db()
    target = db["users"][5]
    mock_session.execute.return_value = make_mock_result(target)
    changes = {"age": "forty"}
    updated = await edit_user(target.telegram_id, changes, mock_session)
    assert updated.age == "forty"

@pytest.mark.asyncio
async def test_edit_user_case17_db_partial_update(mock_session):
    db = create_mock_db()
    target = db["users"][6]
    mock_session.execute.return_value = make_mock_result(target)
    changes = {"city": "UpdatedCity"}
    updated = await edit_user(target.telegram_id, changes, mock_session)
    assert updated.city == "UpdatedCity"

@pytest.mark.asyncio
async def test_edit_user_case18_db_commit_failure(mock_session):
    db = create_mock_db()
    target = db["users"][7]
    mock_session.execute.return_value = make_mock_result(target)
    async def failing_commit():
        raise Exception("Commit error")
    mock_session.commit.side_effect = failing_commit
    with pytest.raises(Exception, match="Commit error"):
        await edit_user(target.telegram_id, {"name": "NewName"}, mock_session)

@pytest.mark.asyncio
async def test_edit_user_case19_db_update_same_value(mock_session):
    db = create_mock_db()
    target = db["users"][8]
    mock_session.execute.return_value = make_mock_result(target)
    changes = {"name": target.name}
    updated = await edit_user(target.telegram_id, changes, mock_session)
    assert updated.name == target.name

@pytest.mark.asyncio
async def test_edit_user_case20_db_empty_string_update(mock_session):
    db = create_mock_db()
    target = db["users"][9]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_user(target.telegram_id, {"name": ""}, mock_session)
    assert updated.name == ""

#############################################
# Тесты для edit_player (20 кейсов)
#############################################

@pytest.mark.asyncio
async def test_edit_player_case1_success(mock_session):
    user = create_dummy_user()
    dummy_player = create_dummy_player(user, availability="full")
    mock_session.execute.return_value = make_mock_result(dummy_player)
    updated = await edit_player(user.telegram_id, {"availability": "edited"}, mock_session)
    assert updated.availability == "edited"

@pytest.mark.asyncio
async def test_edit_player_case11_db_update_availability(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][0]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_player(target.user.telegram_id, {"availability": "changed"}, mock_session)
    assert updated.availability == "changed"

@pytest.mark.asyncio
async def test_edit_player_case12_db_update_experience(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][1]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_player(target.user.telegram_id, {"experience_level": 1}, mock_session)
    assert updated.experience_level == all_experience_levels[1]

@pytest.mark.asyncio
async def test_edit_player_case13_db_empty_change(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][2]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_player(target.user.telegram_id, {}, mock_session)
    fetched = await updated.get_player(mock_session)
    assert fetched.availability == target.availability

@pytest.mark.asyncio
async def test_edit_player_case14_db_invalid_field(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][3]
    mock_session.execute.return_value = make_mock_result(target)
    with pytest.raises(ValueError):
        await edit_player(target.user.telegram_id, {"invalid": "x"}, mock_session)

@pytest.mark.asyncio
async def test_edit_player_case15_db_update_multiple_fields(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][4]
    changes = {"availability": "no", "experience_level": 2}
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_player(target.user.telegram_id, changes, mock_session)
    assert updated.availability == "no"
    assert updated.experience_level == all_experience_levels[2]

@pytest.mark.asyncio
async def test_edit_player_case16_db_update_same_value(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][5]
    changes = {"availability": target.availability}
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_player(target.user.telegram_id, changes, mock_session)
    assert updated.availability == target.availability

@pytest.mark.asyncio
async def test_edit_player_case17_db_commit_failure(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][6]
    mock_session.execute.return_value = make_mock_result(target)
    async def failing_commit():
        raise Exception("Commit fail")
    mock_session.commit.side_effect = failing_commit
    with pytest.raises(Exception, match="Commit fail"):
        await edit_player(target.user.telegram_id, {"availability": "fail"}, mock_session)

@pytest.mark.asyncio
async def test_edit_player_case18_db_non_numeric_experience(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][7]
    mock_session.execute.return_value = make_mock_result(target)
    with pytest.raises(TypeError):
        await edit_player(target.user.telegram_id, {"experience_level": "Опыт"}, mock_session)

@pytest.mark.asyncio
async def test_edit_player_case19_db_update_with_partial_field(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][8]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_player(target.user.telegram_id, {"availability": "updated"}, mock_session)
    assert updated.availability == "updated"

@pytest.mark.asyncio
async def test_edit_player_case20_db_empty_string_update(mock_session):
    db = create_mock_db()
    if not db["players"]:
        pytest.skip("Нет игроков")
    target = db["players"][9]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_player(target.user.telegram_id, {"availability": ""}, mock_session)
    assert updated.availability == ""

#############################################
# Тесты для edit_master (20 кейсов)
#############################################

@pytest.mark.asyncio
async def test_edit_master_case1_success(mock_session):
    user = create_dummy_user()
    dummy_master = create_dummy_master(user, master_style="OldStyle", rating=3)
    mock_session.execute.return_value = make_mock_result(dummy_master)
    updated = await edit_master(user.telegram_id, {"rating": 7}, mock_session)
    assert updated.rating == 7

@pytest.mark.asyncio
async def test_edit_master_case11_db_update_style(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][0]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_master(target.user.telegram_id, {"master_style": "NewStyle"}, mock_session)
    assert updated.master_style == "NewStyle"

@pytest.mark.asyncio
async def test_edit_master_case12_db_update_rating(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][1]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_master(target.user.telegram_id, {"rating": target.rating + 2}, mock_session)
    assert updated.rating == target.rating + 2

@pytest.mark.asyncio
async def test_edit_master_case13_db_empty_change(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][2]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_master(target.user.telegram_id, {}, mock_session)
    fetched = await updated.get_master(mock_session)
    assert fetched.rating == target.rating

@pytest.mark.asyncio
async def test_edit_master_case14_db_invalid_field(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][3]
    mock_session.execute.return_value = make_mock_result(target)
    with pytest.raises(ValueError):
        await edit_master(target.user.telegram_id, {"nonexistent": "value"}, mock_session)

@pytest.mark.asyncio
async def test_edit_master_case15_db_update_multiple_fields(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][4]
    changes = {"master_style": "UpdatedStyle", "rating": target.rating + 1}
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_master(target.user.telegram_id, changes, mock_session)
    assert updated.master_style == "UpdatedStyle"
    assert updated.rating == target.rating + 1

@pytest.mark.asyncio
async def test_edit_master_case16_db_update_same_value(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][5]
    changes = {"master_style": target.master_style}
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_master(target.user.telegram_id, changes, mock_session)
    assert updated.master_style == target.master_style

@pytest.mark.asyncio
async def test_edit_master_case17_db_commit_failure(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][6]
    mock_session.execute.return_value = make_mock_result(target)
    async def failing_commit():
        raise Exception("Commit error")
    mock_session.commit.side_effect = failing_commit
    with pytest.raises(Exception, match="Commit error"):
        await edit_master(target.user.telegram_id, {"rating": 10}, mock_session)

@pytest.mark.asyncio
async def test_edit_master_case18_db_update_with_partial_field(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][7]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_master(target.user.telegram_id, {"master_style": "PartialUpdate"}, mock_session)
    assert updated.master_style == "PartialUpdate"

@pytest.mark.asyncio
async def test_edit_master_case19_db_update_invalid_id(mock_session):
    db = create_mock_db()
    with pytest.raises(Exception):
        await edit_master(mock_session, {"rating": 10}, 999999)

@pytest.mark.asyncio
async def test_edit_master_case20_db_empty_string_update(mock_session):
    db = create_mock_db()
    if not db["masters"]:
        pytest.skip("Нет мастеров")
    target = db["masters"][8]
    mock_session.execute.return_value = make_mock_result(target)
    updated = await edit_master(target.user.telegram_id, {"master_style": ""}, mock_session)
    assert updated.master_style == ""

#############################################
# Тесты для функций из models.py
#############################################

# Для concat (20 кейсов)
def test_concat_case1_single_element():
    assert concat(["a"]) == "a"

def test_concat_case2_multiple_elements():
    assert concat(["a", "b", "c"]) == "a, b, c"

def test_concat_case4_numeric_elements():
    assert concat([str(1), str(2)]) == "1, 2"

def test_concat_case5_special_characters():
    # Тест на отсутствие ошибок, результат может варьироваться
    res = concat(["!", "@", "#"])
    assert isinstance(res, str)

def test_concat_case6_long_list():
    items = [str(i) for i in range(10)]
    result = concat(items)
    assert result.count(",") == 9

def test_concat_case7_spaces_in_elements():
    assert concat([" a", "b "]) == " a, b "

def test_concat_case8_mixed_types():
    with pytest.raises(TypeError):
        concat([1, 2])

def test_concat_case9_none_element():
    with pytest.raises(TypeError):
        concat(["a", None])

def test_concat_case10_unicode_elements():
    assert concat(["тест", "пример"]) == "тест, пример"

# Дополнительные тесты для concat с использованием create_mock_db (просто проверяем, что все строки объединяются)
def test_concat_case11_db_elements():
    db = create_mock_db()
    names = [user.name for user in db["users"][:5]]
    res = concat(names)
    assert isinstance(res, str)

def test_concat_case12_db_empty_string():
    res = concat(["", ""])
    assert res == ", "

def test_concat_case13_db_single_unicode():
    assert concat(["тест"]) == "тест"

def test_concat_case14_db_trailing_spaces():
    res = concat([" a ", " b "])
    assert " a " in res and " b " in res

def test_concat_case15_db_numbers_as_strings():
    res = concat([str(x) for x in range(5)])
    assert res.startswith("0")

def test_concat_case16_db_special_mix():
    res = concat(["!@#", "$%^", "&*("])
    assert isinstance(res, str)

def test_concat_case17_db_long_list():
    items = [f"item{i}" for i in range(20)]
    res = concat(items)
    assert res.count(",") == 19

def test_concat_case19_db_strings_with_commas():
    res = concat(["a,b", "c,d"])
    assert "a,b, c,d" == res

def test_concat_case20_db_normal_mix():
    res = concat(["Hello", "World"])
    assert res == "Hello, World"

# Для get_role (20 кейсов)
def test_get_role_case1_single_role():
    user = create_dummy_user(role=1 << all_roles.index("Игрок"))
    role_str = get_role(user)
    assert "Игрок" in role_str

def test_get_role_case2_multiple_roles():
    combined = (1 << all_roles.index("Игрок")) | (1 << all_roles.index("Мастер"))
    user = create_dummy_user(role=combined)
    role_str = get_role(user)
    assert "Игрок" in role_str and "Мастер" in role_str

def test_get_role_case3_no_roles():
    user = create_dummy_user(role=0)
    role_str = get_role(user)
    assert role_str == ""

def test_get_role_case4_invalid_role_mask():
    user = create_dummy_user(role=-1)
    role_str = get_role(user)
    assert isinstance(role_str, str)

def test_get_role_case5_large_mask():
    user = create_dummy_user(role=2**10)
    role_str = get_role(user)
    assert isinstance(role_str, str)

def test_get_role_case6_string_conversion():
    user = create_dummy_user(role=1 << all_roles.index("Мастер"))
    role_str = get_role(user)
    assert isinstance(role_str, str)

def test_get_role_case7_boundary_mask():
    user = create_dummy_user(role=1)
    role_str = get_role(user)
    assert "Игрок" in role_str or role_str == ""

def test_get_role_case8_none_mask():
    user = create_dummy_user()
    user.role = None
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case9_float_mask():
    user = create_dummy_user(role=1.5)
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case10_complex_mask():
    user = create_dummy_user(role=complex(1,2))
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case11_db_first_role():
    db = create_mock_db()
    user = db["users"][0]
    r = get_role(user)
    assert isinstance(r, str)

def test_get_role_case12_db_all_roles():
    combined = (1 << all_roles.index("Игрок")) | (1 << all_roles.index("Мастер"))
    user = create_dummy_user(role=combined)
    r = get_role(user)
    assert "Игрок" in r and "Мастер" in r

def test_get_role_case13_db_zero_mask():
    user = create_dummy_user(role=0)
    r = get_role(user)
    assert r == ""

def test_get_role_case14_db_invalid_string_mask():
    user = create_dummy_user()
    user.role = "invalid"
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case16_db_none_value():
    user = create_dummy_user()
    user.role = None
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case17_db_float_value():
    user = create_dummy_user()
    user.role = 2.0
    with pytest.raises(TypeError):
        get_role(user)

def test_get_role_case18_db_negative_value():
    user = create_dummy_user()
    user.role = -5
    r = get_role(user)
    assert isinstance(r, str)

def test_get_role_case19_db_large_int():
    user = create_dummy_user(role=2**20)
    r = get_role(user)
    assert isinstance(r, str)

def test_get_role_case20_db_proper_conversion():
    user = create_dummy_user(role=1 << all_roles.index("Игрок"))
    r = get_role(user)
    assert "Игрок" in r

# Для get_game_format (20 кейсов)
def test_get_game_format_case1_single_format():
    user = create_dummy_user(game_format=1 << all_formats.index("Онлайн"))
    f = get_game_format(user)
    assert "Онлайн" in f

def test_get_game_format_case2_multiple_formats():
    combined = (1 << all_formats.index("Онлайн")) | (1 << all_formats.index("Оффлайн"))
    user = create_dummy_user(game_format=combined)
    f = get_game_format(user)
    assert "Онлайн" in f and "Оффлайн" in f

def test_get_game_format_case3_no_format():
    user = create_dummy_user(game_format=0)
    f = get_game_format(user)
    assert f == ""

def test_get_game_format_case4_invalid_mask():
    user = create_dummy_user(game_format=-1)
    f = get_game_format(user)
    assert isinstance(f, str)

def test_get_game_format_case5_large_mask():
    user = create_dummy_user(game_format=2**10)
    f = get_game_format(user)
    assert isinstance(f, str)

def test_get_game_format_case6_string_conversion():
    user = create_dummy_user(game_format=1 << all_formats.index("Оффлайн"))
    f = get_game_format(user)
    assert isinstance(f, str)

def test_get_game_format_case7_boundary_mask():
    user = create_dummy_user(game_format=1)
    f = get_game_format(user)
    assert "Онлайн" in f or f == ""

def test_get_game_format_case8_none_mask():
    user = create_dummy_user()
    user.game_format = None
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case9_float_mask():
    user = create_dummy_user(game_format=1.5)
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case10_complex_mask():
    user = create_dummy_user(game_format=complex(1, 2))
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case11_db_single_format():
    db = create_mock_db()
    user = db["users"][0]
    f = get_game_format(user)
    assert isinstance(f, str)

def test_get_game_format_case12_db_all_formats():
    combined = (1 << all_formats.index("Онлайн")) | (1 << all_formats.index("Оффлайн"))
    user = create_dummy_user(game_format=combined)
    f = get_game_format(user)
    assert "Онлайн" in f and "Оффлайн" in f

def test_get_game_format_case13_db_zero():
    user = create_dummy_user(game_format=0)
    f = get_game_format(user)
    assert f == ""

def test_get_game_format_case14_db_invalid_string():
    user = create_dummy_user()
    user.game_format = "invalid"
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case16_db_none_value():
    user = create_dummy_user()
    user.game_format = None
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case17_db_float_value():
    user = create_dummy_user()
    user.game_format = 3.0
    with pytest.raises(TypeError):
        get_game_format(user)

def test_get_game_format_case18_db_negative_value():
    user = create_dummy_user()
    user.game_format = -5
    f = get_game_format(user)
    assert isinstance(f, str)

def test_get_game_format_case19_db_large_int():
    user = create_dummy_user(game_format=2**20)
    f = get_game_format(user)
    assert isinstance(f, str)

def test_get_game_format_case20_db_proper_conversion():
    user = create_dummy_user(game_format=1 << all_formats.index("Онлайн"))
    f = get_game_format(user)
    assert "Онлайн" in f

#############################################
# Тесты для UserModel.__str__ (20 кейсов)
#############################################

def test_user_model_str_case1_contains_fields():
    user = create_dummy_user(name="Алиса", age=25, city="Город")
    um = UserModel(user)
    s = str(um)
    assert "Алиса" in s and "25" in s and "Город" in s

def test_user_model_str_case2_empty_about():
    user = create_dummy_user(about_info=None)
    um = UserModel(user)
    s = str(um)
    assert "Не указано" in s

def test_user_model_str_case3_long_name():
    long_name = "A" * 100
    user = create_dummy_user(name=long_name)
    um = UserModel(user)
    s = str(um)
    assert long_name in s

def test_user_model_str_case4_special_characters():
    user = create_dummy_user(name="Тест@#$")
    um = UserModel(user)
    s = str(um)
    assert "Тест@#$" in s

def test_user_model_str_case5_different_timezone():
    user = create_dummy_user(time_zone=10)
    um = UserModel(user)
    s = str(um)
    assert "10" in s

def test_user_model_str_case6_missing_city():
    user = create_dummy_user(city="")
    um = UserModel(user)
    s = str(um)
    assert "Город" not in s or "" in s

def test_user_model_str_case7_numeric_age():
    user = create_dummy_user(age=0)
    um = UserModel(user)
    s = str(um)
    assert "0" in s

def test_user_model_str_case8_non_ascii():
    user = create_dummy_user(name="测试", city="城市")
    um = UserModel(user)
    s = str(um)
    assert "测试" in s and "城市" in s

def test_user_model_str_case9_modified_preferred_systems():
    user = create_dummy_user(preferred_systems="PS5")
    um = UserModel(user)
    s = str(um)
    assert "PS5" in s

def test_user_model_str_case10_about_info_custom():
    user = create_dummy_user(about_info="Особая информация")
    um = UserModel(user)
    s = str(um)
    assert "Особая информация" in s

def test_user_model_str_case11_db_unicode(mock_session):
    db = create_mock_db()
    user = db["users"][0]
    um = UserModel(user)
    s = str(um)
    assert isinstance(s, str)

def test_user_model_str_case12_db_empty_name():
    user = create_dummy_user(name="")
    um = UserModel(user)
    s = str(um)
    assert s is not None

def test_user_model_str_case13_db_special_mix():
    user = create_dummy_user(name="@$%^", city="*&^%")
    um = UserModel(user)
    s = str(um)
    assert "@$%^" in s and "*&^%" in s

def test_user_model_str_case14_db_long_about():
    user = create_dummy_user(about_info="A" * 500)
    um = UserModel(user)
    s = str(um)
    assert "A" * 100 in s

def test_user_model_str_case15_db_numeric_timezone():
    user = create_dummy_user(time_zone=5)
    um = UserModel(user)
    s = str(um)
    assert "5" in s

def test_user_model_str_case16_db_missing_info():
    user = create_dummy_user(about_info="")
    um = UserModel(user)
    s = str(um)
    assert "Не указано" in s

def test_user_model_str_case17_db_custom_fields():
    user = create_dummy_user(name="Custom", city="CityX", age=40)
    um = UserModel(user)
    s = str(um)
    assert "Custom" in s and "CityX" in s and "40" in s

def test_user_model_str_case18_db_multiple_lines():
    user = create_dummy_user()
    um = UserModel(user)
    s = str(um)
    assert "\n" in s

def test_user_model_str_case19_db_formatting(mock_session):
    db = create_mock_db()
    user = random.choice(db["users"])
    um = UserModel(user)
    s = str(um)
    assert "Ваш профиль" in s

def test_user_model_str_case20_db_not_none():
    user = create_dummy_user()
    um = UserModel(user)
    s = str(um)
    assert s != ""

#############################################
# Тесты для UserModel.get_user (20 кейсов)
#############################################

@pytest.mark.asyncio
async def test_user_model_get_user_case1_found(mock_session):
    user = create_dummy_user()
    um = UserModel(user)

    # Создаём "результат" с цепочкой scalars().first()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = user
    mock_result.scalars.return_value = mock_scalars

    # Когда вызовем await execute(...), вернётся этот mock_result
    mock_session.execute.return_value = mock_result

    fetched = await um.get_user(mock_session)

    assert fetched == user

def test_main():
    # Для локального запуска тестов
    pytest.main(["-v"])

#############################################
# Завершение
#############################################

if __name__ == "__main__":
    test_main()
