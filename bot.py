"""
Time Tracker Bot с поддержкой часовых поясов.
Упрощенная версия...
"""

import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, ADMIN_ID, ACTIVITIES, DEFAULT_TIMEZONE
from database import (
    init_db, add_user, start_activity, get_current_activity,
    get_hourly_activity_stats, get_total_stats_by_activity,
    update_user_timezone, get_user_timezone, update_user_setting,
    get_user_settings, clear_user_data
)
from keyboards import (
    get_main_keyboard, get_main_keyboard_with_current, get_statistics_keyboard,
    get_settings_keyboard, get_reminder_interval_keyboard, get_quiet_time_keyboard,
    get_clear_confirm_keyboard, get_reminder_buttons_keyboard,
    get_activity_reminder_keyboard
)
from reminder import ReminderManager
from utils import (
    get_activity_emoji, format_duration_simple,
    generate_activity_graph_with_dates, generate_bar_graph_period,
    format_user_local_time, get_timezone_display_name,
    format_all_settings, format_interval  # Добавлено
)

from timezone_manager import timezone_manager

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
reminder_manager = ReminderManager(bot)

# Состояния FSM
class EditStates(StatesGroup):
    waiting_for_quiet_start = State()
    waiting_for_quiet_end = State()
    waiting_for_activity_reminder = State()

class TimezoneStates(StatesGroup):
    waiting_for_timezone = State()


# ====================== КОМАНДЫ БОТА ======================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Команда /start - приветствие и выбор часового пояса."""
    user_id = message.from_user.id

    add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        timezone=DEFAULT_TIMEZONE
    )

    welcome_text = (
        f"⏱️ <b>Time Tracker Bot</b>\n\n"
        f"Добро пожаловать! Я помогу отслеживать время.\n\n"
        f"<b>Перед началом укажите часовой пояс:</b>\n\n"
        f"Введите:\n"
        f"• 📍 Название города (например: <code>Москва</code>)\n"
        f"• ⏱️ Смещение UTC (например: <code>+3</code>)\n\n"
        f"<i>Для Москвы: Москва или +3</i>"
    )

    await message.answer(welcome_text, parse_mode="HTML")
    await state.set_state(TimezoneStates.waiting_for_timezone)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Команда /help - справка."""
    help_text = """
📋 <b>Помощь по боту Time Tracker</b>

<b>Основные функции:</b>
• Выберите активность для отсчёта времени
• Текущая активность автоматически завершается при выборе новой
• Напоминания с заданным интервалом

<b>Кнопки:</b>
• 💼 Труд, 📚 Учёба, 🏃 Спорт, 🎨 Хобби, 💤 Сон, ☕️ Отдых - выбор активности
• 📊 Статистика - просмотр статистики
• ⚙️ Настройки - настройка бота

