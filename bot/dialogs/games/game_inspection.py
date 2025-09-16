# bot/dialogs/games/game_inspection.py
from __future__ import annotations

from typing import Any, Dict

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const, Jinja, Multi
from aiogram_dialog.widgets.kbd import Back

from bot.states.games_states import GameInspection


# ---------- getters ----------

async def get_inspected_game(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """
    Источник данных для окна просмотра игры.
    Ожидается, что объект игры будет лежать либо в dialog_data['inspected_game'],
    либо будет передан через start_data при запуске диалога.

    Пример структуры:
    {
        "id": "g_123",
        "title": "Вечер D&D 5e",
        "system": "D&D 5e",
        "format": "online|offline|hybrid",
        "place": "Roll20/Discord" или "Москва, Клуб X",
        "cost": "Бесплатно" или "500 ₽ / 3 часа",
        "description": "Краткое описание...",
        "master_name": "Иван",
        "players": ["Аня", "Борис", "Сергей"],
    }
    """
    data = dialog_manager.dialog_data.get("inspected_game")
    if not data:
        # пробуем достать из start_data и одновременно сохранить в dialog_data
        data = dialog_manager.start_data.get("inspected_game", {})
        if data:
            dialog_manager.dialog_data["inspected_game"] = data
    # гарантируем, что вернём словарь
    return dict(data or {})


# ---------- dialog ----------

game_inspection_dialog = Dialog(
    Window(
        Multi(
            Jinja("<b>{{ title or 'Без названия' }}</b>"),
            Jinja("\n<b>Система</b>: {{ system or '—' }}"),
            Jinja("\n<b>Формат</b>: {{ format or '—' }}"),
            Jinja("\n<b>Место</b>: {{ place or '—' }}"),
            Jinja("\n<b>Стоимость</b>: {{ cost or '—' }}"),
            Jinja("\n\n<b>Ведущий</b>: {{ master_name or '—' }}"),
            Jinja("\n<b>Игроки</b>: {{ (players|join(', ')) if players else '—' }}"),
            Jinja("\n\n<b>Описание</b>:\n{{ description or '—' }}"),
        ),
        Back(Const("Назад")),
        getter=get_inspected_game,
        state=GameInspection.viewing,
    ),
)
