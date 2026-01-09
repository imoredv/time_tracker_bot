# activity_log.py
"""
Функции для получения лога смен активностей.
"""

from datetime import datetime, timedelta
from database import get_activity_log_data
from config import ACTIVITIES
from utils import get_activity_emoji


def format_activity_log(activities, user_id):
    """
    Форматирует список активностей в читаемый лог в локальном времени пользователя.

    Args:
        activities: список кортежей (timestamp, from_activity, to_activity)
                    Для самой первой активности за всю историю: (timestamp, None, activity_type) - СТАРТ
                    Для всех остальных смен: (timestamp, from_activity, to_activity) -> переход
        user_id: ID пользователя для определения часового пояса

    Returns:
        str: отформатированный лог
    """
    if not activities:
        return "Лог активностей пуст."

    from database import get_user_timezone

    # Получаем часовой пояс пользователя
    timezone_code = get_user_timezone(user_id)

    # Маппинг часовых поясов для pytz
    tz_mapping = {
        'Russian Standard Time': 'Europe/Moscow',
        'FLE Standard Time': 'Europe/Kiev',
        'Belarus Standard Time': 'Europe/Minsk',
        'West Asia Standard Time': 'Asia/Yekaterinburg',
        'Central Asia Standard Time': 'Asia/Almaty',
        'SE Asia Standard Time': 'Asia/Bangkok',
        'China Standard Time': 'Asia/Shanghai',
        'Tokyo Standard Time': 'Asia/Tokyo',
        'GMT Standard Time': 'Europe/London',
        'W. Europe Standard Time': 'Europe/Berlin',
        'Eastern Standard Time': 'America/New_York',
        'Pacific Standard Time': 'America/Los_Angeles',
        'UTC': 'UTC',
    }

    user_tz_name = tz_mapping.get(timezone_code, 'UTC')

    try:
        import pytz
        user_tz = pytz.timezone(user_tz_name)
    except:
        user_tz = None

    log_by_date = {}

    for timestamp_str, from_activity, to_activity in activities:
        # Парсим время (хранится в UTC)
        timestamp = datetime.fromisoformat(timestamp_str)

        # Конвертируем в локальное время пользователя
        if user_tz:
            # Добавляем информацию о часовом поясе UTC и конвертируем
            utc_time = timestamp.replace(tzinfo=pytz.UTC)
            local_time = utc_time.astimezone(user_tz)
        else:
            local_time = timestamp

        # Форматируем дату и время
        date_str = local_time.strftime("%d.%m.%Y")
        time_str = local_time.strftime("%H:%M:%S")

        # Получаем эмодзи
        to_emoji = get_activity_emoji(to_activity)

        # Форматируем строку в зависимости от типа записи
        if from_activity is None:
            # Это СТАРТ самой первой активности за всю историю
            to_name = ACTIVITIES.get(to_activity, to_activity)
            log_entry = f"{time_str} {to_emoji}{to_name} СТАРТ"
        else:
            # Это смена активности
            from_name = ACTIVITIES.get(from_activity, from_activity)
            to_name = ACTIVITIES.get(to_activity, to_activity)
            from_emoji = get_activity_emoji(from_activity)
            log_entry = f"{time_str} {from_emoji}{from_name} -> {to_emoji}{to_name}"

        # Группируем по дате
        if date_str not in log_by_date:
            log_by_date[date_str] = []
        log_by_date[date_str].append(log_entry)

    # Формируем итоговый текст (от старых дат к новым)
    result_lines = []
    for date_str in sorted(log_by_date.keys()):
        result_lines.append(date_str)
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
        return format_activity_log(activities, user_id)
    except Exception as e:
        print(f"Ошибка получения лога для пользователя {user_id}: {e}")
        return "⚠️ Произошла ошибка при получении лога. Попробуйте позже."