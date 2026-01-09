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
    Время в базе хранится в UTC.

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

    from datetime import datetime
    from database import get_user_timezone
    import pytz

    print(f"DEBUG LOG: Текущее время сервера: {datetime.now()}")
    print(f"DEBUG LOG: Текущее время UTC: {datetime.utcnow()}")

    # Получаем часовой пояс пользователя
    timezone_code = get_user_timezone(user_id)
    print(f"DEBUG LOG: Часовой пояс из базы для пользователя {user_id}: {timezone_code}")

    # Маппинг часовых поясов для pytz
    tz_mapping = {
        'Russian Standard Time': 'Europe/Moscow',  # UTC+3
        'FLE Standard Time': 'Europe/Kiev',  # UTC+2
        'Belarus Standard Time': 'Europe/Minsk',  # UTC+3
        'West Asia Standard Time': 'Asia/Yekaterinburg',  # UTC+5 (Екатеринбург)
        'Central Asia Standard Time': 'Asia/Almaty',  # UTC+6
        'SE Asia Standard Time': 'Asia/Bangkok',  # UTC+7
        'China Standard Time': 'Asia/Shanghai',  # UTC+8
        'Tokyo Standard Time': 'Asia/Tokyo',  # UTC+9
        'GMT Standard Time': 'Europe/London',  # UTC+0
        'W. Europe Standard Time': 'Europe/Berlin',  # UTC+1
        'Eastern Standard Time': 'America/New_York',  # UTC-5
        'Pacific Standard Time': 'America/Los_Angeles',  # UTC-8
        'UTC': 'UTC',
    }

    user_tz_name = tz_mapping.get(timezone_code, 'UTC')
    print(f"DEBUG LOG: Имя часового пояса pytz: {user_tz_name}")

    try:
        user_tz = pytz.timezone(user_tz_name)
        print(f"DEBUG LOG: Объект часового пояса создан: {user_tz}")
    except Exception as e:
        print(f"DEBUG LOG: Ошибка создания часового пояса: {e}")
        user_tz = None

    log_by_date = {}

    for timestamp_str, from_activity, to_activity in activities:
        # Парсим время (хранится в UTC)
        timestamp = datetime.fromisoformat(timestamp_str)
        print(f"DEBUG LOG: Время из базы (UTC): {timestamp_str} -> {timestamp}")

        # Конвертируем в локальное время пользователя
        if user_tz:
            try:
                # Предполагаем, что время в базе в UTC (без часового пояса)
                # Добавляем часовой пояс UTC
                utc_time = pytz.UTC.localize(timestamp)
                print(f"DEBUG LOG: Время с UTC: {utc_time}")

                # Конвертируем в часовой пояс пользователя
                local_time = utc_time.astimezone(user_tz)
                print(f"DEBUG LOG: Локальное время пользователя: {local_time}")
            except Exception as e:
                print(f"DEBUG LOG: Ошибка конвертации: {e}")
                local_time = timestamp
        else:
            local_time = timestamp
            print(f"DEBUG LOG: Используется время без конвертации")

        # Форматируем дату и время
        date_str = local_time.strftime("%d.%m.%Y")
        time_str = local_time.strftime("%H:%M:%S")
        print(f"DEBUG LOG: Форматированное время: {date_str} {time_str}")

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