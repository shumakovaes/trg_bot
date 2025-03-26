from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.sql import func

from bot.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    format = Column(ENUM('Оффлайн', 'Онлайн', 'Оффлайн и Онлайн', name='game_format'), nullable=False)
    city = Column(String(100), nullable=False)
    time_zone = Column(String(10), nullable=False)
    role = Column(ENUM('Игрок', 'Мастер', 'Игрок и Мастер', name='user_role'), nullable=False)
    about_info = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
