from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, SwitchTo, Select, Group, Cancel

from bot.states.general_states import Registration, PlayerForm, MasterForm

# TODO: implement database
user = { "name": "", "age": "", "city": "", "time_zone": "", "role": "", "format": "", "about_info": "" }

# TODO: display not const, but the most popular cities
# Passing arguments to dialog (GETTERS)
async def get_cities(**kwargs):
    biggest_cities = [
        { "city": "Москва", "id": "city_moscow", "time_zone": "МСК (UTC/GMT +3)" },
        { "city": "Санкт-Петербург", "id": "city_saint_petersburg", "time_zone": "МСК (UTC/GMT +3)" },
        { "city": "Новосибирск", "id": "city_novosibirsk", "time_zone": "МСК+4 (UTC/GMT +7)" },
        { "city": "Екатеринбург", "id": "city_yekaterinburg", "time_zone": "МСК+2 (UTC/GMT +5)" },
        { "city": "Казань", "id": "city_kazan", "time_zone": "МСК (UTC/GMT +3)" },
        { "city": "Нижний Новгород", "id": "city_nizhny_novgorod", "time_zone": "МСК (UTC/GMT +3)" },
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

    time_zones = [{ "time_zone": "Калининградское МСК-1 (UTC/GMT +2)", "id":  "time_zone_utc+2"},
                 { "time_zone": "Московское МСК (UTC/GMT +3)", "id":  "time_zone_utc+3"}]

    for zone in range(2, 11):
        str_zone = "{} МСК+{} (UTC/GMT +{})".format(main_cities[zone], zone - 1, zone + 2)
        str_id = "time_zone_utc+{}".format(zone + 2)
        time_zones.append({ "time_zone": str_zone, "id": str_id })

    return {
        "time_zones": time_zones
    }

# RAISING ERROR
async def raise_keyboard_error(callback: CallbackQuery, item_type: str):
    await callback.answer(text="Что-то пошло не так, попробуйте выбрать {} снова.\n"
                               "Если это не поможет, обратитесь в поддержку.".format(item_type),
                          show_alert=True)


# Saving profile settings (ONCLICK)
async def save_name(message: Message, message_input: MessageInput, manager: DialogManager):
    user["name"] = message.text

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.typing_age)

async def save_age(message: Message, message_input: MessageInput, manager: DialogManager):
    str_age = message.text.strip()
    if str_age is None or not str_age.isdigit():
        await message.answer("Вам необходимо ввести число.")
        return

    int_age = int(str_age)
    if int_age > 99 or int_age < 12:
        await message.answer("Чтобы пользоваться ботом, вы должны быть старше 12 лет.")
        return

    user["age"] = int_age

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.choosing_format)

async def save_format(callback: CallbackQuery, button: Button, manager: DialogManager):
    get_format_by_id = {
        "format_offline": "Оффлайн",
        "format_online": "Онлайн",
        "format_both": "Оффлайн и Онлайн",
    }
    session_format = get_format_by_id.get(button.widget_id)

    if session_format is None:
        await raise_keyboard_error(callback, "формат")
    user["format"] = session_format

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.choosing_city)

async def save_city(callback: CallbackQuery, button: Button, manager: DialogManager, item_id: str):
    data = await get_cities()
    items = data["cities"]
    item = [item for item in items if item["id"] == item_id]
    if len(item) != 1:
        await raise_keyboard_error(callback, "город")
        return
    item = item[0]

    user["city"] = item["city"]
    user["time_zone"] = item["time_zone"]

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.choosing_role)

async def save_city_from_user(message: Message, message_input: MessageInput, manager: DialogManager):
    # TODO: detect time zone automatically for all cities
    user["city"] = message.text

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.choosing_time_zone)

is_updating = False

async def save_time_zone(callback: CallbackQuery, button: Button, manager: DialogManager,  item_id: str):
    data = await get_time_zones()
    items = data["time_zones"]
    item = [item for item in items if item["id"] == item_id]
    if len(item) != 1:
        await raise_keyboard_error(callback, "часовой пояс")
        return
    item = item[0]

    user["time_zone"] = item["time_zone"]

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.choosing_role)

