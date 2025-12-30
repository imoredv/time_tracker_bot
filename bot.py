"""
Time Tracker Bot с поддержкой часовых поясов.
Упрощенная версия с выбором часового пояса при старте и в настройках.
"""

import asyncio
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

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
    get_main_keyboard, get_main_keyboard_with_current, get_statistics_keyboard,
    get_settings_keyboard, get_reminder_interval_keyboard, get_quiet_time_keyboard,
    get_clear_confirm_keyboard, get_reminder_buttons_keyboard,
    get_activity_reminder_keyboard
)
from utils import (
    get_activity_emoji, format_duration_simple, format_stats_message,
    format_interval, get_timezone_display_name, format_user_local_time,
    format_all_settings, generate_activity_graph_with_dates, generate_bar_graph_period
)
from reminder import ReminderManager

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
reminder_manager = ReminderManager(bot)

# Состояния FSM
class EditStates(StatesGroup):
    waiting_for_quiet_start = State()
    waiting_for_quiet_end = State()
    waiting_for_activity_reminder = State()

# ====================== ЧАСОВЫЕ ПОЯСА ======================

# Полный словарь часовых поясов из вашего запроса
TIMEZONES = {
    "(UTC-12:00) Линия перемены дат": "Dateline Standard Time",
    "(UTC-11:00) Время в формате UTC -11": "UTC-11",
    "(UTC-10:00) Алеутские острова": "Aleutian Standard Time",
    "(UTC-10:00) Гавайи": "Hawaiian Standard Time",
    "(UTC-09:30) Маркизские острова": "Marquesas Standard Time",
    "(UTC-09:00) Аляска": "Alaskan Standard Time",
    "(UTC-09:00) Время в формате UTC -09": "UTC-09",
    "(UTC-08:00) Время в формате UTC -08": "UTC-08",
    "(UTC-08:00) Нижняя Калифорния": "Pacific Standard Time (Mexico)",
    "(UTC-08:00) Тихоокеанское время (США и Канада)": "Pacific Standard Time",
    "(UTC-07:00) Аризона": "US Mountain Standard Time",
    "(UTC-07:00) Горное время (США и Канада)": "Mountain Standard Time",
    "(UTC-07:00) Ла-Пас, Масатлан": "Mountain Standard Time (Mexico)",
    "(UTC-07:00) Юкон": "Yukon Standard Time",
    "(UTC-06:00) Гвадалахара, Мехико, Монтеррей": "Central Standard Time (Mexico)",
    "(UTC-06:00) о. Пасхи": "Easter Island Standard Time",
    "(UTC-06:00) Саскачеван": "Canada Central Standard Time",
    "(UTC-06:00) Центральная Америка": "Central America Standard Time",
    "(UTC-06:00) Центральное время (США и Канада)": "Central Standard Time",
    "(UTC-05:00) Богота, Кито, Лима, Рио-Бранко": "SA Pacific Standard Time",
    "(UTC-05:00) Восточное время (США и Канада)": "Eastern Standard Time",
    "(UTC-05:00) Гавана": "Cuba Standard Time",
    "(UTC-05:00) Гаити": "Haiti Standard Time",
    "(UTC-05:00) Индиана (восток)": "US Eastern Standard Time",
    "(UTC-05:00) Острова Теркс и Кайкос": "Turks And Caicos Standard Time",
    "(UTC-05:00) Четумаль": "Eastern Standard Time (Mexico)",
    "(UTC-04:00) Асунсьон": "Paraguay Standard Time",
    "(UTC-04:00) Атлантическое время (Канада)": "Atlantic Standard Time",
    "(UTC-04:00) Джорджтаун, Ла-Пас, Манаус, Сан-Хуан": "SA Western Standard Time",
    "(UTC-04:00) Каракас": "Venezuela Standard Time",
    "(UTC-04:00) Куяба": "Central Brazilian Standard Time",
    "(UTC-04:00) Сантьяго": "Pacific SA Standard Time",
    "(UTC-03:30) Ньюфаундленд": "Newfoundland Standard Time",
    "(UTC-03:00) Арагуаяна": "Tocantins Standard Time",
    "(UTC-03:00) Бразилия": "E. South America Standard Time",
    "(UTC-03:00) Буэнос-Айрес": "Argentina Standard Time",
    "(UTC-03:00) Кайенна, Форталеза": "SA Eastern Standard Time",
    "(UTC-03:00) Монтевидео": "Montevideo Standard Time",
    "(UTC-03:00) Пунта-Аренас": "Magallanes Standard Time",
    "(UTC-03:00) Сальвадор": "Bahia Standard Time",
    "(UTC-03:00) Сен-Пьер и Микелон": "Saint Pierre Standard Time",
    "(UTC-02:00) Время в формате UTC -02": "UTC-02",
    "(UTC-02:00) Гренландия": "Greenland Standard Time",
    "(UTC-01:00) Азорские о-ва": "Azores Standard Time",
    "(UTC-01:00) Кабо-Верде": "Cape Verde Standard Time",
    "(UTC) Время в формате UTC": "UTC",
    "(UTC+00:00) Дублин, Эдинбург, Лиссабон, Лондон": "GMT Standard Time",
    "(UTC+00:00) Монровия, Рейкьявик": "Greenwich Standard Time",
    "(UTC+00:00) Сан-Томе": "Sao Tome Standard Time",
    "(UTC+01:00) Касабланка": "Morocco Standard Time",
    "(UTC+01:00) Амстердам, Берлин, Берн, Вена, Рим, Стокгольм": "W. Europe Standard Time",
    "(UTC+01:00) Белград, Братислава, Будапешт, Любляна, Прага": "Central Europe Standard Time",
    "(UTC+01:00) Брюссель, Копенгаген, Мадрид, Париж": "Romance Standard Time",
    "(UTC+01:00) Варшава, Загреб, Сараево, Скопье": "Central European Standard Time",
    "(UTC+01:00) Западная Центральная Африка": "W. Central Africa Standard Time",
    "(UTC+02:00) Афины, Бухарест": "GTB Standard Time",
    "(UTC+02:00) Бейрут": "Middle East Standard Time",
    "(UTC+02:00) Вильнюс, Киев, Рига, София, Таллин, Хельсинки": "FLE Standard Time",
    "(UTC+02:00) Виндхук": "Namibia Standard Time",
    "(UTC+02:00) Джуба": "South Sudan Standard Time",
    "(UTC+02:00) Иерусалим": "Israel Standard Time",
    "(UTC+02:00) Каир": "Egypt Standard Time",
    "(UTC+02:00) Калининград": "Kaliningrad Standard Time",
    "(UTC+02:00) Кишинев": "E. Europe Standard Time",
    "(UTC+02:00) Сектор Газа, Хеврон": "West Bank Standard Time",
    "(UTC+02:00) Триполи": "Libya Standard Time",
    "(UTC+02:00) Хараре, Претория": "South Africa Standard Time",
    "(UTC+02:00) Хартум": "Sudan Standard Time",
    "(UTC+03:00) Амман": "Jordan Standard Time",
    "(UTC+03:00) Багдад": "Arabic Standard Time",
    "(UTC+03:00) Волгоград": "Volgograd Standard Time",
    "(UTC+03:00) Дамаск": "Syria Standard Time",
    "(UTC+03:00) Кувейт, Эр-Рияд": "Arab Standard Time",
    "(UTC+03:00) Минск": "Belarus Standard Time",
    "(UTC+03:00) Москва, Санкт-Петербург": "Russian Standard Time",
    "(UTC+03:00) Найроби": "E. Africa Standard Time",
    "(UTC+03:00) Стамбул": "Turkey Standard Time",
    "(UTC+03:30) Тегеран": "Iran Standard Time",
    "(UTC+04:00) Абу-Даби, Мускат": "Arabian Standard Time",
    "(UTC+04:00) Астрахань, Ульяновск": "Astrakhan Standard Time",
    "(UTC+04:00) Баку": "Azerbaijan Standard Time",
    "(UTC+04:00) Ереван": "Caucasus Standard Time",
    "(UTC+04:00) Ижевск, Самара": "Russia Time Zone 3",
    "(UTC+04:00) Порт-Луи": "Mauritius Standard Time",
    "(UTC+04:00) Саратов": "Saratov Standard Time",
    "(UTC+04:00) Тбилиси": "Georgian Standard Time",
    "(UTC+04:30) Кабул": "Afghanistan Standard Time",
    "(UTC+05:00) Астана": "Qyzylorda Standard Time",
    "(UTC+05:00) Ашхабад, Ташкент": "West Asia Standard Time",
    "(UTC+05:00) Екатеринбург": "Ekaterinburg Standard Time",
    "(UTC+05:00) Исламабад, Карачи": "Pakistan Standard Time",
    "(UTC+05:30) Колката, Мумбаи, Нью-Дели, Ченнай": "India Standard Time",
    "(UTC+05:30) Шри-Джаявардене-пура-Котте": "Sri Lanka Standard Time",
    "(UTC+05:45) Катманду": "Nepal Standard Time",
    "(UTC+06:00) Бишкек": "Central Asia Standard Time",
    "(UTC+06:00) Дакка": "Bangladesh Standard Time",
    "(UTC+06:00) Омск": "Omsk Standard Time",
    "(UTC+06:30) Янгон": "Myanmar Standard Time",
    "(UTC+07:00) Бангкок, Джакарта, Ханой": "SE Asia Standard Time",
    "(UTC+07:00) Барнаул, Горно-Алтайск": "Altai Standard Time",
    "(UTC+07:00) Красноярск": "North Asia Standard Time",
    "(UTC+07:00) Новосибирск": "N. Central Asia Standard Time",
    "(UTC+07:00) Томск": "Tomsk Standard Time",
    "(UTC+07:00) Ховд": "W. Mongolia Standard Time",
    "(UTC+08:00) Гонконг, Пекин, Урумчи, Чунцин": "China Standard Time",
    "(UTC+08:00) Иркутск": "North Asia East Standard Time",
    "(UTC+08:00) Куала-Лумпур, Сингапур": "Singapore Standard Time",
    "(UTC+08:00) Перт": "W. Australia Standard Time",
    "(UTC+08:00) Тайбэй": "Taipei Standard Time",
    "(UTC+08:00) Улан-Батор": "Ulaanbaatar Standard Time",
    "(UTC+08:45) Юкла": "Aus Central W. Standard Time",
    "(UTC+09:00) Осака, Саппоро, Токио": "Tokyo Standard Time",
    "(UTC+09:00) Пхеньян": "North Korea Standard Time",
    "(UTC+09:00) Сеул": "Korea Standard Time",
    "(UTC+09:00) Чита": "Transbaikal Standard Time",
    "(UTC+09:00) Якутск": "Yakutsk Standard Time",
    "(UTC+09:30) Аделаида": "Cen. Australia Standard Time",
    "(UTC+09:30) Дарвин": "AUS Central Standard Time",
    "(UTC+10:00) Брисбен": "E. Australia Standard Time",
    "(UTC+10:00) Владивосток": "Vladivostok Standard Time",
    "(UTC+10:00) Гуам, Порт-Морсби": "West Pacific Standard Time",
    "(UTC+10:00) Канберра, Мельбурн, Сидней": "AUS Eastern Standard Time",
    "(UTC+10:00) Хобарт": "Tasmania Standard Time",
    "(UTC+10:30) Лорд-Хау": "Lord Howe Standard Time",
    "(UTC+11:00) Магадан": "Magadan Standard Time",
    "(UTC+11:00) Остров Бугенвиль": "Bougainville Standard Time",
    "(UTC+11:00) Остров Норфолк": "Norfolk Standard Time",
    "(UTC+11:00) Сахалин": "Sakhalin Standard Time",
    "(UTC+11:00) Соломоновы о-ва, Нов. Каледония": "Central Pacific Standard Time",
    "(UTC+11:00) Чокурдах": "Russia Time Zone 10",
    "(UTC+12:00) Анадырь, Петропавловск-Камчатский": "Russia Time Zone 11",
    "(UTC+12:00) Веллингтон, Окленд": "New Zealand Standard Time",
    "(UTC+12:00) Время в формате UTC +12": "UTC+12",
    "(UTC+12:00) Фиджи": "Fiji Standard Time",
    "(UTC+12:45) Чатем": "Chatham Islands Standard Time",
    "(UTC+13:00) Время в формате UTC +13": "UTC+13",
    "(UTC+13:00) Нукуалофа": "Tonga Standard Time",
    "(UTC+13:00) Самоа": "Samoa Standard Time",
    "(UTC+14:00) О-в Киритимати": "Line Islands Standard Time",
}

