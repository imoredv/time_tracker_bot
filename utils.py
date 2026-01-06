"""
Вспомогательные функции с поддержкой часовых поясов.
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
    """Форматирование времени с явным указанием единиц."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds_remain = seconds % 60

    if hours > 0:
        # Часы:минуты (например: 2:15ч)
        return f"{hours}:{minutes:02d}ч"
    elif minutes > 0:
        # Минуты:секунды (например: 14:42с)
        return f"{minutes:02d}:{seconds_remain:02d}с"
    else:
        # Только секунды
        return f"{seconds_remain}с"


def format_duration_for_statistics(seconds):
    """Форматирование времени для статистики (часы:минуты в формате ЧЧч:ММм)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        # Часы:минуты (например: 8ч:36м)
        return f"{hours}ч:{minutes:02d}м"
    else:
        # Только минуты (например: 24м)
        return f"{minutes}м"


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
            return f"{hours}ч {minutes}м"
        else:
            return f"{hours}ч"


def get_user_local_time(user_id):
    """Получение локального времени пользователя."""
    timezone_str = get_user_timezone(user_id)

    try:
        # Используем pytz для получения времени в указанном часовом поясе
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


def generate_activity_graph_with_dates(days_stats_with_dates, days=1):
    """
    Генерация графиков активности с полными датами в формате ДД.ММ.ГГГГ.
    Теперь получает список кортежей (дата, статистика) с 24 часовыми интервалами.
    Выводится одна строка из 24 символов на день.
    """
    if not days_stats_with_dates or days <= 0:
        return ""

    graph_lines = []

    for day_date, day_stats in days_stats_with_dates:
        # Проверяем, есть ли активность в этом дне
        day_has_activity = False
        for activity_type, seconds in day_stats:
            if seconds > 0 and activity_type != 'rest':
                day_has_activity = True
                break

        if not day_has_activity:
            continue

        # Форматируем дату в формате ДД.ММ.ГГГГ
        date_str = day_date.strftime("%d.%m.%Y")
        graph_lines.append(date_str)

        # Создаем график из 24 символов (каждый символ = 1 час)
        timeline = ""
        for i in range(24):
            activity_type, seconds = day_stats[i]
            if seconds > 0:
                if activity_type == 'sleep':
                    timeline += '▁'
                else:
                    symbol = ACTIVITY_SYMBOLS.get(activity_type, '▂')
                    timeline += symbol
            else:
                timeline += '▁'

        graph_lines.append(timeline)

    return "\n".join(graph_lines)


def generate_bar_graph_period(activity_stats, user_id=None):
    """Генерация столбчатой диаграммы для статистики.
    Теперь каждый символ █ = 30 минут (1800 секунд) активности."""
    if not activity_stats:
        return ""

    # Получаем текущую активность
    current_activity = None
    if user_id:
        current = get_current_activity(user_id)
        if current:
            current_activity = current[0]

    # Фильтруем и сортируем
    filtered_stats = [(atype, duration) for atype, duration in activity_stats if duration >= 60]
    if not filtered_stats:
        return ""

    sorted_stats = sorted(filtered_stats, key=lambda x: x[1], reverse=True)

    lines = []

    # НЕ используем максимальное время для пропорции
    # Вместо этого: 1 символ = 30 минут (1800 секунд)
    SECONDS_PER_BLOCK = 1800  # 30 минут в секундах

    for i, (activity_type, seconds) in enumerate(sorted_stats):
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        # Форматируем время с явными единицами
        time_str = format_duration_for_statistics(seconds)

        # Определяем, текущая ли это активность
        is_current = user_id and activity_type == current_activity

        # Строка: эмодзи, название, время и зеленая точка если текущая
        activity_line = f"{emoji} {activity_name} {time_str}"
        if is_current:
            activity_line += " 🟢"
        lines.append(activity_line)

        # Строка с бар-графом
        # Количество полных блоков по 30 минут
        num_full_blocks = seconds // SECONDS_PER_BLOCK

        # Остаток для определения частичного блока
        remainder = seconds % SECONDS_PER_BLOCK

        # Если есть хотя бы 15 минут (половина блока) - добавляем частичный блок
        has_half_block = remainder >= 900  # 15 минут = 900 секунд

        if num_full_blocks == 0:
            if seconds > 0:
                # Меньше 30 минут, но больше 0
                if has_half_block and seconds >= 900:
                    bar_line = "▌"  # Половина блока для >15 минут
                elif seconds >= 60:  # Хотя бы 1 минута
                    bar_line = "▌"  # Маленький блок
                else:
                    bar_line = ""  # Слишком мало
            else:
                bar_line = ""
        else:
            bar_line = "█" * num_full_blocks
            if has_half_block:
                bar_line += "▌"  # Добавляем половину блока

        lines.append(bar_line if bar_line else "▌")

    return "\n".join(lines)


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


def generate_week_bar_graph(activity_stats, user_id=None):
    """Генерация столбчатой диаграммы для недельной статистики.
    Каждая шкала имеет максимальную длину 24 символа (████████████████████████).
    Длина шкалы = процент от максимального времени за неделю."""
    if not activity_stats:
        return ""

    # Получаем текущую активность
    current_activity = None
    if user_id:
        current = get_current_activity(user_id)
        if current:
            current_activity = current[0]

    # Фильтруем и сортируем
    filtered_stats = [(atype, duration) for atype, duration in activity_stats if duration >= 60]
    if not filtered_stats:
        return ""

    sorted_stats = sorted(filtered_stats, key=lambda x: x[1], reverse=True)

    lines = []

    # Максимальное время за неделю для процентного соотношения
    max_duration = sorted_stats[0][1] if sorted_stats else 1
    MAX_BAR_LENGTH = 24  # Максимальная длина шкалы

    for i, (activity_type, seconds) in enumerate(sorted_stats):
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        # Форматируем время с явными единицами (часы:минуты)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        if hours > 0:
            time_str = f"{hours}ч:{minutes:02d}м"
        else:
            time_str = f"{minutes}м"

        # Определяем, текущая ли это активность
        is_current = user_id and activity_type == current_activity

        # Строка: эмодзи, название, время и зеленая точка если текущая
        activity_line = f"{emoji} {activity_name} {time_str}"
        if is_current:
            activity_line += " 🟢"
        lines.append(activity_line)

        # Строка с бар-графом (процент от максимального)
        if max_duration > 0:
            percentage = seconds / max_duration
            bar_length = int(percentage * MAX_BAR_LENGTH)

            # Округляем вверх если есть хотя бы небольшая активность
            if bar_length == 0 and seconds > 0:
                bar_length = 1

            bar_line = "█" * bar_length
        else:
            bar_line = ""

        lines.append(bar_line if bar_line else "▌")

    return "\n".join(lines)