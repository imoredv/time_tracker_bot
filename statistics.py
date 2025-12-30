"""
Функции для работы со статистикой
"""

from datetime import datetime
from database import (
    get_hourly_activity_stats,
    get_total_stats_by_activity,
    get_current_activity,
    get_daily_stats_sorted,
    get_user_current_date
)
from config import ACTIVITIES
from utils import (
    get_activity_emoji,
    format_duration_simple,
    generate_activity_graph_with_dates,
    generate_bar_graph_period
)


async def get_daily_statistics(user_id):
    """
    Полная статистика за день: графики + за 24 часа + с начала суток.
    """
    # Получаем сегодняшнюю дату в часовом поясе пользователя
    today_date = get_user_current_date(user_id)

    # Статистика за 2 дня для графиков
    hourly_stats = get_hourly_activity_stats(user_id, 2)

    # Статистика за 24 часа
    activity_stats_24h = get_total_stats_by_activity(user_id, 1)

    # Статистика с начала суток
    stats_today = get_daily_stats_sorted(user_id, today_date)

    # Текущая активность (не показываем здесь, покажем в кнопке "Назад")
    current = get_current_activity(user_id)

    # Форматирование
    message_text = "📊 Суточная статистика:\n\n"

    # УБИРАЕМ блок с текущей активностью здесь

    # График активности за 2 дня
    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 2)
    if timeline_graph and timeline_graph.strip():
        message_text += timeline_graph
        message_text += "\n\n"

    # Статистика за 24 часа
    message_text += "За последние 24 часа:\n\n"
    bar_graph_24h = generate_bar_graph_period(activity_stats_24h, user_id)
    if bar_graph_24h:
        # Подсчитываем общее время за 24 часа
        total_seconds_24h = sum(duration for _, duration in activity_stats_24h)
        hours_24h = total_seconds_24h // 3600
        minutes_24h = (total_seconds_24h % 3600) // 60
        seconds_24h = total_seconds_24h % 60

        message_text += bar_graph_24h
        message_text += f"\n\n📈 Всего за 24 часа: {hours_24h:02d}:{minutes_24h:02d}:{seconds_24h:02d}"
    else:
        message_text += "Нет данных за 24 часа"

    message_text += "\n\n"

    # Статистика с начала суток
    message_text += "С начала суток:\n\n"
    bar_graph_today = generate_bar_graph_period(stats_today, user_id)
    if bar_graph_today:
        # Подсчитываем общее время за сегодня
        total_seconds_today = sum(duration for _, duration in stats_today)
        hours_today = total_seconds_today // 3600
        minutes_today = (total_seconds_today % 3600) // 60
        seconds_today = total_seconds_today % 60

        message_text += bar_graph_today
        message_text += f"\n\n📈 Всего за сегодня: {hours_today:02d}:{minutes_today:02d}:{seconds_today:02d}"
    else:
        message_text += "Нет данных за сегодня\n"

    return message_text


async def get_week_statistics(user_id):
    """
    Статистика за неделю.
    """
    hourly_stats = get_hourly_activity_stats(user_id, 7)
    activity_stats = get_total_stats_by_activity(user_id, 7)
    current = get_current_activity(user_id)

    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 7)
    bar_graph = generate_bar_graph_period(activity_stats, user_id)

    total_seconds = sum(duration for _, duration in activity_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📅 Статистика за неделю:\n\n"

    # УБИРАЕМ блок с текущей активностью здесь

    if timeline_graph and timeline_graph.strip():
        message_text += timeline_graph
        message_text += "\n\n"

    message_text += "Рейтинг:\n\n"

    if bar_graph:
        message_text += bar_graph
        message_text += f"\n\n📈 Показано за неделю: {hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        message_text += "Нет данных об активностях\n"

    return message_text


async def get_week_statistics(user_id):
    """
    Статистика за неделю.
    """
    hourly_stats = get_hourly_activity_stats(user_id, 7)
    activity_stats = get_total_stats_by_activity(user_id, 7)
    current = get_current_activity(user_id)

    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 7)
    bar_graph = generate_bar_graph_period(activity_stats, user_id)

    total_seconds = sum(duration for _, duration in activity_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📅 Статистика за неделю:\n\n"

    if current:
        activity_type, start_time = current
        start_time_dt = datetime.fromisoformat(start_time)
        current_duration = int((datetime.now() - start_time_dt).total_seconds())
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)
        message_text += f"Текущая: {emoji} {activity_name} {format_duration_simple(current_duration)}\n\n"
    else:
        message_text += "Текущая: Нет активной задачи\n\n"

    if timeline_graph and timeline_graph.strip():
        message_text += timeline_graph
        message_text += "\n\n"

    message_text += "Рейтинг:\n\n"

    if bar_graph:
        message_text += bar_graph
        message_text += f"\n\n📈 Показано за неделю: {hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        message_text += "Нет данных об активностях\n"

    return message_text