"""
Вспомогательные функции.
"""

from config import ACTIVITIES
from database import get_current_activity

def get_activity_emoji(activity_type):
    """
    Эмодзи для активности (по умолчанию).
    """
    emojis = {
        'work': '💼',
        'study': '📚',
        'sport': '🏃',
        'hobby': '🎨',
        'sleep': '💤',
        'rest': '☕️'
    }
    return emojis.get(activity_type, '⏱️')

def format_duration_simple(seconds):
    """
    Форматирование времени.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours} час {minutes} мин {seconds} сек"
    elif minutes > 0:
        return f"{minutes} мин {seconds} сек"
    else:
        return f"{seconds} сек"

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

    for activity_type, duration in stats:
        # Используем стандартное название для статистики
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        if hours > 0:
            duration_str = f"{hours} час {minutes} мин {seconds} сек"
        elif minutes > 0:
            duration_str = f"{minutes} мин {seconds} сек"
        else:
            duration_str = f"{seconds} сек"

        # Добавляем пометку, если это текущая активность
        if activity_type == current_activity:
            message += f"{emoji} {activity_name}: {duration_str} ⏱️\n"
        else:
            message += f"{emoji} {activity_name}: {duration_str}\n"

        total_seconds += duration

    # Итог
    total_hours = total_seconds // 3600
    total_minutes = (total_seconds % 3600) // 60
    total_seconds = total_seconds % 60

    if total_hours > 0:
        total_str = f"{total_hours} час {total_minutes} мин {total_seconds} сек"
    elif total_minutes > 0:
        total_str = f"{total_minutes} мин {total_seconds} сек"
    else:
        total_str = f"{total_seconds} сек"

    # Добавляем информацию о текущей активности
    if current_activity:
        current_name = ACTIVITIES.get(current_activity, current_activity)
        message += f"\n⏱️ Текущая активность: {current_name}"

    message += f"\n📈 Всего: {total_str}"
    return message

def format_interval(seconds):
    """
    Форматирование интервала.
    """
    if seconds == 0:
        return "Выкл"
    elif seconds < 60:
        return f"{seconds} секунд"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} минут"
    else:
        hours = seconds // 3600
        return f"{hours} часов"