def get_timezone_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с часовыми поясами (пагинация).
    """
    timezone_list = list(TIMEZONES.items())
    items_per_page = 8  # Уменьшено для лучшего отображения
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page

    keyboard_buttons = []

    # Добавляем часовые пояса для текущей страницы
    for tz_display, tz_code in timezone_list[start_idx:end_idx]:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=tz_display,
                callback_data=f"tz_select_{tz_code}"
            )
        ])

    # Добавляем кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"tz_page_{page-1}"))

    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page+1}/{((len(timezone_list)-1)//items_per_page)+1}", callback_data="no_action"))

    if end_idx < len(timezone_list):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"tz_page_{page+1}"))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    # Кнопка отмены
    keyboard_buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="tz_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_simple_timezone_keyboard() -> InlineKeyboardMarkup:
    """
    Упрощенная клавиатура с популярными часовыми поясами.
    """
    popular_timezones = {
        "🇷🇺 Москва, Санкт-Петербург": "Russian Standard Time",
        "🇺🇦 Киев, Рига": "FLE Standard Time",
        "🇧🇾 Минск": "Belarus Standard Time",
        "🇩🇪 Амстердам, Берлин": "W. Europe Standard Time",
        "🇬🇧 Лондон, Дублин": "GMT Standard Time",
        "🇺🇸 Нью-Йорк, Вашингтон": "Eastern Standard Time",
        "🇺🇸 Лос-Анджелес": "Pacific Standard Time",
        "🇯🇵 Токио, Сеул": "Tokyo Standard Time",
        "🇨🇳 Пекин, Гонконг": "China Standard Time",
        "🇦🇺 Сидней, Мельбурн": "AUS Eastern Standard Time",
        "🌍 Все часовые пояса...": "show_all"
    }

    keyboard_buttons = []
    row = []

    for tz_display, tz_code in popular_timezones.items():
        if tz_code == "show_all":
            keyboard_buttons.append([InlineKeyboardButton(text=tz_display, callback_data="tz_show_all")])
        else:
            row.append(InlineKeyboardButton(text=tz_display, callback_data=f"tz_select_{tz_code}"))
            if len(row) == 2:
                keyboard_buttons.append(row)
                row = []

    if row:
        keyboard_buttons.append(row)

    keyboard_buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="tz_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

# ====================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======================

def get_display_activity(user_id, activity_type: str) -> str:
    """
    Получаем название активности для отображения.
    """
    default_emoji = get_activity_emoji(activity_type)
    default_name = ACTIVITIES.get(activity_type, activity_type)
    return f"{default_emoji} {default_name}"

# ====================== КОМАНДЫ БОТА ======================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    Команда /start - приветствие и выбор часового пояса.
    """
    user_id = message.from_user.id

    # Добавляем пользователя с часовым поясом по умолчанию
    add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        timezone=DEFAULT_TIMEZONE  # Москва по умолчанию
    )

    welcome_text = (
        f"⏱️ <b>Time Tracker Bot</b>\n\n"
        f"Добро пожаловать! Я помогу вам отслеживать время, потраченное на различные активности.\n\n"
        f"<b>Перед началом работы выберите ваш часовой пояс:</b>\n"
        f"Это нужно для корректного учета времени и напоминаний."
    )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_simple_timezone_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """
    Команда /help - справка по боту.
    """
    help_text = """
📋 <b>Помощь по боту Time Tracker</b>

<b>Основные функции:</b>
• Выберите активность для начала отсчёта времени
• При выборе другой активности, текущая автоматически завершается
• Бот будет спрашивать чем вы заняты с заданным интервалом

<b>Кнопки:</b>
• 💼 Труд, 📚 Учёба, 🏃 Спорт, 🎨 Хобби, 💤 Сон, ☕️ Отдых - выбор активности
• 📊 Статистика - просмотр статистики с графиками
• ⚙️ Настройки - настройка бота

<b>Настройки:</b>
• ⏰ Напоминания - настройка интервала напоминаний
• 🌙 Тихий час - время, когда бот не беспокоит
• 🌍 Часовой пояс - настройка вашего часового пояса
• 🗑️ Очистить - удаление всех данных

<b>Статистика:</b>
• 📊 Статистика - графики за последние 3 дня
• 📅 Неделя - статистика за неделю
• 📅 Месяц - статистика за месяц
• 📊 Год - статистика за год

<b>Часовые пояса:</b>
• Выберите часовой пояс при старте
• Измените в любое время в настройках
• Время всех операций учитывает ваш часовой пояс
    """
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard_with_current(message.from_user.id))

