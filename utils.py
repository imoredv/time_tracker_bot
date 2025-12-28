"""
Вспомогательные функции с поддержкой часовых поясов.
"""

import pytz
from datetime import datetime, timedelta
from config import ACTIVITIES, ACTIVITY_EMOJIS, ACTIVITY_SYMBOLS
from database import get_current_activity, get_user_timezone
from timezone_manager import timezone_manager

def is_test_interval(interval_seconds):
    """
    Проверка, является ли интервал тестовым (меньше 60 секунд).
    """
    return interval_seconds < 60

def get_activity_emoji(activity_type):
    """
    Эмодзи для активности (по умолчанию).
    """
    return ACTIVITY_EMOJIS.get(activity_type, '⏱️')

def format_duration_simple(seconds):
    """
    Форматирование времени.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif minutes > 0:
        return f"{minutes:02d}:{seconds:02d}"
    else:
        return f"{seconds:02d} сек"

def format_duration_compact(seconds):
    """
    Компактное форматирование времени (чч:мм:сс).
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_stats_message(stats, period_name, user_id=None):
    """
    Форматирование статистики с пометкой текущей активности.
    """
    if not stats:
        return f"{period_name}:\n\nНет данных"

    message = f"{period_name}:\n\n"
    total_seconds = 0

    # Получаем текущую активность для пометки
    current_activity = None
    if user_id:
        current = get_current_activity(user_id)
        if current:
            current_activity = current[0]

    # Сортируем по убыванию времени
    sorted_stats = sorted(stats, key=lambda x: x[1], reverse=True)

    for activity_type, duration in sorted_stats:
        if duration == 0:
            continue  # Пропускаем активности с нулевым временем

        # Используем стандартное название для статистики
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        # Форматируем время в формат ЧЧ:ММ:СС
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        # Добавляем пометку, если это текущая активность
        if activity_type == current_activity:
            message += f"{emoji} {activity_name} {hours:02d}:{minutes:02d}:{seconds:02d} 🟢\n"
        else:
            message += f"{emoji} {activity_name} {hours:02d}:{minutes:02d}:{seconds:02d}\n"

        total_seconds += duration

    # Итог
    total_hours = total_seconds // 3600
    total_minutes = (total_seconds % 3600) // 60
    total_seconds_remainder = total_seconds % 60

    if total_seconds > 0:
        message += f"\n📈 Всего: {total_hours:02d}:{total_minutes:02d}:{total_seconds_remainder:02d}"

    # Добавляем информацию о текущей активности
    if current_activity:
        current_name = ACTIVITIES.get(current_activity, current_activity)
        message += f"\n\n⏱️ Текущая активность: {current_name}"

    return message


def generate_activity_graph(stats_by_hour, days=1):
    """
    Генерация графиков активности за указанное количество дней.
    Каждая строка из 24 символов = 12 часов (1 символ = 30 минут)
    Первая строка: 00:00-12:00
    Вторая строка: 12:00-24:00

    stats_by_hour: список из days элементов, каждый элемент - список из 48 кортежей
                   (activity_type, seconds) для каждого 30-минутного интервала
    days: количество дней

    Возвращает строку с графиком.
    """
    if not stats_by_hour or days <= 0:
        return ""

    graph_lines = []

    # Проверяем, есть ли вообще активность за период
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

    for day_stats in stats_by_hour:
        # Проверяем, есть ли активность в этом дне
        day_has_activity = False
        for activity_type, seconds in day_stats:
            if seconds > 0 and activity_type != 'rest':
                day_has_activity = True
                break

        if not day_has_activity:
            continue

        # Создаем график
        # Первая строка: интервалы 0-23 (00:00-12:00)
        line1 = ""
        for i in range(24):  # Интервалы 0-23
            activity_type, seconds = day_stats[i]
            if seconds > 0:
                if activity_type == 'sleep':
                    line1 += '▁'  # Сон
                else:
                    symbol = ACTIVITY_SYMBOLS.get(activity_type, '▂')
                    line1 += symbol
            else:
                line1 += '▁'  # Отдых или нет активности

        # Вторая строка: интервалы 24-47 (12:00-24:00)
        line2 = ""
        for i in range(24, 48):  # Интервалы 24-47
            activity_type, seconds = day_stats[i]
            if seconds > 0:
                if activity_type == 'sleep':
                    line2 += '▁'  # Сон
                else:
                    symbol = ACTIVITY_SYMBOLS.get(activity_type, '▂')
                    line2 += symbol
            else:
                line2 += '▁'  # Отдых или нет активности

        graph_lines.append(line1)
        graph_lines.append(line2)

    return "\n".join(graph_lines)


