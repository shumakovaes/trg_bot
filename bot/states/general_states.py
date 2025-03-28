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


class PlayerForm(StatesGroup):
    checking_info = State()
    choosing_what_to_edit = State()
    choosing_experience = State()
    choosing_payment = State()
    choosing_systems = State()


# TODO: Implement master form
class MasterForm(StatesGroup):
    checking_info = State()
    choosing_what_to_edit = State()
    choosing_experience = State()
    choosing_cost = State()
    typing_cost = State()
    typing_place = State()
    choosing_platform = State()
    typing_platform = State()
    typing_requirements = State()