@dp.message(Command("time"))
async def cmd_time(message: Message):
    """
    Команда /time - отображение текущего времени.
    """
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

@dp.message(Command("timezone"))
async def cmd_timezone(message: Message):
    """
    Команда /timezone - проверка текущего часового пояса.
    """
    user_id = message.from_user.id
    timezone = get_user_timezone(user_id)
    timezone_display = get_timezone_display_name(timezone)
    local_time = format_user_local_time(user_id)

    response = (
        f"🌍 <b>Ваш часовой пояс:</b>\n"
        f"{timezone_display}\n\n"
        f"🕒 <b>Локальное время:</b>\n"
        f"{local_time}\n\n"
        f"Изменить часовой пояс можно в ⚙️ Настройки → 🌍 Часовой пояс"
    )

    await message.answer(
        response,
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )

# ====================== ОБРАБОТЧИКИ АКТИВНОСТЕЙ ======================

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

    # Предлагаем выбрать интервал уведомлений
    response += "📅 Выберите интервал уведомлений для этой активности:"

    # Сначала обновляем клавиатуру
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

# ====================== ОБРАБОТЧИКИ СТАТИСТИКИ ======================

@dp.message(F.text == "📊 Статистика")
async def handle_statistics(message: Message):
    """
    Статистика за последние 24 часа.
    """
    user_id = message.from_user.id

    # Получаем данные за 2 дня для графика
    hourly_stats = get_hourly_activity_stats(user_id, 2)
    activity_stats_24h = get_total_stats_by_activity(user_id, 1)

    # Получаем текущую активность
    current = get_current_activity(user_id)

    # Генерируем графики
    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 2)
    bar_graph = generate_bar_graph_period(activity_stats_24h, user_id)

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
    Статистика за неделю.
    """
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

@dp.message(F.text == "📅 Месяц")
async def handle_month_statistics(message: Message):
    """
    Статистика за месяц.
    """
    user_id = message.from_user.id

    hourly_stats = get_hourly_activity_stats(user_id, 30)
    activity_stats = get_total_stats_by_activity(user_id, 30)
    current = get_current_activity(user_id)

    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 30)
    bar_graph = generate_bar_graph_period(activity_stats, user_id)

    total_seconds = sum(duration for _, duration in activity_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📅 Статистика за месяц:\n\n"

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
        lines = timeline_graph.split('\n')
        if len(lines) > 30:
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
    Статистика за год.
    """
    user_id = message.from_user.id

    hourly_stats = get_hourly_activity_stats(user_id, 30)
    activity_stats = get_total_stats_by_activity(user_id, 365)
    current = get_current_activity(user_id)

    timeline_graph = generate_activity_graph_with_dates(hourly_stats, 30)
    bar_graph = generate_bar_graph_period(activity_stats, user_id)

    total_seconds = sum(duration for _, duration in activity_stats)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    message_text = "📊 Статистика за год:\n\n"

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
        lines = timeline_graph.split('\n')
        if len(lines) > 45:
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

