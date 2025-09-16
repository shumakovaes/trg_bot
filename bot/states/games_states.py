from __future__ import annotations
from aiogram.fsm.state import StatesGroup, State


class AllGames(StatesGroup):
    """States for 'My games' section."""
    player_games = State()
    master_games = State()
    player_archive = State()
    master_archive = State()
    checking_games = State()
    listing_player_games = State()
    listing_master_games = State()
    viewing_game = State()


class GameCreation(StatesGroup):
    """States for game creation/editing."""
    choosing_default = State()
    typing_title = State()
    typing_description = State()
    choosing_system = State()
    choosing_format = State()
    choosing_place = State()
    choosing_cost = State()
    typing_cost = State()
    confirming = State()


class SearchingGame(StatesGroup):
    """States for searching/browsing games."""
    checking_open_games = State()   # <-- added to satisfy default_commands.start(...)
    choosing_filters = State()
    listing_results = State()
    inspecting_game = State()


class GameInspection(StatesGroup):
    """States for inspecting a specific game."""
    viewing = State()
