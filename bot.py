"""
Time Tracker Bot с поддержкой часовых поясов.
"""

import asyncio
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_ID, ACTIVITIES, DEFAULT_TIMEZONE
from database import (
    init_db, add_user, start_activity, get_current_activity,
    get_daily_stats, get_period_stats, update_user_setting,
    get_user_settings, clear_user_data, update_custom_activity,
    get_custom_activity, get_all_custom_activities, delete_custom_activity,
    get_all_users, get_users_for_reminders, update_user_timezone,
    get_user_timezone, get_user_timezone_info, get_timezone_stats
)
from keyboards import (
    get_main_keyboard, get_statistics_keyboard, get_settings_keyboard,
    get_reminder_interval_keyboard, get_clear_confirm_keyboard,
    get_quiet_time_keyboard, get_edit_activities_keyboard,
    get_edit_activity_keyboard, get_emoji_keyboard,
    get_timezone_keyboard, get_timezone_inline_keyboard, get_timezone_back_keyboard
)
from utils import (
    get_activity_emoji, format_duration_simple, format_stats_message,
    format_interval, format_timezone_info, get_timezone_display_name,
    format_user_local_time
)
from reminder import ReminderManager
from timezone_manager import timezone_manager

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
reminder_manager = ReminderManager(bot)

# Состояния FSM для редактирования
class EditStates(StatesGroup):
    waiting_for_activity_name = State()
    waiting_for_activity_emoji = State()
    waiting_for_quiet_start = State()
    waiting_for_quiet_end = State()
    waiting_for_emoji_selection = State()

# Функция для получения отображаемого названия активности
def get_display_activity(user_id, activity_type):
    """
    Получаем название активности для отображения.
    """
    custom = get_custom_activity(user_id, activity_type)
    if custom and custom['custom_name'] and custom['emoji']:
        return f"{custom['emoji']} {custom['custom_name']}"
    else:
        default_emoji = get_activity_emoji(activity_type)
        default_name = ACTIVITIES.get(activity_type, activity_type)
        return f"{default_emoji} {default_name}"

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    Команда /start с определением часового пояса.
    """
    # Определяем часовой пояс
    try:
        auto_timezone = timezone_manager.detect_by_ip()
    except:
        auto_timezone = DEFAULT_TIMEZONE

    add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        timezone=auto_timezone
    )

    welcome_text = (
        f"⏱️ Учёт времени\n\n"
        f"Часовой пояс автоматически определен как: {get_timezone_display_name(auto_timezone)}\n"
        f"Локальное время: {format_user_local_time(message.from_user.id)}"
    )

    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """
    Команда /help.
    """
    help_text = """
📋 <b>Помощь по боту Time Tracker</b>

<b>Основные функции:</b>
• Выберите активность для начала отсчёта времени
• При выборе другой активности, текущая автоматически завершается
• Бот будет спрашивать чем вы заняты с заданным интервалом

<b>Кнопки:</b>
• 💼 Работа, 📚 Учёба, 🏃 Спорт, 🎨 Хобби, 💤 Сон, ☕️ Отдых - выбор активности
• 📊 Статистика - просмотр статистики за разные периоды
• ⚙️ Настройки - настройка бота

<b>Настройки:</b>
• ⏰ Напоминания - настройка интервала напоминаний
• 🌙 Тихий час - время, когда бот не беспокоит
• ✏️ Изменить - изменение названий и эмодзи активностей
• 🌍 Часовой пояс - настройка вашего часового пояса
• 🗑️ Очистить - удаление всех данных

<b>Статистика:</b>
• 📅 День - статистика за сегодня
• 📆 Неделя - статистика за последние 7 дней
• 📅 Месяц - статистика за последние 30 дней
• 📊 Год - статистика за последние 365 дней

⏱️ - обозначает текущую активность в статистике

<b>Часовые пояса:</b>
• Бот автоматически определяет ваш часовой пояс
• Вы можете изменить его в настройках
• Напоминания учитывают ваш часовой пояс и тихое время
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