# ====================== ОБРАБОТЧИКИ НАСТРОЕК ======================

@dp.message(F.text == "⚙️ Настройки")
async def handle_settings(message: Message):
    """
    Настройки - показываем все настройки.
    """
    user_id = message.from_user.id
    settings_text = format_all_settings(user_id)
    await message.answer(settings_text, reply_markup=get_settings_keyboard())

@dp.message(F.text == "🌍 Часовой пояс")
async def handle_timezone_settings(message: Message):
    """
    Настройка часового пояса - показывает текущий и предлагает изменить.
    """
    user_id = message.from_user.id
    timezone = get_user_timezone(user_id)

    # Находим отображаемое имя часового пояса
    timezone_display = "Неизвестный часовой пояс"
    for display, code in TIMEZONES.items():
        if code == timezone:
            timezone_display = display
            break

    local_time = format_user_local_time(user_id)

    message_text = (
        f"🌍 <b>Настройка часового пояса</b>\n\n"
        f"<b>Текущий часовой пояс:</b>\n"
        f"{timezone_display}\n\n"
        f"<b>Ваше локальное время:</b>\n"
        f"{local_time}\n\n"
        f"Выберите новый часовой пояс:"
    )

    await message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=get_simple_timezone_keyboard()
    )

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

# ====================== ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК (ЧАСОВЫЕ ПОЯСА) ======================

