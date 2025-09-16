# bot/states/registration_states.py
from __future__ import annotations
from aiogram.fsm.state import StatesGroup, State


class Registration(StatesGroup):
    """
    Top-level registration flow (legacy-compatible).
    Many dialogs/handlers reference these states directly.
    """
    choosing_what_to_edit = State()   # legacy hub
    typing_age = State()              # legacy
    typing_nickname = State()         # used by registration.py

    # Newly added / commonly expected selection states:
    choosing_city = State()           # <-- registration.py expects this
    choosing_time_zone = State()
    choosing_role = State()
    choosing_game_format = State()
    choosing_format = State()
    choosing_preferred_systems = State()
    confirming = State()
    typing_about_information = State()


class Profile(StatesGroup):
    """
    Profile flow states used by profile-related dialogs.
    Keep both 'editing' and the legacy 'choosing_what_to_edit' to satisfy imports.
    """
    check_player = State()            # entry point elsewhere
    viewing = State()                 # show consolidated profile
    editing = State()                 # generic editing hub
    choosing_what_to_edit = State()   # legacy name expected by some modules
    checking_info = State()


class PlayerForm(StatesGroup):
    """States for filling the player's profile."""
    checking_info = State()        # entry screen
    typing_name = State()
    typing_age = State()
    typing_city = State()
    choosing_format = State()      # online/offline/hybrid
    choosing_systems = State()     # choose or type RPG systems
    confirming = State()           # final confirm/save


class MasterForm(StatesGroup):
    """States for GM/master profile."""
    checking_info = State()
    typing_name = State()
    typing_age = State()
    typing_city = State()
    choosing_format = State()
    choosing_systems = State()
    confirming = State()
    choosing_cost = State()
    choosing_what_to_edit = State()
    choosing_experience = State()
    typing_place = State()
    typing_cost_value = State()
    typing_requirements = State()
    typing_experience = State()
    typing_about = State()
