from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.base import User, Player, Master, Session

all_roles = ['Игрок', 'Мастер']
all_formats = ['Онлайн', 'Оффлайн']
all_experience_levels = ['Опыт1', 'Опыт2', 'Опыт3']


def concat(options: list):
    if not options:
        return ""
    for o in options:
        if o is None:
            raise TypeError("None is not allowed in options")
    option = options[0]
    for o in options[1:]:
        option += f', {o}'
    return option


def get_role(user: User):
    roles = []
    for i in range(len(all_roles)):
        if user.role & 2 ** i:
            roles.append(all_roles[i])
    return concat(roles)


def get_game_format(user: User):
    formats = []
    for i in range(len(all_formats)):
        if user.game_format & 2 ** i:
            formats.append(all_formats[i])
    return concat(formats)


class UserModel:
    def __init__(self, user: User):
        self.id = user.id
        self.telegram_id = user.telegram_id
        self.name = user.name
        self.age = user.age
        self.city = user.city
        self.time_zone = user.time_zone
        self.role = get_role(user)
        self.game_format = get_game_format(user)
        self.preferred_systems = user.preferred_systems
        self.about_info = user.about_info
        self.created_at = user.created_at
        self._player_profile = user.player_profile
        self._master_profile = user.master_profile
        self._sessions = user.sessions

    @property
    def player_profile(self) -> Optional['PlayerModel']:
        return PlayerModel(self._player_profile) if self._player_profile else None

    @property
    def master_profile(self) -> Optional['MasterModel']:
        return MasterModel(self._master_profile) if self._master_profile else None

    async def get_user(self, session: AsyncSession) -> User:
        user = await session.execute(select(User).where(User.telegram_id == self.telegram_id))
        return user.scalars().first()

    @property
    def sessions(self) -> List['SessionModel']:
        return [SessionModel(s) for s in self._sessions]

    def __str__(self):
        return (f"<b>Ваш профиль</b>:\n"
                f"Имя: <b>{self.name}</b>\n"
                f"Возраст: <b>{self.age}</b>\n"
                f"Город: <b>{self.city}</b>\n"
                f"Часовой пояс: <b>{self.time_zone}</b>\n"
                f"Роль: <b>{self.role}</b>\n"
                f"Формат игры: <b>{self.game_format}</b>\n"
                f"Предпочитаемые системы: <b>{self.preferred_systems}</b>\n"
                f"О себе: <b>{self.about_info or 'Не указано'}</b>\n")


class PlayerModel:
    def __init__(self, player: Player):
        self.id = player.id
        self.experience_level = all_experience_levels[player.experience_level]
        self.availability = player.availability

        self._user = player.user
        self._sessions = player.sessions

    @property
    def user(self) -> UserModel:
        return UserModel(self._user)

    @property
    def sessions(self) -> List['SessionModel']:
        return [SessionModel(s) for s in self._sessions]

    async def get_player(self, session):
        player = await session.execute(select(Player).where(User.telegram_id == self.user.telegram_id))
        return player.scalars().first()


class MasterModel:
    def __init__(self, master: Master):
        self.id = master.id
        self.master_style = master.master_style
        self.rating = master.rating

        # Связи
        self._user = master.user
        self._sessions = master.sessions

    async def get_master(self, session):
        master = await session.execute(select(Master).where(User.telegram_id == self.user.telegram_id))
        return master.scalars().first()

    @property
    def user(self) -> UserModel:
        return UserModel(self._user)

    @property
    def sessions(self) -> List['SessionModel']:
        return [SessionModel(s) for s in self._sessions]


class SessionModel:
    def __init__(self, session: Session):
        # Основные поля
        self.id = session.id
        self.title = session.title
        self.description = session.description
        self.game_system = session.game_system
        self.date_time = session.date_time
        self.format = all_formats[session.format]
        self.status = session.status
        self.max_players = session.max_players
        self.looking_for = all_roles[session.looking_for]

        # Связи
        self._creator = session.creator
        self._players = session.players

    @property
    def creator(self) -> UserModel:
        return UserModel(self._creator)

    async def get_game(self, session: AsyncSession) -> Session:
        game = await session.execute(select(Session).where(Session.id == self.id))
        return game.scalars().first()

    @property
    def players(self) -> List[Union[PlayerModel, UserModel]]:
        return [PlayerModel(p) for p in self._players]
