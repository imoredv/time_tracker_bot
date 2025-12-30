"""
Вспомогательные функции с поддержкой часовых поясов
"""

import pytz
from datetime import datetime, timedelta
from config import ACTIVITIES, ACTIVITY_EMOJIS, ACTIVITY_SYMBOLS
from database import get_current_activity, get_user_timezone
from timezone_manager import timezone_manager


def get_activity_emoji(activity_type):
    """Эмодзи для активности."""
    return ACTIVITY_EMOJIS.get(activity_type, '⏱️')


def format_duration_simple(seconds):
    """Форматирование времени."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif minutes > 0:
        return f"{minutes:02d}:{seconds:02d}"
    else:
        return f"{seconds:02d} сек"


def format_interval(seconds):
    """Форматирование интервала."""
    if seconds == 0:
        return "Выкл"
    elif seconds == 5:
        return "5 секунд"
    elif seconds < 60:
        return f"{seconds} секунд"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} минут"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} час {minutes} мин"
        else:
            return f"{hours} часов"


def get_user_local_time(user_id):
    """Получение локального времени пользователя."""
    timezone_str = get_user_timezone(user_id)

    try:
        # Используем pytz для получения времени в указанном часовом поясе
        # Нам нужно преобразовать код часового пояса в формат pytz

        # Маппинг кодов часовых поясов на реальные таймзоны pytz
        tz_mapping = {
            # Россия и СНГ
            'Russian Standard Time': 'Europe/Moscow',  # UTC+3
            'FLE Standard Time': 'Europe/Kiev',  # UTC+2
            'Belarus Standard Time': 'Europe/Minsk',  # UTC+3
            'Ekaterinburg Standard Time': 'Asia/Yekaterinburg',  # UTC+5
            'West Asia Standard Time': 'Asia/Yekaterinburg',  # UTC+5 (Екатеринбург)
            'Central Asia Standard Time': 'Asia/Almaty',  # UTC+6
            'SE Asia Standard Time': 'Asia/Bangkok',  # UTC+7
            'China Standard Time': 'Asia/Shanghai',  # UTC+8
            'Tokyo Standard Time': 'Asia/Tokyo',  # UTC+9
            'Vladivostok Standard Time': 'Asia/Vladivostok',  # UTC+10
            'Magadan Standard Time': 'Asia/Magadan',  # UTC+11

            # Европа
            'GMT Standard Time': 'Europe/London',  # UTC+0
            'W. Europe Standard Time': 'Europe/Berlin',  # UTC+1
            'Romance Standard Time': 'Europe/Paris',  # UTC+1
            'Central Europe Standard Time': 'Europe/Prague',  # UTC+1

            # Америка
            'Eastern Standard Time': 'America/New_York',  # UTC-5
            'Central Standard Time': 'America/Chicago',  # UTC-6
            'Mountain Standard Time': 'America/Denver',  # UTC-7
            'Pacific Standard Time': 'America/Los_Angeles',  # UTC-8

            # Другие
            'UTC': 'UTC',
            'UTC-11': 'Etc/GMT+11',
            'UTC-10': 'Etc/GMT+10',
            'UTC-9': 'Etc/GMT+9',
            'UTC-8': 'Etc/GMT+8',
            'UTC-7': 'Etc/GMT+7',
            'UTC-6': 'Etc/GMT+6',
            'UTC-5': 'Etc/GMT+5',
            'UTC-4': 'Etc/GMT+4',
            'UTC-3': 'Etc/GMT+3',
            'UTC-2': 'Etc/GMT+2',
            'UTC-1': 'Etc/GMT+1',
            'UTC+0': 'Etc/GMT',
            'UTC+1': 'Etc/GMT-1',
            'UTC+2': 'Etc/GMT-2',
            'UTC+3': 'Etc/GMT-3',
            'UTC+4': 'Etc/GMT-4',
            'UTC+5': 'Etc/GMT-5',
            'UTC+6': 'Etc/GMT-6',
            'UTC+7': 'Etc/GMT-7',
            'UTC+8': 'Etc/GMT-8',
            'UTC+9': 'Etc/GMT-9',
            'UTC+10': 'Etc/GMT-10',
            'UTC+11': 'Etc/GMT-11',
            'UTC+12': 'Etc/GMT-12',
        }

        # Ищем соответствующий часовой пояс
        pytz_tz = tz_mapping.get(timezone_str, 'UTC')
        tz = pytz.timezone(pytz_tz)
        return datetime.now(tz)
    except Exception as e:
        print(f"Ошибка получения локального времени для {timezone_str}: {e}")
        return datetime.now()


def format_user_local_time(user_id):
    """Форматирование локального времени пользователя."""
    local_time = get_user_local_time(user_id)
    timezone_str = get_user_timezone(user_id)

    try:
        # Получаем смещение от UTC
        tz = local_time.tzinfo
        if tz:
            offset = tz.utcoffset(local_time)
            if offset:
                total_seconds = offset.total_seconds()
                hours = int(total_seconds // 3600)

                # Форматируем смещение
                if hours >= 0:
                    offset_str = f"UTC+{hours}"
                else:
                    offset_str = f"UTC{hours}"
            else:
                offset_str = "UTC+0"
        else:
            offset_str = "UTC+0"

        return f"{local_time.strftime('%H:%M')} ({offset_str})"
    except Exception as e:
        print(f"Ошибка форматирования времени: {e}")
        return f"{local_time.strftime('%H:%M')} (UTC+0)"


def get_timezone_display_name(timezone_str):
    """Получение отображаемого имени часового пояса."""
    return timezone_manager.get_timezone_display_name(timezone_str)


def format_all_settings(user_id):
    """Форматирование всех настроек пользователя."""
    from database import get_user_settings

    settings = get_user_settings(user_id)
    if not settings:
        return "Настройки не найдены"

    timezone_str = get_user_timezone(user_id)
    timezone_display = get_timezone_display_name(timezone_str)

    interval = settings['reminder_interval']
    interval_text = format_interval(interval)

    return f"""⚙️ Все настройки:

⏰ Напоминания: {'✅ Вкл' if settings['notifications_enabled'] else '❌ Выкл'}
📅 Интервал: {interval_text}

🌙 Тихий час: {'✅ Вкл' if settings['quiet_time_enabled'] else '❌ Выкл'}
🕘 Начало: {settings['quiet_time_start']}
🕖 Конец: {settings['quiet_time_end']}

🌍 Часовой пояс: {timezone_display}
🕒 Локальное время: {format_user_local_time(user_id)}
"""


def generate_activity_graph_with_dates(stats_by_hour, days=1):
    """Генерация графиков активности с датами."""
    if not stats_by_hour or days <= 0:
        return ""

    graph_lines = []

    # Проверяем, есть ли активность
    has_activity = False
    for day_stats in stats_by_hour:
        for activity_type, seconds in day_stats:
            if seconds > 0 and activity_type != 'rest':
                has_activity = True
                break
        if has_activity:
            break

    if not has_activity:
        return ""

    current_date = datetime.now().date()

    for day_idx, day_stats in enumerate(stats_by_hour):
        day_date = current_date - timedelta(days=days - 1 - day_idx)

        # Проверяем активность в дне
        day_has_activity = False
        for activity_type, seconds in day_stats:
            if seconds > 0 and activity_type != 'rest':
                day_has_activity = True
                break

        if not day_has_activity:
            continue

        # Добавляем дату
        date_str = day_date.strftime("%d.%m.%Y")
        graph_lines.append(date_str)

        # Создаем график
        line1 = ""
        for i in range(24):
            activity_type, seconds = day_stats[i]
            if seconds > 0:
                if activity_type == 'sleep':
                    line1 += '▁'
                else:
                    symbol = ACTIVITY_SYMBOLS.get(activity_type, '▂')
                    line1 += symbol
            else:
                line1 += '▁'

        line2 = ""
        for i in range(24, 48):
            activity_type, seconds = day_stats[i]
            if seconds > 0:
                if activity_type == 'sleep':
                    line2 += '▁'
                else:
                    symbol = ACTIVITY_SYMBOLS.get(activity_type, '▂')
                    line2 += symbol
            else:
                line2 += '▁'

        graph_lines.append(line1)
        graph_lines.append(line2)

    return "\n".join(graph_lines)


def generate_bar_graph_period(activity_stats, user_id=None):
    """Генерация столбчатой диаграммы для статистики."""
    if not activity_stats:
        return ""

    # Получаем текущую активность
    current_activity = None
    if user_id:
        current = get_current_activity(user_id)
        if current:
            current_activity = current[0]

    # Фильтруем и сортируем
    filtered_stats = [(atype, duration) for atype, duration in activity_stats if duration > 0]
    if not filtered_stats:
        return ""

    sorted_stats = sorted(filtered_stats, key=lambda x: x[1], reverse=True)

    bars = []

    # Находим максимальное время
    max_duration = sorted_stats[0][1] if sorted_stats else 1

    for activity_type, seconds in sorted_stats:
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        # Рассчитываем ширину
        width_fraction = seconds / max_duration
        width = int(width_fraction * 12)

        if width == 0 and seconds > 0:
            if width_fraction >= 0.04:
                width = 1
            else:
                width = 0

        if width == 0:
            bar = "▌"
        else:
            bar = "█" * width

        # Форматируем время
        total_hours = seconds // 3600
        total_minutes = (seconds % 3600) // 60
        total_seconds = seconds % 60

        # Добавляем пометку текущей активности
        if activity_type == current_activity:
            bars.append(f"{bar} {emoji} {activity_name} {total_hours:02d}:{total_minutes:02d}:{total_seconds:02d} 🟢")
        else:
            bars.append(f"{bar} {emoji} {activity_name} {total_hours:02d}:{total_minutes:02d}:{total_seconds:02d}")

    return "\n".join(bars)


def get_timezone_offset(timezone_code):
    """Получение смещения часового пояса в часах."""
    try:
        # Маппинг кодов на смещения
        offset_mapping = {
            'Russian Standard Time': 3,
            'FLE Standard Time': 2,
            'Belarus Standard Time': 3,
            'Ekaterinburg Standard Time': 5,
            'West Asia Standard Time': 5,
            'Central Asia Standard Time': 6,
            'SE Asia Standard Time': 7,
            'China Standard Time': 8,
            'Tokyo Standard Time': 9,
            'Vladivostok Standard Time': 10,
            'Magadan Standard Time': 11,
            'GMT Standard Time': 0,
            'W. Europe Standard Time': 1,
            'Eastern Standard Time': -5,
            'Central Standard Time': -6,
            'Mountain Standard Time': -7,
            'Pacific Standard Time': -8,
            'UTC': 0,
        }

        # Ищем в основном словаре по частичному совпадению
        for tz_name, offset in offset_mapping.items():
            if tz_name in timezone_code or timezone_code in tz_name:
                return offset

        # Пробуем извлечь из названия часового пояса
        import re
        match = re.search(r'UTC([+-]?\d+)', timezone_code)
        if match:
            return int(match.group(1))

        return 0
    except:
        return 0