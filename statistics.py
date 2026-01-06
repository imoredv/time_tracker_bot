"""
Функции для работы со статистикой..
"""

from datetime import datetime, timedelta
from database import (
    get_hourly_activity_stats,
    get_total_stats_by_activity,
    get_current_activity,
    get_daily_stats_sorted,
    get_user_current_date,
    get_period_stats
)
from config import ACTIVITIES
from utils import (
    get_activity_emoji,
    generate_activity_graph_with_dates,
    generate_bar_graph_period,
    format_duration_for_statistics, generate_week_bar_graph
)


async def get_daily_statistics(user_id):
    """
    Полная статистика за день: графики + за 24 часа + с начала суток.
    """
    try:
        # Получаем сегодняшнюю дату в часовом поясе пользователя
        today_date = get_user_current_date(user_id)

        # Статистика за 2 дня для графиков (вчера и позавчера)
        hourly_stats_with_dates = get_hourly_activity_stats(user_id, 2)

        # Статистика за 24 часа
        activity_stats_24h = get_total_stats_by_activity(user_id, 1)

        # Статистика с начала суток (используем сегодняшнюю дату с учетом часового пояса)
        stats_today = get_daily_stats_sorted(user_id, today_date)

        # Текущая активность
        current = get_current_activity(user_id)

        # Форматирование
        message_text = "📊 Суточная статистика:\n\n"

        # График активности за 2 дня
        if hourly_stats_with_dates:
            timeline_graph = generate_activity_graph_with_dates(hourly_stats_with_dates, 2)
            if timeline_graph and timeline_graph.strip():
                message_text += timeline_graph
                message_text += "\n\n"
        else:
            print(f"DEBUG: No hourly stats available")

        # Статистика за 24 часа
        message_text += "За 24 часа:\n\n"

        # Фильтруем активности больше 1 минуты для 24 часов
        filtered_24h = [(act_type, duration) for act_type, duration in activity_stats_24h if duration >= 60]

        # Формируем бар-граф для отфильтрованных активностей (без пометки текущей активности)
        if filtered_24h:
            bar_graph_24h = generate_bar_graph_period(filtered_24h, None)  # Передаем None чтобы убрать зеленую точку
            if bar_graph_24h:
                message_text += bar_graph_24h
        else:
            message_text += "Нет данных за 24 часа"

        message_text += "\n\n"

        # Статистика с начала суток
        message_text += "Сегодня:\n\n"

        # Фильтруем активности больше 1 минуты для сегодня
        filtered_today = [(act_type, duration) for act_type, duration in stats_today if duration >= 60]

        if filtered_today:
            bar_graph_today = generate_bar_graph_period(filtered_today, user_id)
            if bar_graph_today:
                message_text += bar_graph_today
            else:
                message_text += "Нет данных за сегодня"
        else:
            message_text += "Нет данных за сегодня"

        # Добавляем список незадействованных активностей с ❌
        unused_activities = []
        for act_type in ACTIVITIES.keys():
            # Проверяем, есть ли активность в статистике сегодня (больше 1 минуты)
            found = False
            for act_type_stat, duration in stats_today:
                if act_type_stat == act_type and duration >= 60:
                    found = True
                    break

            if not found:
                name = ACTIVITIES.get(act_type, act_type)
                unused_activities.append(name)

        if unused_activities:
            message_text += "\n\n❌ " + ", ".join(unused_activities)

        return message_text

    except Exception as e:
        print(f"❌ Ошибка в get_daily_statistics: {e}")
        import traceback
        traceback.print_exc()
        return "⚠️ Произошла ошибка при получении статистики. Попробуйте позже."


