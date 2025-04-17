from aiogram.fsm.state import State, StatesGroup


class AllGames(StatesGroup):
    checking_games = State()
    checking_archive = State()
    checking_master_games = State()
    checking_master_archive = State()
    checking_player_games = State()
    checking_player_archive = State()


class GameInspection(StatesGroup):
    # General
    checking_game = State()
    rating_game = State()
    delete_game_confirmation = State()
    change_game_folder_confirmation = State()
    # Master
    choosing_what_to_edit = State()
    set_status_public_confirmation = State()
    set_status_done_confirmation = State()
    checking_applications = State()
    managing_group = State()



class GameCreation(StatesGroup):
    choosing_default = State()
    typing_title = State()
    choosing_format = State()
    typing_place = State()
    typing_platform = State()
    choosing_cost = State()
    typing_cost = State()
    typing_time = State()
    choosing_type = State()
    choosing_system = State()
    choosing_edition = State()
    choosing_players_number = State()
    choosing_age = State()
    typing_requirements = State()
    typing_description = State()
    loading_picture = State()

class SearchingGame(StatesGroup):
    checking_open_games = State()
    checking_specific_game = State()
    checking_master_form = State()
    checking_filters = State()
    format_filter = State()
    cost_filter = State()
    type_filter = State()
    system_filter = State()
    age_filter = State()