@dp.callback_query(F.data.startswith("tz_select_"))
async def handle_timezone_select(callback: CallbackQuery):
    """
    Обработчик выбора часового пояса.
    """
    user_id = callback.from_user.id
    timezone_code = callback.data.replace("tz_select_", "")

    # Обновляем часовой пояс пользователя
    if update_user_timezone(user_id, timezone_code):
        # Получаем отображаемое название часового пояса
        timezone_display = "Неизвестный часовой пояс"
        for display, code in TIMEZONES.items():
            if code == timezone_code:
                timezone_display = display
                break

        local_time = format_user_local_time(user_id)

        response = (
            f"✅ <b>Часовой пояс обновлен!</b>\n\n"
            f"<b>Установлен:</b> {timezone_display}\n"
            f"<b>Локальное время:</b> {local_time}"
        )

        # Если это был выбор при старте, показываем главное меню
        if not get_current_activity(user_id):
            await callback.message.edit_text(
                response,
                parse_mode="HTML"
            )
            await callback.message.answer(
                "Теперь вы можете начать использовать бот!",
                reply_markup=get_main_keyboard_with_current(user_id)
            )
        else:
            await callback.message.edit_text(
                response,
                parse_mode="HTML"
            )
            await callback.answer("Часовой пояс обновлен")
    else:
        await callback.message.edit_text(
            "❌ Не удалось обновить часовой пояс. Попробуйте еще раз.",
            reply_markup=get_simple_timezone_keyboard()
        )
        await callback.answer("Ошибка")

