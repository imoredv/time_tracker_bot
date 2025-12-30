"""
Time Tracker Bot с поддержкой часовых поясов и новой системой статистики .
Исправленная версия для ботахост.ру
"""

import asyncio
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_ID, ACTIVITIES, DEFAULT_TIMEZONE
from database import (
    init_db, add_user, start_activity, get_current_activity,
    get_daily_stats, get_period_stats, update_user_setting,
    get_user_settings, clear_user_data, get_all_users,
    get_users_for_reminders, update_user_timezone,
    get_user_timezone, get_user_timezone_info, get_timezone_stats,
    get_hourly_activity_stats, get_total_stats_by_activity
)
from keyboards import (
    get_main_keyboard, get_main_keyboard_with_current, get_statistics_keyboard, get_settings_keyboard,
    get_reminder_interval_keyboard, get_quiet_time_keyboard,
    get_clear_confirm_keyboard, get_timezone_keyboard,
    get_timezone_back_keyboard, get_reminder_buttons_keyboard,
    get_activity_reminder_keyboard
)

from utils import (
    get_activity_emoji, format_duration_simple, format_stats_message,
    format_interval, format_timezone_info, get_timezone_display_name,
    format_user_local_time, format_complete_stats, format_all_settings,
    generate_activity_graph_with_dates, generate_bar_graph_period
)

from reminder import ReminderManager
from timezone_manager import timezone_manager

from utils import (
    get_activity_emoji, format_duration_simple, format_stats_message,
    format_interval, format_timezone_info, get_timezone_display_name,
    format_user_local_time, format_complete_stats, format_all_settings,
    generate_activity_graph_with_dates, generate_bar_graph_period
)

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
reminder_manager = ReminderManager(bot)

# Состояния FSM для тихого часа и выбора интервала при смене активности
class EditStates(StatesGroup):
    waiting_for_quiet_start = State()
    waiting_for_quiet_end = State()
    waiting_for_activity_reminder = State()  # Новое состояние для выбора интервала при смене активности

# Функция для получения отображаемого названия активности
def get_display_activity(user_id, activity_type):
    """
    Получаем название активности для отображения.
    """
    default_emoji = get_activity_emoji(activity_type)
    default_name = ACTIVITIES.get(activity_type, activity_type)
    return f"{default_emoji} {default_name}"


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    Команда /start с определением часового пояса.
    """
    # СНАЧАЛА пробуем получить часовой пояс из сообщения пользователя
    user_timezone = DEFAULT_TIMEZONE

    # Пробуем определить часовой пояс из информации о пользователе
    try:
        # Если у пользователя есть информация о локации
        if message.from_user.language_code:
            # Маппинг языковых кодов на часовые пояса
            lang_to_timezone = {
                'ru': 'Europe/Moscow',
                'en': 'UTC',
                'uk': 'Europe/Kiev',
                'be': 'Europe/Minsk',
                'de': 'Europe/Berlin',
                'fr': 'Europe/Paris',
                'es': 'Europe/Madrid',
                'it': 'Europe/Rome',
                'zh': 'Asia/Shanghai',
                'ja': 'Asia/Tokyo',
                'ko': 'Asia/Seoul',
                'ar': 'Asia/Riyadh',
                'tr': 'Europe/Istanbul',
                'pt': 'America/Sao_Paulo',
            }

            lang_code = message.from_user.language_code.lower()
            # Берем первые 2 символа языка
            lang_prefix = lang_code[:2] if len(lang_code) >= 2 else lang_code

            if lang_prefix in lang_to_timezone:
                user_timezone = lang_to_timezone[lang_prefix]
                print(f"✅ Определен часовой пояс по языку {lang_code}: {user_timezone}")
            else:
                # Если язык не найден, пробуем по IP
                user_timezone = timezone_manager.detect_by_ip()
                print(f"⚠️ Язык {lang_code} не найден, используем IP: {user_timezone}")
    except Exception as e:
        print(f"⚠️ Ошибка определения часового пояса: {e}")
        user_timezone = timezone_manager.detect_by_ip()

    # Добавляем пользователя с определенным часовым поясом
    add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        timezone=user_timezone
    )

    welcome_text = (
        f"⏱️ Учёт времени\n\n"
        f"Часовой пояс определен как: {get_timezone_display_name(user_timezone)}\n"
        f"Локальное время: {format_user_local_time(message.from_user.id)}\n\n"
        f"Если часовой пояс определен неверно, измените его в ⚙️ Настройки → 🌍 Часовой пояс"
    )

    await message.answer(welcome_text, reply_markup=get_main_keyboard_with_current(message.from_user.id))

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """
    Команда /help.
    """
    help_text = """
📋 <b>Помощь по боту Time Tracker</b>

<b>Основные функции:</b>
• Выберите активность для начала отсчёта времени
• При выборе другой активности, текуная автоматически завершается
• Бот будет спрашивать чем вы заняты с заданным интервалом

