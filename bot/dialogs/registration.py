import operator
from email.headerregistry import Group

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Column, Next, SwitchTo, Select, Group

from bot.states.general_states import Registration

# TODO: implement database
profile = {}

# TODO: display not const, but the most popular cities
# Passing arguments to dialog (GETTERS)
async def get_cities(**kwargs):
    biggest_cities = [
        { "city": "Москва", "id": "city_moscow", "time_zone": "GMT+3" },
        { "city": "Санкт-Петербург", "id": "city_saint_petersburg", "time_zone": "GMT+3" },
        { "city": "Новосибирск", "id": "city_novosibirsk", "time_zone": "GMT+7" },
        { "city": "Екатеринбург", "id": "city_yekaterinburg", "time_zone": "GMT+5" },
        { "city": "Казань", "id": "city_kazan", "time_zone": "GMT+3" },
        { "city": "Нижний Новгород", "id": "city_nizhny_novgorod", "time_zone": "GMT+3" },
    ]
    return {
        "cities": biggest_cities
    }

async def get_time_zones(**kwargs):
    time_zones = []

    for zone in range(1, 13):
        str_zone = "GMT+{}".format(zone)
        str_id = "time_zone_gmt+{}".format(zone)
        time_zones.append({ "zone": str_zone, "id": str_id })

    time_zones.append({ "zone": "GMT+0", "id": "time_zone_gmt+0" })
    for zone in range(1, 12):
        str_zone = "GMT-{}".format(zone)
        str_id = "time_zone_gmt-{}".format(zone)
        time_zones.append({ "zone": str_zone, "id": str_id })

    return {
        "zones": time_zones
    }

# RAISING ERROR
async def raise_keyboard_error(callback: CallbackQuery, item_type: str):
    await callback.answer(text="Что-то пошло не так, попробуйте выбрать {} снова.\n"
                               "Если это не поможет, обратитесь в поддержку.".format(item_type),
                          show_alert=True)


# Saving profile settings (ONCLICK)
async def save_name(message: Message, message_input: MessageInput, manager: DialogManager):
    profile["name"] = message.text
    await manager.switch_to(Registration.typing_age)

async def save_age(message: Message, message_input: MessageInput, manager: DialogManager):
    str_age = message.text
    if str_age is None or not str_age.isdigit():
        await message.answer("Введите число.")
        return

    int_age = int(str_age)
    if int_age > 99 or int_age < 12:
        await message.answer("Введите число от 12 до 99.")
        return

    profile["age"] = int_age

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
    profile["format"] = session_format

async def save_city(callback: CallbackQuery, button: Button, manager: DialogManager, item_id: str):
    data = await get_cities()
    items = data["cities"]
    item = [item for item in items if item["id"] == item_id]
    if len(item) != 1:
        await raise_keyboard_error(callback, "город")
        return
    item = item[0]

    profile["city"] = item["city"]
    profile["time_zone"] = item["time_zone"]

    # TODO: detect time zone automatically for all cities
    await manager.switch_to(Registration.choosing_role)

async def save_time_zone(callback: CallbackQuery, button: Button, manager: DialogManager,  item_id: str):
    data = await get_time_zones()
    items = data["time_zones"]
    item = [item for item in items if item["id"] == item_id]
    if len(items) != 1:
        await raise_keyboard_error(callback, "часовой пояс")
        return
    item = item[0]

    profile["time_zone"] = item["time_zone"]

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
    profile["role"] = role


async def save_about_info(message: Message, message_input: MessageInput, manager: DialogManager):
    profile["about_info"] = message.text
    await manager.done()

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
        Row(SwitchTo(Const("Оффлайн"), state=Registration.choosing_city, id="format_offline", on_click=save_format),
            SwitchTo(Const("Онлайн"), state=Registration.choosing_city, id="format_online", on_click=save_format)),
        SwitchTo(Const("Оффлайн и Онлайн"), state=Registration.choosing_city, id="format_both", on_click=save_format),
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
        state=Registration.choosing_city,
        getter = get_cities,
),
    # Getting time zone
    Window(
        Const("Выберете ваш часовой пояс."),
        Group(
            Select(
                text=Format("{item[zone]}"),
                id="time_zone_select",
                item_id_getter=lambda item: item["id"],
                items="zones",
                on_click=save_time_zone,
            ),
            width=6,
        ),
        state=Registration.choosing_time_zone,
        getter=get_time_zones,
    ),
    # Getting role
    Window(
        Const("Выберете роль, в которой будете выступать."),
        Row(SwitchTo(Const("Игрок"), state=Registration.typing_about_information, id="role_player", on_click=save_role),
            SwitchTo(Const("Мастер"), state=Registration.typing_about_information, id="role_master", on_click=save_role)),
        SwitchTo(Const("Игрок и Мастер"), state=Registration.typing_about_information, id="role_both", on_click=save_role),
        state=Registration.choosing_role,
    ),
    # Getting about info
    Window(
        Const("Расскажите немного о себе."),
        MessageInput(func=save_about_info, content_types=[ContentType.TEXT]),
        state=Registration.typing_about_information,
    )
)