async def get_week_statistics(user_id):
    """
    Статистика за неделю.
    """
    hourly_stats = get_hourly_activity_stats(user_id, 7)
    activity_stats = get_total_stats_by_activity(user_id, 7)
    current = get_current_activity(user_id)

    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 7)

    # Фильтруем активности больше 1 минуты
    filtered_stats = [(act_type, duration) for act_type, duration in activity_stats if duration >= 60]

    # Используем новую функцию для недельного графика
    bar_graph = generate_week_bar_graph(filtered_stats, user_id)

    total_seconds = sum(duration for _, duration in filtered_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    message_text = "📅 Статистика за неделю:\n\n"

    if current:
        activity_type, start_time = current
        start_time_dt = datetime.fromisoformat(start_time)
        current_duration = int((datetime.now() - start_time_dt).total_seconds())
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        # Форматируем текущую активность как часы:минуты
        hours_curr = current_duration // 3600
        minutes_curr = (current_duration % 3600) // 60

        if hours_curr > 0:
            time_str = f"{hours_curr}ч:{minutes_curr:02d}м"
        else:
            time_str = f"{minutes_curr}м"

        message_text += f"Текущая: {emoji} {activity_name} {time_str}\n\n"
    else:
        message_text += "Текущая: Нет активной задачи\n\n"

    if timeline_graph and timeline_graph.strip():
        message_text += timeline_graph
        message_text += "\n\n"

    message_text += "Рейтинг:\n\n"

    if bar_graph:
        message_text += bar_graph
    else:
        message_text += "Нет данных об активностях\n"

    return message_text


async def get_month_statistics(user_id):
    """
    Статистика за месяц (30 дней).
    """
    hourly_stats = get_hourly_activity_stats(user_id, 30)
    activity_stats = get_total_stats_by_activity(user_id, 30)
    current = get_current_activity(user_id)

    # Для месяца показываем только последние 7 дней в графике
    recent_hourly_stats = hourly_stats[-7:] if len(hourly_stats) > 7 else hourly_stats
    timeline_graph = generate_activity_graph_with_dates(recent_hourly_stats, min(7, len(recent_hourly_stats)))

    # Фильтруем активности больше 1 минуты
    filtered_stats = [(act_type, duration) for act_type, duration in activity_stats if duration >= 60]
    bar_graph = generate_bar_graph_period(filtered_stats, user_id)

    message_text = "📅 Статистика за месяц:\n\n"

    if current:
        activity_type, start_time = current
        start_time_dt = datetime.fromisoformat(start_time)
        current_duration = int((datetime.now() - start_time_dt).total_seconds())
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)
        time_str = format_duration_for_statistics(current_duration)
        message_text += f"Текущая: {emoji} {activity_name} {time_str}\n\n"
    else:
        message_text += "Текущая: Нет активной задачи\n\n"

    if timeline_graph and timeline_graph.strip():
        message_text += timeline_graph
        message_text += "\n\n"

    message_text += "Рейтинг за месяц:\n\n"

    if bar_graph:
        message_text += bar_graph
    else:
        message_text += "Нет данных об активностях\n"

    return message_text


async def get_year_statistics(user_id):
    """
    Статистика за год.
    """
    activity_stats = get_period_stats(user_id, 365)
    current = get_current_activity(user_id)

    # Фильтруем активности больше 1 минуты
    filtered_stats = [(act_type, duration) for act_type, duration in activity_stats if duration >= 60]
    bar_graph = generate_bar_graph_period(filtered_stats, user_id)

    message_text = "📊 Статистика за год:\n\n"

    if current:
        activity_type, start_time = current
        start_time_dt = datetime.fromisoformat(start_time)
        current_duration = int((datetime.now() - start_time_dt).total_seconds())
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)
        time_str = format_duration_for_statistics(current_duration)
        message_text += f"Текущая: {emoji} {activity_name} {time_str}\n\n"
    else:
        message_text += "Текущая: Нет активной задачи\n\n"

    message_text += "Рейтинг за год:\n\n"

    if bar_graph:
        message_text += bar_graph
    else:
        message_text += "Нет данных об активностях\n"

    return message_text