from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel

from bot.dialogs.general_tools import need_to_display_current_value, go_back_when_edit_mode, switch_state, \
    raise_keyboard_error, get_item_by_key, generate_save_message_from_user_no_formatting
from bot.dialogs.registration.profile import user, get_user_general
from bot.states.registration_states import Registration, PlayerForm, MasterForm


# TODO: display not const, but the most popular cities
# Passing arguments to the dialog (GETTERS)
async def get_cities(**kwargs):
    biggest_cities = [
        {"city": "Москва", "id": "city_moscow", "time_zone": "МСК (UTC/GMT +3)"},
        {"city": "Санкт-Петербург", "id": "city_saint_petersburg", "time_zone": "МСК (UTC/GMT +3)"},
        {"city": "Новосибирск", "id": "city_novosibirsk", "time_zone": "МСК+4 (UTC/GMT +7)"},
        {"city": "Екатеринбург", "id": "city_yekaterinburg", "time_zone": "МСК+2 (UTC/GMT +5)"},
        {"city": "Казань", "id": "city_kazan", "time_zone": "МСК (UTC/GMT +3)"},
        {"city": "Нижний Новгород", "id": "city_nizhny_novgorod", "time_zone": "МСК (UTC/GMT +3)"},
    ]
    return {
        "cities": biggest_cities
    }


async def get_time_zones(**kwargs):
    main_cities = [
        "Калининградское",
        "Московское",
        "Самарское",
        "Екатеринбургское",
        "Омское",
        "Красноярское",
        "Иркутское",
        "Якутское",
        "Владивостокское",
        "Магаданское",
        "Камчатское",
    ]

    time_zones = [{"time_zone": "Калининградское МСК-1 (UTC/GMT +2)", "id": "time_zone_utc+2"},
                  {"time_zone": "Московское МСК (UTC/GMT +3)", "id": "time_zone_utc+3"}]

    for zone in range(2, 11):
        str_zone = "{} МСК+{} (UTC/GMT +{})".format(main_cities[zone], zone - 1, zone + 2)
        str_id = "time_zone_utc+{}".format(zone + 2)
        time_zones.append({"time_zone": str_zone, "id": str_id})

    return {
        "time_zones": time_zones
    }


# SELECTORS
def is_user_player(data: dict, widget: Whenable, manager: DialogManager):
    role = user["general"].get("role")
    return role == "Игрок" or role == "Игрок и Мастер"


def is_user_master(data: dict, widget: Whenable, manager: DialogManager):
    role = user["general"].get("role")
    return role == "Мастер" or role == "Игрок и Мастер"


# Saving profile settings (ONCLICK)
save_name = generate_save_message_from_user_no_formatting("general", "name", {"edit": None, "register": Registration.typing_age})


async def save_age(message: Message, message_input: MessageInput, manager: DialogManager):
    str_age = message.text.strip()
    if str_age is None or not str_age.isdigit():
        await message.answer("Вам необходимо ввести число.")
        return

    int_age = int(str_age)
    if int_age > 99 or int_age < 14:
        await message.answer("Чтобы пользоваться ботом, вы должны быть старше 14 лет.")
        return

    user["general"]["age"] = int_age

    next_states = {"edit": None, "register": Registration.choosing_format}
    await switch_state(manager, next_states)


async def save_format(callback: CallbackQuery, button: Button, manager: DialogManager):
    format_by_id = {
        "format_offline": "Оффлайн",
        "format_online": "Онлайн",
        "format_both": "Оффлайн и Онлайн",
    }
    session_format = format_by_id.get(button.widget_id)

    if session_format is None:
        await raise_keyboard_error(callback, "формат")
        return
    user["general"]["format"] = session_format

    next_states = {"edit": None, "register": Registration.choosing_city}
    await switch_state(manager, next_states)


