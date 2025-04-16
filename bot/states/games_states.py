from aiogram.fsm.state import State, StatesGroup


class AllGames(StatesGroup):
    checking_games = State()
    checking_master_games = State()
    checking_player_games = State()


class GameInspection(StatesGroup):
    # General
    checking_game = State()
    rating_game = State()
    # Player
    exit_group_confirmation = State()
    # Master
    choosing_what_to_edit = State()
    publishing_confirmation = State()
    checking_applications = State()
    managing_group = State()



class GameCreation(StatesGroup):
    choosing_default = State()
    typing_title = State()
    choosing_format = State()
    choosing_type = State()
    typing_place = State()
    typing_platform = State()
    choosing_cost = State()
    typing_cost = State()
    typing_time = State()
    choosing_system = State()
    choosing_edition = State()
    choosing_players_number = State()
    choosing_age = State()
    typing_requirements = State()
    typing_description = State()
    loading_picture = State()