def generate_bar_graph(activity_stats, user_id=None, max_width=12):
    """
    Генерация столбчатой диаграммы для статистики по активностям.
    Один символ █ = 1 час активности.

    activity_stats: список кортежей (activity_type, seconds)
    user_id: ID пользователя для определения текущей активности
    max_width: максимальная ширина графика в символах (по умолчанию 12 блоков = 12 часов)

    Возвращает строку с диаграммой.
    """
    if not activity_stats:
        return ""

    # Получаем текущую активность
    current_activity = None
    if user_id:
        current = get_current_activity(user_id)
        if current:
            current_activity = current[0]

    # Фильтруем активности с нулевым временем и сортируем по убыванию
    filtered_stats = [(atype, duration) for atype, duration in activity_stats if duration > 0]
    if not filtered_stats:
        return ""

    sorted_stats = sorted(filtered_stats, key=lambda x: x[1], reverse=True)

    bars = []

    for activity_type, seconds in sorted_stats:
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        # Рассчитываем ширину столбца на основе часов активности
        # Один символ █ = 1 час (3600 секунд)
        hours = seconds / 3600.0  # В часах с дробной частью

        # Рассчитываем ширину
        # Если активность меньше 30 минут (0.5 часа), показываем половинку символа (▌)
        # Если активность от 30 минут до 1 часа, показываем 1 символ (█)
        # Если активность больше 1 часа, показываем целое число часов
        if hours < 0.5:
            # Менее 30 минут - половинка символа
            bar = "▌"
        elif hours < 1:
            # От 30 минут до 1 часа - один символ
            bar = "█"
        else:
            # 1 час и более - целое число символов
            width = int(hours)
            # Если есть остаток более 30 минут, добавляем еще один символ
            if hours - width >= 0.5:
                width += 1

            if width > max_width:
                width = max_width

            bar = "█" * width

        # Форматируем время в ЧЧ:ММ:СС
        total_hours = seconds // 3600
        total_minutes = (seconds % 3600) // 60
        total_seconds = seconds % 60

        # Добавляем зеленый кружок для текущей активности вместо "(Текущая)"
        if activity_type == current_activity:
            bars.append(f"{bar} {emoji} {activity_name} {total_hours:02d}:{total_minutes:02d}:{total_seconds:02d} 🟢")
        else:
            bars.append(f"{bar} {emoji} {activity_name} {total_hours:02d}:{total_minutes:02d}:{total_seconds:02d}")

    return "\n".join(bars)

def format_complete_stats(user_id, days=3):
    """
    Форматирование полной статистики с графиками.
    """
    from database import get_hourly_activity_stats, get_total_stats_by_activity

    # Получаем данные
    hourly_stats = get_hourly_activity_stats(user_id, days)
    activity_stats = get_total_stats_by_activity(user_id, 1)  # Только за сутки для графика

    # Генерируем графики
    timeline_graph = generate_activity_graph(hourly_stats, days)
    bar_graph = generate_bar_graph(activity_stats, user_id)

    # Форматируем сообщение
    message = ""

    if days == 1:
        message += "📊 Статистика за последние 24 часа:\n\n"
    else:
        message += f"📊 Статистика за последние {days} дня:\n\n"

    if timeline_graph and timeline_graph.strip():
        message += "График активности:\n"
        message += timeline_graph
        message += "\n\n"

    message += "За последние сутки:\n\n"
    if bar_graph:
        message += bar_graph
    else:
        message += "Нет данных об активностях\n"

    return message

def format_interval(seconds):
    """
    Форматирование интервала.
    """
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
    """
    Получение локального времени пользователя.
    """
    timezone_str = get_user_timezone(user_id)
    try:
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz)
    except:
        return datetime.now()

def format_user_local_time(user_id):
    """
    Форматирование локального времени пользователя.
    """
    local_time = get_user_local_time(user_id)
    timezone_str = get_user_timezone(user_id)

    # Получаем смещение от UTC
    try:
        tz = pytz.timezone(timezone_str)
        offset = tz.utcoffset(datetime.now())
        hours = int(offset.total_seconds() / 3600)
        offset_str = f"UTC+{hours}" if hours >= 0 else f"UTC{hours}"
    except:
        offset_str = "UTC+3"

    return f"{local_time.strftime('%H:%M')} ({offset_str})"

def get_timezone_display_name(timezone_str):
    """
    Получение отображаемого имени часового пояса.
    """
    for display_name, tz_name in timezone_manager.common_timezones.items():
        if tz_name == timezone_str:
            return display_name
    return timezone_str

def format_timezone_info(user_id):
    """
    Форматирование информации о часовом поясе пользователя.
    """
    timezone_str = get_user_timezone(user_id)
    display_name = get_timezone_display_name(timezone_str)
    local_time = get_user_local_time(user_id)

    return f"🌍 {display_name}\n🕒 {local_time.strftime('%H:%M')}"

def format_all_settings(user_id):
    """
    Форматирование всех настроек пользователя.
    """
    from database import get_user_settings

    settings = get_user_settings(user_id)
    if not settings:
        return "Настройки не найдены"

    timezone_str = get_user_timezone(user_id)
    timezone_display = get_timezone_display_name(timezone_str)

    # Форматируем интервал напоминаний
    interval = settings['reminder_interval']
    if interval == 0:
        interval_text = "Выкл"
    elif interval == 5:
        interval_text = "5 секунд"
    elif interval < 60:
        interval_text = f"{interval} секунд"
    elif interval < 3600:
        interval_text = f"{interval // 60} минут"
    else:
        hours = interval // 3600
        minutes = (interval % 3600) // 60
        if minutes > 0:
            interval_text = f"{hours} час {minutes} мин"
        else:
            interval_text = f"{hours} часов"

    return f"""⚙️ Все настройки:

⏰ Напоминания: {'✅ Вкл' if settings['notifications_enabled'] else '❌ Выкл'}
📅 Интервал: {interval_text}

🌙 Тихий час: {'✅ Вкл' if settings['quiet_time_enabled'] else '❌ Выкл'}
🕘 Начало: {settings['quiet_time_start']}
🕖 Конец: {settings['quiet_time_end']}

🌍 Часовой пояс: {timezone_display}
🕒 Локальное время: {format_user_local_time(user_id)}
"""