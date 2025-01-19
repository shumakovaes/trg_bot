from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    typing_nickname = State()
    typing_age = State()
    choosing_format = State()
    choosing_city = State()
    choosing_time_zone = State()
    choosing_role = State()
    typing_about_information = State()
