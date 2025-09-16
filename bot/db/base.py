from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, DateTime,
    ForeignKey, Boolean, Table
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()
metadata = Base.metadata

session_players = Table(
    "session_players",
    Base.metadata,
    Column("session_id", Integer, ForeignKey("sessions.id"), primary_key=True),
    Column("player_id", Integer, ForeignKey("players.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String(100), nullable=False)
    time_zone = Column(Integer, nullable=False)
    role = Column(Integer, nullable=False)
    game_format = Column(Integer, nullable=False)
    preferred_systems = Column(String, nullable=False)
    about_info = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    player_profile = relationship("Player", back_populates="user", cascade="all, delete-orphan", uselist=False)
    master_profile = relationship("Master", back_populates="user", cascade="all, delete-orphan", uselist=False)
    sessions = relationship("Session", back_populates="creator", cascade="all, delete")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    experience_level = Column(Integer)
    availability = Column(String)

    user = relationship("User", back_populates="player_profile")
    sessions = relationship("Session", secondary=session_players, back_populates="players")


class Master(Base):
    __tablename__ = "masters"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    master_style = Column(Text)
    rating = Column(Integer, default=0)

    user = relationship("User", back_populates="master_profile")
    sessions = relationship("Session", back_populates="master")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    game_system = Column(String)
    date_time = Column(DateTime, nullable=False)
    format = Column(Integer, nullable=False)
    status = Column(Boolean, default=True)
    max_players = Column(Integer)
    looking_for = Column(Integer)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    master_id = Column(Integer, ForeignKey("masters.id"), nullable=True)

    creator = relationship("User", back_populates="sessions")
    master = relationship("Master", back_populates="sessions")
    players = relationship("Player", secondary=session_players, back_populates="sessions")