<b>Настройки:</b>
• ⏰ Напоминания - настройка интервала
• 🌙 Тихий час - время без уведомлений
• 🌍 Часовой пояс - настройка часового пояса
• 🗑️ Очистить - удаление данных
    """
    await message.answer(help_text, parse_mode="HTML",
                         reply_markup=get_main_keyboard_with_current(message.from_user.id))


@dp.message(Command("time"))
async def cmd_time(message: types.Message):
    """Команда /time - отображение текущего времени."""
    user_id = message.from_user.id
    local_time = format_user_local_time(user_id)
    timezone = get_user_timezone(user_id)
    timezone_display = get_timezone_display_name(timezone)

    await message.answer(
        f"🕒 <b>Ваше локальное время:</b>\n"
        f"{local_time}\n"
        f"<i>Часовой пояс: {timezone_display}</i>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard_with_current(user_id)
    )


# ====================== ОБРАБОТКА ЧАСОВОГО ПОЯСА ======================

@dp.message(TimezoneStates.waiting_for_timezone)
async def handle_timezone_input(message: types.Message, state: FSMContext):
    """Обработка ввода часового пояса."""
    user_id = message.from_user.id
    user_input = message.text.strip()

    tz_code, result_message = timezone_manager.parse_input(user_input)

    if tz_code:
        if update_user_timezone(user_id, tz_code):
            local_time = format_user_local_time(user_id)

            response = (
                f"✅ <b>Часовой пояс установлен!</b>\n\n"
                f"{result_message}\n"
                f"🕒 <b>Ваше время:</b> {local_time}\n\n"
                f"Теперь можно использовать бот!"
            )

            await message.answer(response, parse_mode="HTML", reply_markup=get_main_keyboard())
        else:
            await message.answer(
                "❌ <b>Ошибка установки часового пояса</b>\n\n"
                "Попробуйте еще раз. Введите город или смещение UTC:",
                parse_mode="HTML"
            )
    else:
        await message.answer(
            f"❌ <b>{result_message}</b>\n\n"
            "Попробуйте:\n"
            "• Ввести название города (Москва, Лондон)\n"
            "• Указать смещение UTC (+3, -5, UTC+8)\n"
            "• Использовать английское название города",
            parse_mode="HTML"
        )

    await state.clear()


# ====================== ОБРАБОТЧИКИ АКТИВНОСТЕЙ ======================

@dp.message(F.text.in_(["💼 Труд", "💼 Труд ✅", "📚 Учёба", "📚 Учёба ✅", "🏃 Спорт", "🏃 Спорт ✅",
                        "🎨 Хобби", "🎨 Хобби ✅", "💤 Сон", "💤 Сон ✅", "☕️ Отдых", "☕️ Отдых ✅"]))
async def handle_activity(message: types.Message, state: FSMContext):
    """Обработчик выбора активности."""
    user_id = message.from_user.id

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
        emoji = get_activity_emoji(act_type)
        name = ACTIVITIES.get(act_type, act_type)
        start_time = datetime.fromisoformat(current[1])
        current_time = datetime.now()
        duration = int((current_time - start_time).total_seconds())

        await message.answer(
            f"{emoji} {name} продолжается\n{format_duration_simple(duration)}",
            reply_markup=get_main_keyboard_with_current(user_id)
        )
        return

    # Запускаем новую активность
    completed_activity = start_activity(user_id, act_type)

    response = ""

    if completed_activity:
        completed_type, start_time_str = completed_activity
        emoji = get_activity_emoji(completed_type)
        name = ACTIVITIES.get(completed_type, completed_type)

        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        response += f"{emoji} {name} стоп\n{format_duration_simple(duration)}\n\n"

    # Новая активность
    emoji = get_activity_emoji(act_type)
    name = ACTIVITIES.get(act_type, act_type)
    response += f"{emoji} {name} старт\n00:00:00\n\n"

    # Предлагаем выбрать интервал уведомлений
    response += "📅 Выберите интервал уведомлений для этой активности:"

    await message.answer("🔄 Обновление меню...",
                         reply_markup=get_main_keyboard_with_current(user_id))
    await message.answer(response, reply_markup=get_activity_reminder_keyboard())

    await state.update_data(activity_type=act_type)
    await state.set_state(EditStates.waiting_for_activity_reminder)


# ====================== ОБРАБОТЧИКИ СТАТИСТИКИ ======================

@dp.message(F.text == "📊 Статистика")
async def handle_statistics(message: types.Message):
    """Статистика за последние 24 часа."""
    user_id = message.from_user.id

    hourly_stats = get_hourly_activity_stats(user_id, 2)
    activity_stats_24h = get_total_stats_by_activity(user_id, 1)
    current = get_current_activity(user_id)

    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 2)
    bar_graph = generate_bar_graph_period(activity_stats_24h, user_id)

    total_seconds = sum(duration for _, duration in activity_stats_24h)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📊 Статистика за последние 24 часа:\n\n"

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
async def handle_week_statistics(message: types.Message):
    """Статистика за неделю."""
    user_id = message.from_user.id

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

    await message.answer(message_text, reply_markup=get_statistics_keyboard())


# ====================== ОБРАБОТЧИКИ НАСТРОЕК ======================

@dp.message(F.text == "⚙️ Настройки")
async def handle_settings(message: types.Message):
    """Настройки - показываем все настройки."""
    user_id = message.from_user.id
    settings_text = format_all_settings(user_id)
    await message.answer(settings_text, reply_markup=get_settings_keyboard())


@dp.message(F.text == "🌍 Часовой пояс")
async def handle_timezone_settings(message: types.Message, state: FSMContext):
    """Настройка часового пояса - просим ввести новый."""
    user_id = message.from_user.id
    timezone = get_user_timezone(user_id)
    local_time = format_user_local_time(user_id)

    message_text = (
        f"🌍 <b>Текущий часовой пояс:</b>\n"
        f"{get_timezone_display_name(timezone)}\n"
        f"🕒 <b>Ваше время:</b> {local_time}\n\n"
        f"<b>Введите новый часовой пояс:</b>\n\n"
        f"Введите:\n"
        f"• 📍 Название города (например: <code>Москва</code>)\n"
        f"• ⏱️ Смещение UTC (например: <code>+3</code>)"
    )

    await message.answer(message_text, parse_mode="HTML")
    await state.set_state(TimezoneStates.waiting_for_timezone)


@dp.message(F.text == "⏰ Напоминания")
async def handle_reminders(message: types.Message):
    """Настройка напоминаний."""
    user_id = message.from_user.id
    settings = get_user_settings(user_id)

    current_interval = settings['reminder_interval'] if settings else 1800
    notifications_enabled = settings['notifications_enabled'] if settings else True

    from utils import format_interval
    interval_text = format_interval(current_interval)
    status_text = "включены" if notifications_enabled else "выключены"

    await message.answer(
        f"⏰ Напоминания\nИнтервал: {interval_text}\nСтатус: {status_text}",
        reply_markup=get_reminder_interval_keyboard(current_interval, notifications_enabled)
    )


@dp.message(F.text == "🌙 Тихий час")
async def handle_quiet_time(message: types.Message):
    """Настройка тихого времени."""
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
async def handle_clear_data(message: types.Message):
    """Очистка данных."""
    await message.answer(
        "🗑️ Очистить все данные?\nЭто действие нельзя отменить.",
        reply_markup=get_clear_confirm_keyboard()
    )


@dp.message(F.text == "⬅️ Назад")
async def handle_back(message: types.Message):
    """Назад в главное меню."""
    await message.answer("Главное меню",
                         reply_markup=get_main_keyboard_with_current(message.from_user.id))


# ====================== ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК ======================

@dp.callback_query(F.data.startswith("interval_"))
async def handle_interval_callback(callback: types.CallbackQuery):
    """Выбор интервала напоминаний в настройках."""
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

        from utils import format_interval
        interval_text = format_interval(interval)
        await callback.message.edit_text(
            f"⏰ Напоминания\nИнтервал: {interval_text}\nСтатус: включены"
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_reminder_interval_keyboard(interval, True)
        )

    await callback.answer(f"Установлено: {format_interval(interval)}")


@dp.callback_query(F.data.startswith("remind_"))
async def handle_reminder_interval_callback(callback: types.CallbackQuery):
    """Выбор интервала напоминания в ответ на уведомление."""
    user_id = callback.from_user.id
    interval_str = callback.data.split("_")[1]

    try:
        interval_minutes = int(interval_str)
        interval_seconds = interval_minutes * 60

        update_user_setting(user_id, 'reminder_interval', interval_seconds)
        update_user_setting(user_id, 'notifications_enabled', 1)

        for key in list(reminder_manager.user_next_reminder_time.keys()):
            if key.startswith(str(user_id)):
                del reminder_manager.user_next_reminder_time[key]

        await callback.message.edit_text(
            f"✅ Уведомления установлены на каждые {interval_minutes} минут"
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@dp.callback_query(F.data.startswith("activity_remind_"))
async def handle_activity_reminder_callback(callback: types.CallbackQuery, state: FSMContext):
    """Выбор интервала уведомлений при смене активности."""
    user_id = callback.from_user.id
    interval_str = callback.data.split("_")[2]

    try:
        interval_minutes = int(interval_str)
        interval_seconds = interval_minutes * 60

        update_user_setting(user_id, 'reminder_interval', interval_seconds)
        update_user_setting(user_id, 'notifications_enabled', 1)

        for key in list(reminder_manager.user_next_reminder_time.keys()):
            if key.startswith(str(user_id)):
                del reminder_manager.user_next_reminder_time[key]

        data = await state.get_data()
        activity_type = data.get('activity_type', 'work')
        activity_name = ACTIVITIES.get(activity_type, activity_type)
        emoji = get_activity_emoji(activity_type)

        await callback.message.edit_text(
            f"{emoji} {activity_name}\n00:00:00\n\n✅ Уведомления установлены на каждые {interval_minutes} минут"
        )
        await callback.answer(f"Интервал: {interval_minutes} мин")

        await state.clear()
        await callback.message.answer("Активность запущена",
                                     reply_markup=get_main_keyboard_with_current(user_id))

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# ====================== ГЛАВНАЯ ФУНКЦИЯ ======================

async def main():
    """Запуск бота."""
    init_db()

    print("=" * 50)
    print("🤖 Time Tracker Bot v4.3.1 (упрощенная версия)")
    print("✅ База данных инициализирована")
    print("🚀 Запуск бота...")

    await reminder_manager.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Вебхук удален")
    except Exception as e:
        print(f"⚠️ Ошибка удаления вебхука: {e}")

    print("✅ Бот готов к работе")
    print("✅ Напоминания запущены")
    print("=" * 50)

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    finally:
        await reminder_manager.stop()
        print("\n🛑 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())