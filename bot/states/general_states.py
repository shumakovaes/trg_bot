from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    typing_nickname = State()
    typing_age = State()
    choosing_format = State()
    choosing_city = State()
    choosing_time_zone = State()
    choosing_role = State()
    typing_about_information = State()
    end_of_dialog = State()


class Profile(StatesGroup):
    checking_info = State()
    choosing_what_to_edit = State()


# TODO: Implement player form
class PlayerForm(StatesGroup):
    player_form = State()


# TODO: Implement master form
class MasterForm(StatesGroup):
    master_form = State()