async def save_city(callback: CallbackQuery, button: Button, manager: DialogManager, item_id: str):
    item = await get_item_by_key(get_cities, "cities", "id", item_id, callback, "город", False, False)

    user["general"]["city"] = item["city"]
    user["general"]["time_zone"] = item["time_zone"]

    next_states = {"edit": None, "register": Registration.choosing_role}
    await switch_state(manager, next_states)


async def save_city_from_user(message: Message, message_input: MessageInput, manager: DialogManager):
    # TODO: detect time zone automatically for all cities
    user_city = message.text.strip(". \"\'")

    # TODO: detect synonyms to main cites, e. g. Москва - мск
    item = await get_item_by_key(get_cities, "cities", "city", user_city, message, "город", True, True)

    if not item is None:
        user["general"]["city"] = item["city"]
        user["general"]["time_zone"] = item["time_zone"]

        next_states = {"edit": None, "register": Registration.choosing_role}
        await switch_state(manager, next_states)
        return

    user["general"]["city"] = user_city.title()

    next_states = {"edit": Registration.choosing_time_zone, "register": Registration.choosing_time_zone}
    await switch_state(manager, next_states)


async def save_time_zone(callback: CallbackQuery, button: Button, manager: DialogManager, item_id: str):
    item = await get_item_by_key(get_time_zones, "time_zones", "id", item_id, callback, "часовой пояс", False, False)

    user["general"]["time_zone"] = item["time_zone"]

    next_states = {"edit": None, "register": Registration.choosing_role}
    await switch_state(manager, next_states)


async def save_time_zone_from_user(message: Message, message_input: MessageInput, manager: DialogManager):
    time_zone = message.text.strip(" .:\"\'")
    if time_zone is None:
        await message.answer("Ваше сообщение не должно быть пустым.")
        return

    parts = list(time_zone.split(":"))
    if len(parts) > 2:
        await message.answer("Не используйте более одного двоеточия.")
        return

    str_time_zone_hours = parts[0].lstrip('+').lstrip('-')
    if not str_time_zone_hours.isdigit():
        await message.answer("Часы должны быть числом от -12 до +14.")
        return

    int_time_zone_hours = int(parts[0])
    if int_time_zone_hours < -12 or int_time_zone_hours > 14:
        await message.answer("Часы должны быть числом от -12 до +14.")
        return

    time_zone_minutes = ""
    if len(parts) == 2:
        time_zone_minutes = parts[1]
        allowed_minutes = ["00", "15", "30", "45"]
        if not time_zone_minutes in allowed_minutes:
            await message.answer("Минуты должны равняться 00, 15, 30 или 45.")
            return

        if time_zone_minutes != "00":
            time_zone_minutes = ":" + time_zone_minutes
        else:
            time_zone_minutes = ""

    def get_plus_sign(number):
        if int_time_zone_hours > 0:
            return "+"
        return ""

    utc_time = "{}{}{}".format(get_plus_sign(int_time_zone_hours), int_time_zone_hours, time_zone_minutes)
    msk_time = "{}{}{}".format(get_plus_sign(int_time_zone_hours - 3), int_time_zone_hours - 3, time_zone_minutes)
    formatted_time_zone = "МСК{} (UTC/GMT {})".format(msk_time, utc_time)

    user["general"]["time_zone"] = formatted_time_zone

    next_states = {"edit": None, "register": Registration.choosing_role}
    await switch_state(manager, next_states)


async def save_role(callback: CallbackQuery, button: Button, manager: DialogManager):
    role_by_id = {
        "role_player": "Игрок",
        "role_master": "Мастер",
        "role_both": "Игрок и Мастер",
    }
    role = role_by_id.get(button.widget_id)

    if role is None:
        await raise_keyboard_error(callback, "роль")
        return
    user["general"]["role"] = role

    next_states = {"edit": None, "register": Registration.typing_about_information}
    await switch_state(manager, next_states)


save_about_info = generate_save_message_from_user_no_formatting("general", "about_info", {"edit": None, "register": Registration.end_of_dialog})