@dp.callback_query(F.data.startswith("tz_page_"))
async def handle_timezone_page(callback: CallbackQuery):
    """
    Обработчик переключения страниц с часовыми поясами.
    """
    page = int(callback.data.replace("tz_page_", ""))
    await callback.message.edit_reply_markup(reply_markup=get_timezone_keyboard(page))
    await callback.answer(f"Страница {page+1}")

@dp.callback_query(F.data == "tz_show_all")
async def handle_show_all_timezones(callback: CallbackQuery):
    """
    Показать все часовые пояса (полный список).
    """
    await callback.message.edit_text(
        "🌍 <b>Выберите ваш часовой пояс:</b>\n\n"
        "<i>Используйте кнопки навигации для просмотра всех вариантов</i>",
        parse_mode="HTML",
        reply_markup=get_timezone_keyboard(0)
    )
    await callback.answer()

@dp.callback_query(F.data == "tz_cancel")
async def handle_timezone_cancel(callback: CallbackQuery):
    """
    Отмена выбора часового пояса.
    """
    user_id = callback.from_user.id

    # Если это был выбор при старте, возвращаем к выбору часового пояса
    if not get_current_activity(user_id):
        await callback.message.edit_text(
            "Пожалуйста, выберите ваш часовой пояс для продолжения работы с ботом:",
            reply_markup=get_simple_timezone_keyboard()
        )
    else:
        # Иначе возвращаем в настройки
        timezone = get_user_timezone(user_id)

        # Находим отображаемое имя часового пояса
        timezone_display = "Неизвестный часовой пояс"
        for display, code in TIMEZONES.items():
            if code == timezone:
                timezone_display = display
                break

        local_time = format_user_local_time(user_id)

        message_text = (
            f"🌍 <b>Настройка часового пояса</b>\n\n"
            f"<b>Текущий часовой пояс:</b>\n"
            f"{timezone_display}\n\n"
            f"<b>Ваше локальное время:</b>\n"
            f"{local_time}\n\n"
            f"Выберите новый часовой пояс или нажмите 'Назад':"
        )

        await callback.message.edit_text(
            message_text,
            parse_mode="HTML"
        )
        await callback.message.answer(
            "Выбор часового пояса отменен.",
            reply_markup=get_settings_keyboard()
        )

    await callback.answer()

