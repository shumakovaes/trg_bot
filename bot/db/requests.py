from typing import Optional, Type, Any, Dict
from aiogram import Router
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.db.base import User, Player, Master, Session
from bot.db.models import UserModel, SessionModel, PlayerModel, MasterModel, all_formats, all_roles, \
    all_experience_levels

router = Router()


async def _get_entity(
        session: AsyncSession,
        model: Type[Any],
        filters: Dict[str, Any],
        join_model: Optional[Type[Any]] = None
) -> Optional[Any]:
    stmt: Select = select(model)

    if join_model:
        stmt = stmt.join(join_model)

    for key, value in filters.items():
        if join_model and hasattr(join_model, key):
            stmt = stmt.where(getattr(join_model, key) == value)
        else:
            stmt = stmt.where(getattr(model, key) == value)

    result = await session.execute(stmt)
    return result.scalars().first()


async def _register_entity(
        session: AsyncSession,
        model: Type[Any],
        data: Dict[str, Any],
        check_filters: Optional[Dict[str, Any]] = None
) -> Any:
    if check_filters:
        existing = await _get_entity(session, model, check_filters)
        if existing:
            entity_name = model.__name__.lower()
            raise ValueError(f"{entity_name.capitalize()} already exists")

    entity = model(**data)
    session.add(entity)
    await session.commit()
    await session.refresh(entity)
    return entity


async def _edit_entity(
        session: AsyncSession,
        model: Type[Any],
        entity_id: int,
        changes: Dict[str, Any],
        allowed_fields: set
) -> Optional[Any]:
    if not set(changes.keys()).issubset(allowed_fields):
        raise ValueError(f"Invalid fields for {model.__name__} update")

    entity = await session.get(model, entity_id)
    if not entity:
        return None

    for key, value in changes.items():
        setattr(entity, key, value)

    await session.commit()
    await session.refresh(entity)
    return entity


async def get_user_model(session: AsyncSession, tg_id: int) -> Optional[UserModel]:
    user = await _get_entity(session, User, {"telegram_id": tg_id})
    return UserModel(user) if user else None


async def get_player_model(session: AsyncSession, tg_id: int) -> Optional[PlayerModel]:
    player = await _get_entity(session, Player, {"telegram_id": tg_id}, join_model=User)
    return PlayerModel(player) if player else None


async def get_master_model(session: AsyncSession, tg_id: int) -> Optional[MasterModel]:
    master = await _get_entity(session, Master, {"telegram_id": tg_id}, join_model=User)
    return MasterModel(master) if master else None


async def get_game_model(session: AsyncSession, game_id: int) -> Optional[SessionModel]:
    game = await _get_entity(session, Session, {"id": game_id})
    return SessionModel(game) if game else None


async def register_user(user_model: UserModel, session: AsyncSession) -> UserModel:
    role_mask = sum(1 << all_roles.index(r) for r in user_model.role.split(', '))
    format_mask = sum(1 << all_formats.index(f) for f in user_model.game_format.split(', '))

    user_data = {
        "telegram_id": user_model.telegram_id,
        "name": user_model.name,
        "age": user_model.age,
        "city": user_model.city,
        "time_zone": user_model.time_zone,
        "role": role_mask,
        "game_format": format_mask,
        "preferred_systems": user_model.preferred_systems,
        "about_info": user_model.about_info
    }

    user = await _register_entity(
        session,
        User,
        user_data,
        check_filters={"telegram_id": user_model.telegram_id}
    )
    return UserModel(user)


async def register_player(player_model: PlayerModel, session: AsyncSession) -> PlayerModel:
    user = await get_user_model(session, player_model.user.telegram_id)
    if not user:
        raise ValueError("User not found")

    player_data = {
        "id": user.id,
        "experience_level": all_experience_levels.index(player_model.experience_level),
        "availability": player_model.availability
    }

    player = await _register_entity(
        session,
        Player,
        player_data,
        check_filters={"id": user.id}
    )
    return PlayerModel(player)


async def register_master(master_model: MasterModel, session: AsyncSession) -> MasterModel:
    user = await get_user_model(session, master_model.user.telegram_id)
    if not user:
        raise ValueError("User not found")

    master_data = {
        "id": user.id,
        "master_style": master_model.master_style,
        "rating": master_model.rating
    }

    master = await _register_entity(
        session,
        Master,
        master_data,
        check_filters={"id": user.id}
    )
    return MasterModel(master)


async def register_game(game_model: SessionModel, session: AsyncSession) -> SessionModel:
    if game_model.format not in all_formats:
        raise ValueError(f"Invalid format: {game_model.format}")
    if game_model.looking_for not in all_roles:
        raise ValueError(f"Invalid role: {game_model.looking_for}")

    game_data = {
        "title": game_model.title,
        "description": game_model.description,
        "game_system": game_model.game_system,
        "date_time": game_model.date_time,
        "format": all_formats.index(game_model.format),
        "status": game_model.status,
        "max_players": game_model.max_players,
        "looking_for": all_roles.index(game_model.looking_for),
        "creator_id": game_model.creator.id
    }

    game = await _register_entity(session, Session, game_data)
    return SessionModel(game)


async def edit_user(tg_id: int, changes: dict, session: AsyncSession) -> Optional[UserModel]:
    allowed_fields = {
        "name", "age", "city", "time_zone",
        "preferred_systems", "about_info"
    }

    user = await get_user_model(session, tg_id)
    if not user:
        return None

    updated_user = await _edit_entity(
        session,
        User,
        user.id,
        changes,
        allowed_fields
    )
    return UserModel(updated_user) if updated_user else None


async def edit_player(tg_id: int, changes: dict, session: AsyncSession) -> Optional[PlayerModel]:
    allowed_fields = {"experience_level", "availability"}

    player = await get_player_model(session, tg_id)
    if not player:
        return None

    updated_player = await _edit_entity(
        session,
        Player,
        player.id,
        changes,
        allowed_fields
    )
    return PlayerModel(updated_player) if updated_player else None


async def edit_master(tg_id: int, changes: dict, session: AsyncSession) -> Optional[MasterModel]:
    allowed_fields = {"master_style", "rating"}

    master = await get_master_model(session, tg_id)
    if not master:
        return None

    updated_master = await _edit_entity(
        session,
        Master,
        master.id,
        changes,
        allowed_fields
    )
    return MasterModel(updated_master) if updated_master else None


async def edit_game(game_id: int, changes: dict, session: AsyncSession) -> Optional[SessionModel]:
    allowed_fields = {
        "title", "description", "game_system",
        "date_time", "status", "max_players"
    }

    game = await get_game_model(session, game_id)
    if not game:
        return None

    updated_game = await _edit_entity(
        session,
        Session,
        game.id,
        changes,
        allowed_fields
    )
    return SessionModel(updated_game) if updated_game else None
