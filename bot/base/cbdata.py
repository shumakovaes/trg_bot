from aiogram.dispatcher.filters.callback_data import CallbackData

class NewProfileCallbackFactory(CallbackData, prefix="new_profile_role"):
    role: str