@dp.message(Command("debug"))
async def cmd_debug(message: Message):
    """
    Отладка настроек активностей.
    """
    user_id_int = int(message.from_user.id)
    admin_id_int = int(ADMIN_ID)

    if user_id_int != admin_id_int:
        return

    user_id = message.from_user.id
    custom_activities = get_all_custom_activities(user_id)

    debug_text = "🔧 Отладка кастомных активностей:\n\n"

    for activity_type in ['work', 'study', 'sport', 'hobby', 'sleep', 'rest']:
        custom = get_custom_activity(user_id, activity_type)
        if custom and custom['custom_name'] and custom['emoji']:
            debug_text += f"{activity_type}: {custom['custom_name']} {custom['emoji']}\n"
        else:
            debug_text += f"{activity_type}: нет кастомных настроек\n"

    await message.answer(debug_text)

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
        f"• Версия: 3.0 (с часовыми поясами)\n"
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

# Обработчики активностей
activity_buttons = {
    "💼 Работа": "work",
    "📚 Учёба": "study",
    "🏃 Спорт": "sport",
    "🎨 Хобби": "hobby",
    "💤 Сон": "sleep",
    "☕️ Отдых": "rest"
}

for button_text, activity_type in activity_buttons.items():
    @dp.message(F.text == button_text)
    async def handle_activity(message: Message, btn_text=button_text, act_type=activity_type):
        user_id = message.from_user.id

        # Проверяем, активна ли уже такая же активность
        current = get_current_activity(user_id)
        if current and current[0] == act_type:
            display_text = get_display_activity(user_id, act_type)
            start_time = datetime.fromisoformat(current[1])
            current_time = datetime.now()
            duration = int((current_time - start_time).total_seconds())

            await message.answer(
                f"{display_text} продолжается\n{format_duration_simple(duration)}"
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
        response += f"{display_text} старт\n00:00:00"

        await message.answer(response)

@dp.message(F.text == "📊 Статистика")
async def handle_statistics(message: Message):
    """
    Статистика.
    """
    user_id = message.from_user.id
    stats = get_daily_stats(user_id)
    message_text = format_stats_message(stats, "📊 Статистика за день", user_id)

    await message.answer(message_text, reply_markup=get_statistics_keyboard())

@dp.message(F.text.in_(["📅 День", "📆 Неделя", "📅 Месяц", "📊 Год"]))
async def handle_statistics_period(message: Message):
    """
    Выбор периода статистики.
    """
    user_id = message.from_user.id
    period_map = {
        "📅 День": ("📅 День", 1),
        "📆 Неделя": ("📆 Неделя", 7),
        "📅 Месяц": ("📅 Месяц", 30),
        "📊 Год": ("📊 Год", 365)
    }

    period_name, days = period_map[message.text]

    if days == 1:
        stats = get_daily_stats(user_id)
    else:
        stats = get_period_stats(user_id, days)

    message_text = format_stats_message(stats, period_name, user_id)
    await message.answer(message_text, reply_markup=get_statistics_keyboard())

@dp.message(F.text == "⚙️ Настройки")
async def handle_settings(message: Message):
    """
    Настройки.
    """
    user_id = message.from_user.id
    timezone_info = format_timezone_info(user_id)

    settings_text = (
        f"⚙️ Настройки\n\n"
        f"{timezone_info}\n\n"
        f"Выберите раздел для настройки:"
    )

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
        auto_timezone = timezone_manager.detect_by_ip()
        update_user_timezone(user_id, auto_timezone)

        timezone_display = get_timezone_display_name(auto_timezone)
        local_time = format_user_local_time(user_id)

        response = (
            f"✅ Часовой пояс обновлен!\n\n"
            f"• {timezone_display}\n"
            f"• Локальное время: {local_time}"
        )
    except Exception as e:
        response = f"❌ Не удалось определить часовой пояс автоматически: {e}"

    await message.answer(response, reply_markup=get_settings_keyboard())

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

@dp.message(F.text == "✏️ Изменить")
async def handle_edit_activities(message: Message):
    """
    Редактирование активностей.
    """
    user_id = message.from_user.id

    message_text = "✏️ Изменить активности\n\n"
    activity_types = ['work', 'study', 'sport', 'hobby', 'sleep', 'rest']

    for activity_type in activity_types:
        display_text = get_display_activity(user_id, activity_type)
        message_text += f"{display_text}\n"

    await message.answer(
        message_text,
        reply_markup=get_edit_activities_keyboard()
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
    await message.answer("Главное меню", reply_markup=get_main_keyboard())

# Обработчики инлайн-кнопок для часовых поясов
@dp.callback_query(F.data.startswith("timezone_"))
async def handle_timezone_callback(callback: CallbackQuery):
    """
    Выбор часового пояса через инлайн-кнопки.
    """
    user_id = callback.from_user.id
    timezone_code = callback.data.replace("timezone_", "")

    if timezone_code == "auto":
        # Автоопределение
        try:
            auto_timezone = timezone_manager.detect_by_ip()
            update_user_timezone(user_id, auto_timezone)
            timezone_display = get_timezone_display_name(auto_timezone)
            response = f"✅ Автоопределение: {timezone_display}"
        except Exception as e:
            response = f"❌ Не удалось определить автоматически: {e}"
    else:
        # Ручной выбор
        if timezone_manager.validate_timezone(timezone_code):
            update_user_timezone(user_id, timezone_code)
            timezone_display = get_timezone_display_name(timezone_code)
            response = f"✅ Установлен: {timezone_display}"
        else:
            response = "❌ Неверный часовой пояс"

    local_time = format_user_local_time(user_id)
    response += f"\n🕒 Локальное время: {local_time}"

    await callback.message.edit_text(response)
    await callback.message.edit_reply_markup(
        reply_markup=get_timezone_inline_keyboard()
    )
    await callback.answer(response)

@dp.callback_query(F.data.startswith("interval_"))
async def handle_interval_callback(callback: CallbackQuery):
    """
    Выбор интервала.
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

@dp.callback_query(F.data == "edit_activities")
async def handle_edit_activities_callback(callback: CallbackQuery):
    """
    Редактирование активностей.
    """
    user_id = callback.from_user.id

    message_text = "✏️ Изменить активности\n\n"
    activity_types = ['work', 'study', 'sport', 'hobby', 'sleep', 'rest']

    for activity_type in activity_types:
        display_text = get_display_activity(user_id, activity_type)
        message_text += f"{display_text}\n"

    await callback.message.edit_text(message_text)
    await callback.message.edit_reply_markup(
        reply_markup=get_edit_activities_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def handle_edit_activity(callback: CallbackQuery):
    """
    Редактирование конкретной активности.
    """
    if callback.data.startswith("edit_work"):
        activity_type = "work"
    elif callback.data.startswith("edit_study"):
        activity_type = "study"
    elif callback.data.startswith("edit_sport"):
        activity_type = "sport"
    elif callback.data.startswith("edit_hobby"):
        activity_type = "hobby"
    elif callback.data.startswith("edit_sleep"):
        activity_type = "sleep"
    elif callback.data.startswith("edit_rest"):
        activity_type = "rest"
    else:
        await callback.answer("Неизвестная активность")
        return

    user_id = callback.from_user.id
    display_text = get_display_activity(user_id, activity_type)
    default_name = ACTIVITIES.get(activity_type, activity_type)

    await callback.message.edit_text(
        f"✏️ Изменить:\n{display_text}\n\nПо умолчанию: {default_name}"
    )
    await callback.message.edit_reply_markup(
        reply_markup=get_edit_activity_keyboard(activity_type)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_name_"))
async def handle_edit_name(callback: CallbackQuery, state: FSMContext):
    """
    Изменение названия активности.
    """
    activity_type = callback.data.split("_")[2]
    await state.update_data(activity_type=activity_type)

    user_id = callback.from_user.id
    current_name = get_custom_activity(user_id, activity_type)
    if current_name and current_name['custom_name']:
        current_text = f"\nТекущее название: {current_name['custom_name']}"
    else:
        current_text = ""

    await callback.message.edit_text(
        f"Введите новое название для активности:\n\nТип: {activity_type}{current_text}"
    )
    await state.set_state(EditStates.waiting_for_activity_name)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_emoji_"))
async def handle_edit_emoji(callback: CallbackQuery, state: FSMContext):
    """
    Изменение эмодзи активности.
    """
    activity_type = callback.data.split("_")[2]
    await state.update_data(activity_type=activity_type)
    await state.set_state(EditStates.waiting_for_emoji_selection)

    user_id = callback.from_user.id
    current_emoji = get_custom_activity(user_id, activity_type)
    if current_emoji and current_emoji['emoji']:
        current_text = f"\nТекущий эмодзи: {current_emoji['emoji']}"
    else:
        default_emoji = get_activity_emoji(activity_type)
        current_text = f"\nТекущий эмодзи: {default_emoji}"

    await callback.message.edit_text(
        f"Выберите эмодзи для активности {activity_type}:{current_text}"
    )
    await callback.message.edit_reply_markup(
        reply_markup=get_emoji_keyboard()
    )
    await callback.answer()

@dp.callback_query(EditStates.waiting_for_emoji_selection, F.data.startswith("emoji_"))
async def handle_emoji_selection(callback: CallbackQuery, state: FSMContext):
    """
    Выбор эмодзи для активности.
    """
    emoji = callback.data.split("_")[1]
    data = await state.get_data()
    activity_type = data.get('activity_type')
    user_id = callback.from_user.id

    if not activity_type:
        await callback.answer("Ошибка: не найден тип активности")
        return

    # Получаем текущее название или используем стандартное
    custom = get_custom_activity(user_id, activity_type)
    if custom and custom['custom_name']:
        current_name = custom['custom_name']
    else:
        current_name = ACTIVITIES.get(activity_type, activity_type)

    update_custom_activity(user_id, activity_type, current_name, emoji)

    display_text = get_display_activity(user_id, activity_type)
    await callback.message.edit_text(
        f"✅ Обновлено: {display_text}"
    )
    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard()
    )
    await state.clear()
    await callback.answer(f"Установлен эмодзи: {emoji}")

@dp.callback_query(F.data == "back_emoji")
async def handle_back_emoji(callback: CallbackQuery, state: FSMContext):
    """
    Назад от выбора эмодзи.
    """
    data = await state.get_data()
    activity_type = data.get('activity_type')

    if activity_type:
        user_id = callback.from_user.id
        display_text = get_display_activity(user_id, activity_type)
        default_name = ACTIVITIES.get(activity_type, activity_type)

        await callback.message.edit_text(
            f"✏️ Изменить:\n{display_text}\n\nПо умолчанию: {default_name}"
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_edit_activity_keyboard(activity_type)
        )

    await state.clear()
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_activity_"))
async def handle_delete_activity(callback: CallbackQuery):
    """
    Удаление пользовательской активности.
    """
    activity_type = callback.data.split("_")[2]
    user_id = callback.from_user.id

    delete_custom_activity(user_id, activity_type)

    display_text = get_display_activity(user_id, activity_type)
    await callback.message.edit_text(
        f"✅ Сброшено: {display_text}\n\nУстановлены значения по умолчанию."
    )

    # Возвращаем к списку активностей
    message_text = "✏️ Изменить активностей"
    # Возвращаем к списку активностей
    message_text = "✏️ Изменить активности\n\n"
    activity_types = ['work', 'study', 'sport', 'hobby', 'sleep', 'rest']

    for act_type in activity_types:
        display_text = get_display_activity(user_id, act_type)
        message_text += f"{display_text}\n"

    await callback.message.edit_text(message_text)
    await callback.message.edit_reply_markup(
        reply_markup=get_edit_activities_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "add_activity")
async def handle_add_activity(callback: CallbackQuery):
    """
    Добавление новой активности.
    """
    await callback.answer("Функция в разработке", show_alert=True)


@dp.callback_query(F.data == "back_settings")
async def handle_back_settings(callback: CallbackQuery):
    """
    Назад в настройки.
    """
    user_id = callback.from_user.id
    timezone_info = format_timezone_info(user_id)

    settings_text = (
        f"⚙️ Настройки\n\n"
        f"{timezone_info}\n\n"
        f"Выберите раздел для настройки:"
    )

    await callback.message.edit_text(settings_text)
    await callback.message.edit_reply_markup(
        reply_markup=None
    )
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
async def handle_other_messages(message: Message):
    """
    Обработка всех остальных сообщений.
    """
    # Если сообщение не начинается с команды и не является кнопкой - игнорируем
    if not message.text.startswith('/'):
        # Проверяем, не является ли это кнопкой из клавиатуры
        if message.text not in [
            "💼 Работа", "📚 Учёба", "🏃 Спорт", "🎨 Хобби", "💤 Сон", "☕️ Отдых",
            "📊 Статистика", "⚙️ Настройки", "📅 День", "📆 Неделя", "📅 Месяц", "📊 Год",
            "⏰ Напоминания", "🌙 Тихий час", "✏️ Изменить", "🗑️ Очистить", "⬅️ Назад",
            "🌍 Часовой пояс", "🌍 Автоопределение", "🇷🇺 Москва (UTC+3)",
            "🇷🇺 Калининград (UTC+2)", "🇷🇺 Самара (UTC+4)", "🇷🇺 Екатеринбург (UTC+5)",
            "🇷🇺 Омск (UTC+6)", "🇷🇺 Красноярск (UTC+7)", "🇷🇺 Иркутск (UTC+8)",
            "🇷🇺 Якутск (UTC+9)", "🇷🇺 Владивосток (UTC+10)", "🇷🇺 Магадан (UTC+11)",
            "🇷🇺 Камчатка (UTC+12)", "🇺🇦 Киев (UTC+2)", "🇧🇾 Минск (UTC+3)",
            "🇪🇺 Лондон (UTC+0)", "🇪🇺 Берлин (UTC+1)", "🇺🇸 Нью-Йорк (UTC-5)",
            "🇺🇸 Лос-Анджелес (UTC-8)", "🇨🇳 Пекин (UTC+8)", "🇯🇵 Токио (UTC+9)",
            "🌍 UTC (Гринвич)"
        ]:
            await message.answer("Пожалуйста, используйте кнопки для взаимодействия с ботом.",
                                 reply_markup=get_main_keyboard())


async def main():
    """
    Запуск бота с поддержкой часовых поясов.
    """
    init_db()

    print("=" * 50)
    print("🤖 Time Tracker Bot v3.0")
    print("=" * 50)
    print("✅ База данных инициализирована (с часовыми поясами)")
    print("✅ Менеджер часовых поясов загружен")
    print("🚀 Запуск бота...")

    await reminder_manager.start()
    await bot.delete_webhook(drop_pending_updates=True)

    print("✅ Бот готов к работе")
    print("✅ Напоминания запущены (с учетом часовых поясов)")
    print("⏰ Интервал по умолчанию: 30 минут")
    print("🌙 Тихий час по умолчанию: 22:00 - 06:00")
    print("🌍 Часовой пояс по умолчанию: Europe/Moscow")
    print("=" * 50)
    print("📱 Используйте /start для начала работы")
    print("ℹ️  Используйте /help для справки")
    print("🌍 Используйте /timezone для проверки часового пояса")
    print("🕒 Используйте /time для проверки локального времени")
    if ADMIN_ID:
        print(f"🛠️  Администратор: ID {ADMIN_ID}")
    print("=" * 50)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
    finally:
        await reminder_manager.stop()
        print("\n🛑 Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")