# TODO: change phrases, make them more friendly
# Registration dialog
registration_dialog = Dialog(
    # Getting nickname
    Window(
        Const("Введите ваше имя или никнейм."),
        Jinja("\n<b>Текущее значение</b>: {{name}}", when=need_to_display_current_value),

        MessageInput(func=save_name, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=Registration.typing_nickname,
    ),
    # Getting age
    Window(
        Const("Введите ваш возраст, число от 14 до 99."),
        Jinja("\n<b>Текущее значение</b>: {{age}}", when=need_to_display_current_value),

        MessageInput(func=save_age, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=Registration.typing_age,
    ),
    # Getting format
    Window(
        Const("Выберете удобный для вас формат проведения игр.\n"),
        Jinja("\n<b>Текущее значение</b>: {{format}}", when=need_to_display_current_value),

        Row(
            Button(Const("Оффлайн"), id="format_offline", on_click=save_format),
            Button(Const("Онлайн"), id="format_online", on_click=save_format)),
        Button(Const("Оффлайн и Онлайн"), id="format_both", on_click=save_format
               ),

        go_back_when_edit_mode,
        state=Registration.choosing_format,
    ),
    # Getting city
    Window(
        Const(
            "Выберите город, в котором живёте.\nЕсли его нет в списке, то отправьте его название ответным сообщением."),
        Jinja("\n<b>Текущее значение</b>: {{city}}", when=need_to_display_current_value),

        Column(Select(
            text=Format("{item[city]}"),
            id="cities_select",
            item_id_getter=lambda item: item["id"],
            items="cities",
            on_click=save_city,
        )),
        MessageInput(func=save_city_from_user, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=Registration.choosing_city,
        getter=get_cities,
    ),
    # Getting time zone
    Window(
        Const(
            "Выберете ваш часовой пояс.\nЕсли его нет в списке, укажите его в формате UTC. Вводите только знак и цифры, например: -5, 0 или +5:30."),
        Jinja("\n<b>Текущее значение</b>: {{time_zone}}", when=need_to_display_current_value),

        Column(
            Select(
                text=Jinja("{{item[time_zone]}}"),
                id="time_zone_select",
                item_id_getter=lambda item: item["id"],
                items="time_zones",
                on_click=save_time_zone,
            ),
        ),
        MessageInput(func=save_time_zone_from_user, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=Registration.choosing_time_zone,
        getter=get_time_zones,
    ),
    # Getting role
    Window(
        Const("Выберете роль, в которой будете выступать."),
        Jinja("\n<b>Текущее значение</b>: {{role}}", when=need_to_display_current_value),

        Row(
            Button(Const("Игрок"), id="role_player", on_click=save_role),
            Button(Const("Мастер"), id="role_master", on_click=save_role)),
        Button(Const("Игрок и Мастер"), id="role_both", on_click=save_role
               ),

        go_back_when_edit_mode,
        state=Registration.choosing_role,
    ),
    # Getting about info
    Window(
        Const("Расскажите немного о себе."),
        Jinja("\n<b>Текущее значение</b>: {{about_info}}", when=need_to_display_current_value),

        MessageInput(func=save_about_info, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=Registration.typing_about_information,
    ),
    # End of dialog
    Window(
        Const(
            "Вы заполнили анкету! Вы всегда можете посмотреть или отредактировать её, введя команду /profile. Там же вы сможете указать дополнительную информацию, которая поможет мастерам лучше понять ваши интересы и сэкономит вам время при создании игры."),
        Row(Start(Const("Анкета игрока"), state=PlayerForm.checking_info, id="player_form_from_register",
                  when=is_user_player),
            Start(Const("Анкета мастера"), state=MasterForm.checking_info, id="master_form_from_register"),
            when=is_user_master),
        Cancel(Const("Завершить"), id="end_registration"),
        state=Registration.end_of_dialog,
    ),
    getter=get_user_general,
)