<b>Кнопки:</b>
• 💼 Труд, 📚 Учёба, 🏃 Спорт, 🎨 Хобби, 💤 Сон, ☕️ Отдых - выбор активности
• 📊 Статистика - просмотр статистики с графиками
• ⚙️ Настройки - настройка бота

<b>Настройки:</b>
• ⏰ Напоминания - настройка интервала напоминаний (включая тестовый 5 секунд)
• 🌙 Тихий час - время, когда бот не беспокоит
• 🌍 Часовой пояс - настройка вашего часового пояса
• 🗑️ Очистить - удаление всех данных

<b>Статистика:</b>
• 📊 Статистика - графики за последние 3 дня
• 📅 Неделя - статистика за неделю
• 📅 Месяц - статистика за месяц
• 📊 Год - статистика за год

<b>Напоминания:</b>
• Напоминания привязаны к часам (12:15, 12:30, 12:45...)
• Можно выбрать интервал напоминаний в настройках (включая 5 секунд для тестов)
• Можно изменить интервал в ответ на уведомление (10, 30, 60 минут)
• При смене активности можно выбрать интервал уведомлений (10, 30, 60 минут)
• Учитывается тихое время и часовой пояс

⏱️ - обозначает текущую активность
    """
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("timezone"))
async def cmd_timezone(message: Message):
    """
    Команда для проверки часового пояса.
    """
    user_id = message.from_user.id
    timezone_info = get_user_timezone_info(user_id)

    if timezone_info:
        current_time = format_user_local_time(user_id)
        timezone_display = get_timezone_display_name(timezone_info['timezone'])

        response = (
            f"🌍 Ваш часовой пояс:\n"
            f"• {timezone_display}\n"
            f"• Код: {timezone_info['timezone']}\n"
            f"• Локальное время: {current_time}\n\n"
            f"Изменить часовой пояс можно в ⚙️ Настройки → 🌍 Часовой пояс"
        )
    else:
        response = "Не удалось определить ваш часовой пояс. Пожалуйста, используйте /start"

    await message.answer(response)

@dp.message(Command("time"))
async def cmd_time(message: Message):
    """
    Команда для отображения текущего времени.
    """
    user_id = message.from_user.id
    local_time = format_user_local_time(user_id)

    await message.answer(f"🕒 Ваше локальное время: {local_time}")

# Административные команды
@dp.message(Command("test5"))
async def cmd_test5(message: Message):
    """
    Быстрая установка тестового интервала 5 секунд.
    """
    user_id_int = int(message.from_user.id)
    admin_id_int = int(ADMIN_ID)

    if user_id_int != admin_id_int:
        return

    # Устанавливаем интервал 5 секунд
    update_user_setting(user_id_int, 'reminder_interval', 5)
    update_user_setting(user_id_int, 'notifications_enabled', 1)

    # Сбрасываем кэш времени напоминаний для этого пользователя
    for key in list(reminder_manager.user_next_reminder_time.keys()):
        if key.startswith(str(user_id_int)):
            del reminder_manager.user_next_reminder_time[key]

    await message.answer("✅ Установлен тестовый интервал 5 секунд. Напоминания будут приходить каждые 5 секунд.")

@dp.message(Command("test"))
async def cmd_test(message: Message):
    """
    Тест напоминания.
    """
    user_id_int = int(message.from_user.id)
    admin_id_int = int(ADMIN_ID)

    if user_id_int != admin_id_int:
        return

    await reminder_manager.send_test_reminder(message.from_user.id)
    await message.answer("✅ Тестовое напоминание отправлено")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    """
    Статус бота.
    """
    user_id_int = int(message.from_user.id)
    admin_id_int = int(ADMIN_ID)

    if user_id_int != admin_id_int:
        return

    all_users = get_all_users()
    users_for_reminders = get_users_for_reminders()
    timezone_stats = get_timezone_stats()

    status_text = (
        f"🤖 Статус бота:\n\n"
        f"• Всего пользователей: {len(all_users)}\n"
        f"• Пользователей для напоминаний: {len(users_for_reminders)}\n"
        f"• Напоминания: {'✅ Вкл' if reminder_manager.is_running else '❌ Выкл'}\n"
        f"• База данных: ✅ Работает\n"
        f"• Версия: 4.3 (тестовые уведомления 5 секунд + упрощенные интервалы)\n"
        f"• Ваш ID: {user_id_int}\n"
        f"• ADMIN_ID: {admin_id_int}\n\n"
        f"📊 Статистика по часовым поясам:\n"
    )

    for tz, count in timezone_stats:
        tz_display = get_timezone_display_name(tz)
        status_text += f"• {tz_display}: {count} пользователей\n"

    await message.answer(status_text)

@dp.message(Command("users"))
async def cmd_users(message: Message):
    """
    Просмотр списка пользователей.
    """
    user_id_int = int(message.from_user.id)
    admin_id_int = int(ADMIN_ID)

    if user_id_int != admin_id_int:
        return

    all_users = get_all_users()

    if not all_users:
        await message.answer("📭 Нет зарегистрированных пользователей")
        return

    users_text = f"👥 Пользователи бота (всего: {len(all_users)}):\n\n"

    for idx, (user_id, first_name, timezone) in enumerate(all_users, 1):
        name_display = f" ({first_name})" if first_name else ""
        timezone_display = get_timezone_display_name(timezone)
        users_text += f"{idx}. ID: {user_id}{name_display}\n   📍 {timezone_display}\n"

        # Чтобы сообщение не было слишком длинным
        if idx % 10 == 0:
            await message.answer(users_text)
            users_text = ""

    if users_text:
        await message.answer(users_text)

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """
    Подробная статистика по пользователям.
    """
    user_id_int = int(message.from_user.id)
    admin_id_int = int(ADMIN_ID)

    if user_id_int != admin_id_int:
        return

    all_users = get_all_users()

    if not all_users:
        await message.answer("📭 Нет зарегистрированных пользователей")
        return

    # Статистика
    total_users = len(all_users)
    active_now = 0

    for user in all_users:
        user_id = user[0]
        current = get_current_activity(user_id)
        if current:
            active_now += 1

    stats_text = (
        f"📊 Статистика бота:\n\n"
        f"• Всего пользователей: {total_users}\n"
        f"• Активных сейчас: {active_now}\n"
        f"• Неактивных: {total_users - active_now}\n"
        f"• Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    await message.answer(stats_text)


@dp.message(F.text.in_(["💼 Труд", "💼 Труд ✅", "📚 Учёба", "📚 Учёба ✅", "🏃 Спорт", "🏃 Спорт ✅",
                        "🎨 Хобби", "🎨 Хобби ✅", "💤 Сон", "💤 Сон ✅", "☕️ Отдых", "☕️ Отдых ✅"]))
async def handle_activity(message: Message, state: FSMContext):
    """
    Обработчик выбора активности.
    """
    user_id = message.from_user.id

    # Определяем тип активности из текста кнопки
    button_text = message.text
    activity_mapping = {
        "💼 Труд": "work", "💼 Труд ✅": "work",
        "📚 Учёба": "study", "📚 Учёба ✅": "study",
        "🏃 Спорт": "sport", "🏃 Спорт ✅": "sport",
        "🎨 Хобби": "hobby", "🎨 Хобби ✅": "hobby",
        "💤 Сон": "sleep", "💤 Сон ✅": "sleep",
        "☕️ Отдых": "rest", "☕️ Отдых ✅": "rest"
    }

    act_type = activity_mapping.get(button_text, "work")

    # Проверяем, активна ли уже такая же активность
    current = get_current_activity(user_id)
    if current and current[0] == act_type:
        display_text = get_display_activity(user_id, act_type)
        start_time = datetime.fromisoformat(current[1])
        current_time = datetime.now()
        duration = int((current_time - start_time).total_seconds())

        await message.answer(
            f"{display_text} продолжается\n{format_duration_simple(duration)}",
            reply_markup=get_main_keyboard_with_current(user_id)
        )
        return

    # Запускаем новую активность
    completed_activity = start_activity(user_id, act_type)

    response = ""

    if completed_activity:
        completed_type, start_time_str = completed_activity
        display_text = get_display_activity(user_id, completed_type)

        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        response += f"{display_text} стоп\n{format_duration_simple(duration)}\n\n"

    # Новая активность
    display_text = get_display_activity(user_id, act_type)
    response += f"{display_text} старт\n00:00:00\n\n"

    # Предлагаем выбрать интервал уведомлений (только 10, 30, 60 минут)
    response += "📅 Выберите интервал уведомлений для этой активности:"

    # СНАЧАЛА обновляем клавиатуру
    await message.answer(
        "🔄 Обновление меню...",
        reply_markup=get_main_keyboard_with_current(user_id)
    )

    # Потом отправляем запрос на выбор интервала
    await message.answer(
        response,
        reply_markup=get_activity_reminder_keyboard()
    )

    # Сохраняем информацию о активности в состоянии
    await state.update_data(activity_type=act_type)
    await state.set_state(EditStates.waiting_for_activity_reminder)

@dp.message(F.text == "📊 Статистика")
async def handle_statistics(message: Message):
    """
    Статистика за последние 24 часа (2 дня графика + 24 часа распределение).
    """
    user_id = message.from_user.id

    from database import get_hourly_activity_stats, get_total_stats_by_activity, get_current_activity
    from utils import generate_activity_graph_with_dates, generate_bar_graph, format_duration_simple, get_activity_emoji

    # Получаем данные за 2 дня для графика
    hourly_stats = get_hourly_activity_stats(user_id, 2)  # График за 2 дня
    # Получаем статистику именно за последние 24 часа
    activity_stats_24h = get_total_stats_by_activity(user_id, 1)  # Распределение за 24 часа

    # Получаем текущую активность
    current = get_current_activity(user_id)

    # Генерируем графики
    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 2)
    bar_graph = generate_bar_graph(activity_stats_24h, user_id, max_width=12)

    # Общее время за последние 24 часа
    total_seconds = sum(duration for _, duration in activity_stats_24h)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📊 Статистика за последние 24 часа:\n\n"

    # Добавляем текущую активность
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
        message_text += f"\n\n📈 Показано за 24 часа: {hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        message_text += "Нет данных об активностях\n"

    await message.answer(message_text, reply_markup=get_statistics_keyboard())


@dp.message(F.text == "📅 Неделя")
async def handle_week_statistics(message: Message):
    """
    Статистика за неделю (7 дней график + суммирование за неделю).
    """
    user_id = message.from_user.id

    from database import get_hourly_activity_stats, get_total_stats_by_activity, get_current_activity
    from utils import generate_activity_graph_with_dates, generate_bar_graph_period, format_duration_simple, \
        get_activity_emoji

    # Получаем данные за 7 дней
    hourly_stats = get_hourly_activity_stats(user_id, 7)  # График за 7 дней
    activity_stats = get_total_stats_by_activity(user_id, 7)  # Распределение за 7 дней
    current = get_current_activity(user_id)  # Текущая активность

    # Генерируем графики
    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 7)
    bar_graph = generate_bar_graph_period(activity_stats, user_id)

    # Суммарное время за неделю
    total_seconds = sum(duration for _, duration in activity_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📅 Статистика за неделю:\n\n"

    # Добавляем текущую активность
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

    await message.answer(message_text, reply_markup=get_statistics_keyboard())


@dp.message(F.text == "📅 Месяц")
async def handle_month_statistics(message: Message):
    """
    Статистика за месяц (30 дней график + суммирование за месяц).
    """
    user_id = message.from_user.id

    from database import get_hourly_activity_stats, get_total_stats_by_activity, get_current_activity
    from utils import generate_activity_graph_with_dates, generate_bar_graph_period, format_duration_simple, \
        get_activity_emoji

    # Получаем данные за 30 дней
    hourly_stats = get_hourly_activity_stats(user_id, 30)  # График за 30 дней
    activity_stats = get_total_stats_by_activity(user_id, 30)  # Распределение за 30 дней
    current = get_current_activity(user_id)  # Текущая активность

    # Генерируем графики
    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 30)
    bar_graph = generate_bar_graph_period(activity_stats, user_id)

    # Суммарное время за месяц
    total_seconds = sum(duration for _, duration in activity_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📅 Статистика за месяц:\n\n"

    # Добавляем текущую активность
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
        message_text += "График активности:\n"
        # Для месяца показываем только последние 10 дней графика
        lines = timeline_graph.split('\n')
        if len(lines) > 30:  # 10 дней * 3 строки (дата + 2 строки графика)
            message_text += '\n'.join(lines[:30]) + "\n..."
        else:
            message_text += timeline_graph
        message_text += "\n\n"

    message_text += "Рейтинг:\n\n"

    if bar_graph:
        message_text += bar_graph
        message_text += f"\n\n📈 Показано за месяц: {hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        message_text += "Нет данных об активностях\n"

    await message.answer(message_text, reply_markup=get_statistics_keyboard())


@dp.message(F.text == "📊 Год")
async def handle_year_statistics(message: Message):
    """
    Статистика за год (365 дней суммирование).
    """
    user_id = message.from_user.id

    from database import get_hourly_activity_stats, get_total_stats_by_activity, get_current_activity
    from utils import generate_activity_graph_with_dates, generate_bar_graph_period, format_duration_simple, \
        get_activity_emoji

    # Для года показываем график за 30 дней + статистику за год
    hourly_stats = get_hourly_activity_stats(user_id, 30)  # График за 30 дней
    activity_stats = get_total_stats_by_activity(user_id, 365)  # Распределение за год
    current = get_current_activity(user_id)  # Текущая активность

    # Генерируем графики
    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 30)
    bar_graph = generate_bar_graph_period(activity_stats, user_id)

    # Суммарное время за год
    total_seconds = sum(duration for _, duration in activity_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📊 Статистика за год:\n\n"

    # Добавляем текущую активность
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
        message_text += "График активности:\n"
        # Для года показываем только последние 15 дней графика
        lines = timeline_graph.split('\n')
        if len(lines) > 45:  # 15 дней * 3 строки
            message_text += '\n'.join(lines[:45]) + "\n..."
        else:
            message_text += timeline_graph
        message_text += "\n\n"

    message_text += "Рейтинг:\n\n"

    if bar_graph:
        message_text += bar_graph
        message_text += f"\n\n📈 Показано за год: {hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        message_text += "Нет данных об активностях\n"

    await message.answer(message_text, reply_markup=get_statistics_keyboard())

@dp.message(F.text == "⚙️ Настройки")
async def handle_settings(message: Message):
    """
    Настройки - показываем все настройки сразу.
    """
    user_id = message.from_user.id
    settings_text = format_all_settings(user_id)

    await message.answer(settings_text, reply_markup=get_settings_keyboard())

@dp.message(F.text == "🌍 Часовой пояс")
async def handle_timezone(message: Message):
    """
    Настройка часового пояса.
    """
    user_id = message.from_user.id
    current_timezone = get_user_timezone(user_id)
    current_display = get_timezone_display_name(current_timezone)
    current_time = format_user_local_time(user_id)

    message_text = (
        f"🌍 Часовой пояс\n\n"
        f"Текущий: {current_display}\n"
        f"Локальное время: {current_time}\n\n"
        f"Выберите новый часовой пояс:"
    )

    await message.answer(message_text, reply_markup=get_timezone_keyboard())


@dp.message(F.text == "🌍 Автоопределение")
async def handle_auto_timezone(message: Message):
    """
    Автоопределение часового пояса.
    """
    user_id = message.from_user.id

    try:
        # Пробуем определить по IP
        auto_timezone = timezone_manager.detect_by_ip(force_refresh=True)  # Принудительно обновляем

        # Проверяем, популярный ли это часовой пояс для пользователей
        popular_timezones = [
            'Europe/Moscow', 'Europe/Kiev', 'Europe/Minsk',
            'Asia/Yekaterinburg', 'Asia/Novosibirsk', 'Asia/Krasnoyarsk',
            'Europe/London', 'America/New_York', 'Europe/Berlin',
            'Europe/Paris', 'Europe/Madrid'
        ]

        timezone_display = get_timezone_display_name(auto_timezone)
        local_time = format_user_local_time(user_id)

        # Если часовой пояс популярный - используем его
        if auto_timezone in popular_timezones:
            update_user_timezone(user_id, auto_timezone)

            response = (
                f"✅ Часовой пояс обновлен!\n\n"
                f"• {timezone_display}\n"
                f"• Локальное время: {local_time}"
            )

            await message.answer(response, reply_markup=get_settings_keyboard())
        else:
            # Если часовой пояс не популярный, предлагаем выбрать вручную
            response = (
                f"Определен часовой пояс: {timezone_display}\n"
                f"Локальное время: {local_time}\n\n"
                f"Это ваш часовой пояс? Если нет, выберите вручную:"
            )

            # Создаем клавиатуру с кнопкой подтверждения и выбора
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=f"✅ Да, это {timezone_display}")],
                    [KeyboardButton(text="❌ Нет, выбрать другой")],
                    [KeyboardButton(text="⬅️ Назад")]
                ],
                resize_keyboard=True
            )

            await message.answer(response, reply_markup=keyboard)
            # Можно сохранить предложенный часовой пояс в состоянии FSM

    except Exception as e:
        response = f"❌ Не удалось определить часовой пояс: {e}\n\nПожалуйста, выберите вручную:"
        await message.answer(response, reply_markup=get_timezone_keyboard())

# Обработка выбора часового пояса
@dp.message(F.text.in_(list(timezone_manager.common_timezones.keys())))
async def handle_timezone_selection(message: Message):
    """
    Выбор часового пояса из списка.
    """
    user_id = message.from_user.id
    timezone_display = message.text

    # Получаем IANA код часового пояса
    timezone_code = timezone_manager.common_timezones.get(timezone_display, DEFAULT_TIMEZONE)

    # Обновляем часовой пояс
    if update_user_timezone(user_id, timezone_code):
        local_time = format_user_local_time(user_id)

        response = (
            f"✅ Часовой пояс обновлен!\n\n"
            f"• {timezone_display}\n"
            f"• Локальное время: {local_time}"
        )
    else:
        response = "❌ Не удалось обновить часовой пояс"

    await message.answer(response, reply_markup=get_settings_keyboard())

@dp.message(F.text == "⏰ Напоминания")
async def handle_reminders(message: Message):
    """
    Настройка напоминаний.
    """
    user_id = message.from_user.id
    settings = get_user_settings(user_id)

    current_interval = settings['reminder_interval'] if settings else 1800
    notifications_enabled = settings['notifications_enabled'] if settings else True

    interval_text = format_interval(current_interval)
    status_text = "включены" if notifications_enabled else "выключены"

    await message.answer(
        f"⏰ Напоминания\nИнтервал: {interval_text}\nСтатус: {status_text}",
        reply_markup=get_reminder_interval_keyboard(current_interval, notifications_enabled)
    )

@dp.message(F.text == "🌙 Тихий час")
async def handle_quiet_time(message: Message):
    """
    Настройка тихого времени.
    """
    user_id = message.from_user.id
    settings = get_user_settings(user_id)

    quiet_enabled = settings['quiet_time_enabled'] if settings else True
    start_time = settings['quiet_time_start'] if settings else "22:00"
    end_time = settings['quiet_time_end'] if settings else "06:00"

    status_text = "включен" if quiet_enabled else "выключен"

    await message.answer(
        f"🌙 Тихий час\n{start_time} - {end_time}\nСтатус: {status_text}",
        reply_markup=get_quiet_time_keyboard(quiet_enabled, start_time, end_time)
    )

@dp.message(F.text == "🗑️ Очистить")
async def handle_clear_data(message: Message):
    """
    Очистка данных.
    """
    await message.answer(
        "🗑️ Очистить все данные?\nЭто действие нельзя отменить.",
        reply_markup=get_clear_confirm_keyboard()
    )

@dp.message(F.text == "⬅️ Назад")
async def handle_back(message: Message):
    """
    Назад в главное меню.
    """
    await message.answer("Главное меню", reply_markup=get_main_keyboard_with_current(message.from_user.id))

# Обработчики инлайн-кнопок для интервалов в настройках
@dp.callback_query(F.data.startswith("interval_"))
async def handle_interval_callback(callback: CallbackQuery):
    """
    Выбор интервала напоминаний в настройках (включая тестовые 5 секунд).
    """
    user_id = callback.from_user.id
    interval = int(callback.data.split("_")[1])

    if interval == 0:
        update_user_setting(user_id, 'notifications_enabled', 0)
        await callback.message.edit_text(
            "⏰ Напоминания\nИнтервал: Выкл\nСтатус: выключены"
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_reminder_interval_keyboard(interval, False)
        )
    else:
        update_user_setting(user_id, 'reminder_interval', interval)
        update_user_setting(user_id, 'notifications_enabled', 1)

        interval_text = format_interval(interval)
        await callback.message.edit_text(
            f"⏰ Напоминания\nИнтервал: {interval_text}\nСтатус: включены"
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_reminder_interval_keyboard(interval, True)
        )

    await callback.answer(f"Установлено: {format_interval(interval)}")

# Обработчики инлайн-кнопок для напоминаний (быстрая смена интервала)
@dp.callback_query(F.data.startswith("remind_"))
async def handle_reminder_interval_callback(callback: CallbackQuery):
    """
    Выбор интервала напоминания в ответ на уведомление (только 10, 30, 60 минут).
    """
    user_id = callback.from_user.id
    interval_str = callback.data.split("_")[1]

    try:
        interval_minutes = int(interval_str)
        interval_seconds = interval_minutes * 60

        # Обновляем настройки
        update_user_setting(user_id, 'reminder_interval', interval_seconds)
        update_user_setting(user_id, 'notifications_enabled', 1)

        # Сбрасываем кэш времени напоминаний для этого пользователя
        for key in list(reminder_manager.user_next_reminder_time.keys()):
            if key.startswith(str(user_id)):
                del reminder_manager.user_next_reminder_time[key]

        await callback.message.edit_text(
            f"✅ Уведомления установлены на каждые {interval_minutes} минут"
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

# Обработчики инлайн-кнопок для выбора интервала при смене активности
@dp.callback_query(F.data.startswith("activity_remind_"))
async def handle_activity_reminder_callback(callback: CallbackQuery, state: FSMContext):
    """
    Выбор интервала уведомлений при смене активности (только 10, 30, 60 минут).
    """
    user_id = callback.from_user.id
    interval_str = callback.data.split("_")[2]  # activity_remind_10 -> 10

    try:
        interval_minutes = int(interval_str)
        interval_seconds = interval_minutes * 60

        # Обновляем настройки
        update_user_setting(user_id, 'reminder_interval', interval_seconds)
        update_user_setting(user_id, 'notifications_enabled', 1)

        # Сбрасываем кэш времени напоминаний для этого пользователя
        for key in list(reminder_manager.user_next_reminder_time.keys()):
            if key.startswith(str(user_id)):
                del reminder_manager.user_next_reminder_time[key]

        # Получаем информацию о активности из состояния
        data = await state.get_data()
        activity_type = data.get('activity_type', 'work')
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        await callback.message.edit_text(
            f"{emoji} {activity_name}\n00:00:00\n\n✅ Уведомления установлены на каждые {interval_minutes} минут"
        )
        await callback.answer(f"Интервал: {interval_minutes} мин")

        # Очищаем состояние и обновляем главное меню
        await state.clear()

        # Отправляем обновленное главное меню
        await callback.message.answer("Активность запущена", reply_markup=get_main_keyboard_with_current(user_id))

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data == "toggle_notif")
async def handle_toggle_notif(callback: CallbackQuery):
    """
    Переключение уведомлений.
    """
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)

    if settings:
        current_state = settings['notifications_enabled']
        new_state = not current_state

        update_user_setting(user_id, 'notifications_enabled', 1 if new_state else 0)

        # Если выключаем уведомления, очищаем кэш
        if not new_state:
            for key in list(reminder_manager.user_next_reminder_time.keys()):
                if key.startswith(str(user_id)):
                    del reminder_manager.user_next_reminder_time[key]

        current_interval = settings['reminder_interval']

        status_text = "включены" if new_state else "выключены"
        interval_text = format_interval(current_interval)

        await callback.message.edit_text(
            f"⏰ Напоминания\nИнтервал: {interval_text}\nСтатус: {status_text}"
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_reminder_interval_keyboard(current_interval, new_state)
        )

        await callback.answer(f"Уведомления {status_text}")
    await callback.answer()

@dp.callback_query(F.data == "toggle_quiet")
async def handle_toggle_quiet(callback: CallbackQuery):
    """
    Переключение тихого времени.
    """
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)

    if settings:
        current_state = settings['quiet_time_enabled']
        new_state = not current_state

        update_user_setting(user_id, 'quiet_time_enabled', 1 if new_state else 0)

        start_time = settings['quiet_time_start']
        end_time = settings['quiet_time_end']

        status_text = "включен" if new_state else "выключен"

        await callback.message.edit_text(
            f"🌙 Тихий час\n{start_time} - {end_time}\nСтатус: {status_text}"
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_quiet_time_keyboard(new_state, start_time, end_time)
        )

        await callback.answer(f"Тихий час {status_text}")
    await callback.answer()

@dp.callback_query(F.data.in_(["set_quiet_start", "set_quiet_end"]))
async def handle_set_quiet_time(callback: CallbackQuery, state: FSMContext):
    """
    Установка времени для тихого часа.
    """
    time_type = "начала" if callback.data == "set_quiet_start" else "окончания"
    await state.update_data(time_type=callback.data)

    await callback.message.edit_text(
        f"Введите время {time_type} тихого часа (формат ЧЧ:ММ):\n\nПример: 22:00"
    )

    if callback.data == "set_quiet_start":
        await state.set_state(EditStates.waiting_for_quiet_start)
    else:
        await state.set_state(EditStates.waiting_for_quiet_end)

    await callback.answer()

@dp.message(EditStates.waiting_for_quiet_start)
async def handle_quiet_start_input(message: Message, state: FSMContext):
    """
    Обработка ввода времени начала.
    """
    if re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', message.text):
        user_id = message.from_user.id
        update_user_setting(user_id, 'quiet_time_start', message.text)

        settings = get_user_settings(user_id)
        end_time = settings['quiet_time_end'] if settings else "06:00"
        quiet_enabled = settings['quiet_time_enabled'] if settings else True

        status_text = "включен" if quiet_enabled else "выключен"

        await message.answer(
            f"🌙 Тихий час\n{message.text} - {end_time}\nСтатус: {status_text}",
            reply_markup=get_quiet_time_keyboard(quiet_enabled, message.text, end_time)
        )
        await state.clear()
    else:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 22:00)")

@dp.message(EditStates.waiting_for_quiet_end)
async def handle_quiet_end_input(message: Message, state: FSMContext):
    """
    Обработка ввода времени окончания.
    """
    if re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', message.text):
        user_id = message.from_user.id
        update_user_setting(user_id, 'quiet_time_end', message.text)

        settings = get_user_settings(user_id)
        start_time = settings['quiet_time_start'] if settings else "22:00"
        quiet_enabled = settings['quiet_time_enabled'] if settings else True

        status_text = "включен" if quiet_enabled else "выключен"

        await message.answer(
            f"🌙 Тихий час\n{start_time} - {message.text}\nСтатус: {status_text}",
            reply_markup=get_quiet_time_keyboard(quiet_enabled, start_time, message.text)
        )
        await state.clear()
    else:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 06:00)")

@dp.callback_query(F.data == "back_settings")
async def handle_back_settings(callback: CallbackQuery):
    """
    Назад в настройки.
    """
    user_id = callback.from_user.id
    settings_text = format_all_settings(user_id)

    await callback.message.edit_text(settings_text)
    await callback.answer()

@dp.callback_query(F.data.in_(["clear_yes", "clear_no"]))
async def handle_clear_confirm(callback: CallbackQuery):
    """
    Подтверждение удаления данных.
    """
    if callback.data == "clear_yes":
        user_id = callback.from_user.id
        clear_user_data(user_id)
        await callback.message.edit_text("✅ Все данные очищены")
    else:
        await callback.message.edit_text("❌ Очистка отменена")

    await callback.answer()

# Обработка всех остальных сообщений
@dp.message()
@dp.message()
async def handle_other_messages(message: Message):
    """
    Обработка всех остальных сообщений.
    """
    # Если сообщение не начинается с команды и не является кнопкой - игнорируем
    if not message.text.startswith('/'):
        # Проверяем, не является ли это кнопкой из клавиатуры
        if message.text not in [
            "💼 Труд", "💼 Труд ✅", "📚 Учёба", "📚 Учёба ✅",
            "🏃 Спорт", "🏃 Спорт ✅", "🎨 Хобби", "🎨 Хобби ✅",
            "💤 Сон", "💤 Сон ✅", "☕️ Отдых", "☕️ Отдых ✅",
            "📊 Статистика", "⚙️ Настройки", "📅 Неделя", "📅 Месяц", "📊 Год",
            "⏰ Напоминания", "🌙 Тихий час", "🗑️ Очистить", "⬅️ Назад",
            "🌍 Часовой пояс", "🌍 Автоопределение", "🇷🇺 Москва (UTC+3)",
            "🇷🇺 Екатеринбург (UTC+5)", "🇷🇺 Владивосток (UTC+10)",
            "🇺🇦 Киев (UTC+2)", "🇧🇾 Минск (UTC+3)", "🇪🇺 Лондон (UTC+0)",
            "🇺🇸 Нью-Йорк (UTC-5)"
        ]:
            await message.answer("Пожалуйста, используйте кнопки для взаимодействия с ботом.",
                               reply_markup=get_main_keyboard_with_current(message.from_user.id))


@dp.callback_query(F.data.startswith("activity_remind_"))
async def handle_activity_reminder_callback(callback: CallbackQuery, state: FSMContext):
    """
    Выбор интервала уведомлений при смене активности (только 10, 30, 60 минут).
    """
    user_id = callback.from_user.id
    interval_str = callback.data.split("_")[2]  # activity_remind_10 -> 10

    try:
        interval_minutes = int(interval_str)
        interval_seconds = interval_minutes * 60

        # Обновляем настройки
        update_user_setting(user_id, 'reminder_interval', interval_seconds)
        update_user_setting(user_id, 'notifications_enabled', 1)

        # Сбрасываем кэш времени напоминаний для этого пользователя
        for key in list(reminder_manager.user_next_reminder_time.keys()):
            if key.startswith(str(user_id)):
                del reminder_manager.user_next_reminder_time[key]

        # Получаем информацию о активности из состояния
        data = await state.get_data()
        activity_type = data.get('activity_type', 'work')
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        await callback.message.edit_text(
            f"{emoji} {activity_name}\n00:00:00\n\n✅ Уведомления установлены на каждые {interval_minutes} минут"
        )
        await callback.answer(f"Интервал: {interval_minutes} мин")

        # Очищаем состояние и обновляем главное меню
        await state.clear()

        # Отправляем обновленное главное меню
        await callback.message.answer("Активность запущена", reply_markup=get_main_keyboard_with_current(user_id))

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@dp.message(Command("mytimezone"))
async def cmd_mytimezone(message: Message):
    """
    Проверка и установка часового пояса вручную.
    """
    user_id = message.from_user.id

    # Получаем текущий часовой пояс
    current_tz = get_user_timezone(user_id)

    response = (
        f"🌍 Текущий часовой пояс:\n"
        f"• {get_timezone_display_name(current_tz)}\n"
        f"• Код: {current_tz}\n"
        f"• Локальное время: {format_user_local_time(user_id)}\n\n"
        f"Для смены часового пояса:\n"
        f"1. Используйте ⚙️ Настройки → 🌍 Часовой пояс\n"
        f"2. Или нажмите кнопку ниже для быстрой настройки"
    )

    await message.answer(response, reply_markup=get_timezone_keyboard())

async def main():
    """
    Запуск бота с поддержкой часовых поясов.
    """
    init_db()

    print("=" * 50)
    print("🤖 Time Tracker Bot v4.3.1")
    print("=" * 50)
    print("✅ База данных инициализирована")
    print("✅ Менеджер часовых поясов загружен")
    print("🚀 Запуск бота...")

    await reminder_manager.start()

    # Важно: удаляем вебхук перед запуском polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Вебхук удален")
    except Exception as e:
        print(f"⚠️ Ошибка удаления вебхука: {e}")

    print("✅ Бот готов к работе")
    print("✅ Напоминания запущены (поддержка тестовых интервалов 5 секунд)")
    print("📊 Исправленная система статистики с графиками")
    print("⚙️ Работают тестовые уведомления через 5 секунд")
    print("⚙️ Упрощенные интервалы при смене активности (10, 30, 60 минут)")
    print("=" * 50)
    print("📱 Используйте /start для начала работы")
    print("ℹ️  Используйте /help для справки")
    print("🌍 Используйте /timezone для проверки часового пояса")
    print("🕒 Используйте /time для проверки локального времени")
    print("🧪 Используйте /test5 для быстрого теста (5 секунд)")
    if ADMIN_ID:
        print(f"🛠️  Администратор: ID {ADMIN_ID}")
    print("=" * 50)

    try:
        # Простой запуск polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await reminder_manager.stop()
        print("\n🛑 Бот остановлен")