async def save_time_zone_from_user(message: Message, message_input: MessageInput, manager: DialogManager):
    time_zone = message.text.strip().rstrip('.').rstrip(':').strip('"').strip('\'')
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

    msk_time = "{}{}{}".format(get_plus_sign(int_time_zone_hours), int_time_zone_hours, time_zone_minutes)
    utc_time = "{}{}{}".format(get_plus_sign(int_time_zone_hours - 3), int_time_zone_hours - 3, time_zone_minutes)
    formatted_time_zone = "МСК{} (UTC/GMT {})".format(msk_time, utc_time)

    user["time_zone"] = formatted_time_zone

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.choosing_role)

async def save_role(callback: CallbackQuery, button: Button, manager: DialogManager):
    get_role_by_id = {
        "role_player": "Игрок",
        "role_master": "Мастер",
        "role_both": "Игрок и Мастер",
    }
    role = get_role_by_id.get(button.widget_id)

    if role is None:
        await raise_keyboard_error(callback, "роль")
    user["role"] = role

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.typing_about_information)

async def save_about_info(message: Message, message_input: MessageInput, manager: DialogManager):
    user["about_info"] = message.text

    if manager.start_data["type"] == "edit":
        await manager.done()
    else:
        await manager.switch_to(Registration.end_of_dialog)

# TODO: change phrases, make them more friendly
# TODO: change Const to Jinja
# Registration dialog
dialog = Dialog(
    # Getting nickname
    Window(
        Const("Введите ваше имя или никнейм."),
        MessageInput(func=save_name, content_types=[ContentType.TEXT]),
        state=Registration.typing_nickname,
    ),
    # Getting age
    Window(
        Const("Введите ваш возраст, число от 12 до 99."),
        MessageInput(func=save_age, content_types=[ContentType.TEXT]),
        state=Registration.typing_age,
    ),
    # Getting format
    Window(
        Const("Выберете удобный для вас формат проведения игр.\n"
              "При создании игры это настройка будет применена по умолчанию, но вы сможете изменить её при создании сессии."),
        Row(Button(Const("Оффлайн"), id="format_offline", on_click=save_format),
            Button(Const("Онлайн"), id="format_online", on_click=save_format)),
        Button(Const("Оффлайн и Онлайн"), id="format_both", on_click=save_format),
        state=Registration.choosing_format,
    ),
    # Getting city
    Window(
        Const("Выберите город, в котором живёте. Если его нет в списке, то отправьте его название ответным сообщением."),
        Column(Select(
            text=Format("{item[city]}"),
            id="cities_select",
            item_id_getter=lambda item: item["id"],
            items="cities",
            on_click=save_city,
        )),
        MessageInput(func=save_city_from_user, content_types=[ContentType.TEXT]),
        state=Registration.choosing_city,
        getter = get_cities,
    ),
    # Getting time zone
    Window(
        Const("Выберете ваш часовой пояс. Если его нет в списке, укажите его в формате UTC. Вводите только знак и цифры, например: -5, 0 или +5:30."),
        Column(
            Select(
                text=Format("{item[time_zone]}"),
                id="time_zone_select",
                item_id_getter=lambda item: item["id"],
                items="time_zones",
                on_click=save_time_zone,
            ),
        ),
        MessageInput(func=save_time_zone_from_user, content_types=[ContentType.TEXT]),
        state=Registration.choosing_time_zone,
        getter=get_time_zones,
    ),
    # Getting role
    Window(
        Const("Выберете роль, в которой будете выступать."),
        Row(Button(Const("Игрок"), id="role_player", on_click=save_role),
            Button(Const("Мастер"), id="role_master", on_click=save_role)),
        Button(Const("Игрок и Мастер"), id="role_both", on_click=save_role),
        state=Registration.choosing_role,
    ),
    # Getting about info
    Window(
        Const("Расскажите немного о себе."),
        MessageInput(func=save_about_info, content_types=[ContentType.TEXT]),
        state=Registration.typing_about_information,
    ),
    # End of dialog
    # TODO: display player and master forms only for players and masters respectively
    # Can be done with Select() but better wait until database will be implemented
    # Maybe even not worth to do it
    Window(
        Const("Вы заполнили анкету! Вы всегда можете посмотреть или отредактировать её, введя команду /profile. Там же вы сможете указать дополнительную информацию, которая поможет мастерам лучше понять ваши интересы и сэкономит вам время при создании игры."),
        Row(Start(Const("Анкета игрока"), state=PlayerForm.player_form, id="player_form_from_register"),
            Start(Const("Анкета мастера"), state=MasterForm.master_form, id="master_form_from_register")),
        Cancel(Const("Завершить"), id="end_registration"),
        state=Registration.end_of_dialog,
    )
)