@dp.callback_query(F.data == "no_action")
async def handle_no_action(callback: CallbackQuery):
    """
    Обработчик для кнопок без действия (например, номер страницы).
    """
    await callback.answer()

# ====================== ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК (НАСТРОЙКИ) ======================

@dp.callback_query(F.data.startswith("interval_"))
async def handle_interval_callback(callback: CallbackQuery):
    """
    Выбор интервала напоминаний в настройках.
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

@dp.callback_query(F.data.startswith("remind_"))
async def handle_reminder_interval_callback(callback: CallbackQuery):
    """
    Выбор интервала напоминания в ответ на уведомление.
    """
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
async def handle_activity_reminder_callback(callback: CallbackQuery, state: FSMContext):
    """
    Выбор интервала уведомлений при смене активности.
    """
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
    Обработка ввода времени начала тихого часа.
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
    Обработка ввода времени окончания тихого часа.
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

# ====================== ОБРАБОТЧИК ОСТАЛЬНЫХ СООБЩЕНИЙ ======================

@dp.message()
async def handle_other_messages(message: Message):
    """
    Обработка всех остальных сообщений.
    """
    # Игнорируем сообщения, не начинающиеся с команды
    if not message.text.startswith('/'):
        allowed_buttons = [
            "💼 Труд", "💼 Труд ✅", "📚 Учёба", "📚 Учёба ✅",
            "🏃 Спорт", "🏃 Спорт ✅", "🎨 Хобби", "🎨 Хобби ✅",
            "💤 Сон", "💤 Сон ✅", "☕️ Отдых", "☕️ Отдых ✅",
            "📊 Статистика", "⚙️ Настройки", "📅 Неделя", "📅 Месяц", "📊 Год",
            "⏰ Напоминания", "🌙 Тихий час", "🗑️ Очистить", "⬅️ Назад",
            "🌍 Часовой пояс"
        ]

        if message.text not in allowed_buttons:
            await message.answer(
                "Пожалуйста, используйте кнопки для взаимодействия с ботом.",
                reply_markup=get_main_keyboard_with_current(message.from_user.id)
            )

# ====================== ГЛАВНАЯ ФУНКЦИЯ ======================

async def main():
    """
    Запуск бота.
    """
    init_db()

    print("=" * 50)
    print("🤖 Time Tracker Bot v4.3.1")
    print("=" * 50)
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
    print("✅ Упрощенная система выбора часовых поясов")
    print("=" * 50)
    print("📱 Используйте /start для начала работы")
    print("ℹ️  Используйте /help для справки")
    print("🕒 Используйте /time для проверки времени")
    print("🌍 Используйте /timezone для проверки часового пояса")
    if ADMIN_ID:
        print(f"🛠️  Администратор: ID {ADMIN_ID}")
    print("=" * 50)

    try:
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