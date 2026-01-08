# activity_log.py
"""
Функции для получения лога смен активностей.
"""

from datetime import datetime, timedelta
from database import get_activity_log_data
from config import ACTIVITIES
from utils import get_activity_emoji


def format_activity_log(activities):
    """
    Форматирует список активностей в читаемый лог.

    Args:
        activities: список кортежей (timestamp, from_activity, to_activity)

    Returns:
        str: отформатированный лог
    """
    if not activities:
        return "Лог активностей пуст."

    log_by_date = {}

    for timestamp_str, from_activity, to_activity in activities:
        # Парсим время
        timestamp = datetime.fromisoformat(timestamp_str)
        date_str = timestamp.strftime("%d.%m.%Y")
        time_str = timestamp.strftime("%H:%M:%S")

        # Получаем названия активностей
        from_name = ACTIVITIES.get(from_activity, from_activity)
        to_name = ACTIVITIES.get(to_activity, to_activity)

        # Получаем эмодзи
        from_emoji = get_activity_emoji(from_activity)
        to_emoji = get_activity_emoji(to_activity)

        # Форматируем строку
        log_entry = f"{time_str} {from_emoji}{from_name} -> {to_emoji}{to_name}"

        # Группируем по дате
        if date_str not in log_by_date:
            log_by_date[date_str] = []
        log_by_date[date_str].append(log_entry)

    # Формируем итоговый текст (от старых дат к новым)
    result_lines = []
    for date_str in sorted(log_by_date.keys()):  # Убрали reverse=True
        result_lines.append(date_str)  # Убрали теги <b></b>
        # Выводим записи в порядке от старых к новым в пределах дня
        for log_entry in log_by_date[date_str]:
            result_lines.append(log_entry)
        result_lines.append("")  # Пустая строка между днями

    return "\n".join(result_lines)


async def get_activity_log(user_id, days=7):
    """
    Получает лог смен активностей за указанное количество дней.

    Args:
        user_id: ID пользователя
        days: количество дней (по умолчанию 7)

    Returns:
        str: отформатированный лог
    """
    try:
        activities = get_activity_log_data(user_id, days)
        return format_activity_log(activities)
    except Exception as e:
        print(f"Ошибка получения лога для пользователя {user_id}: {e}")
        return "⚠️ Произошла ошибка при получении лога. Попробуйте позже."