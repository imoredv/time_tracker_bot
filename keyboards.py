"""
Клавиатуры с поддержкой часовых поясов .
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from timezone_manager import timezone_manager

def get_main_keyboard():
    """
    Основная клавиатура - активности.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💼 Труд"), KeyboardButton(text="📚 Учёба")],
            [KeyboardButton(text="🏃 Спорт"), KeyboardButton(text="🎨 Хобби")],
            [KeyboardButton(text="💤 Сон"), KeyboardButton(text="☕️ Отдых")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_statistics_keyboard():
    """
    Клавиатура статистики.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📅 Неделя")],
            [KeyboardButton(text="📅 Месяц"), KeyboardButton(text="📊 Год")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_settings_keyboard():
    """
    Клавиатура настроек (по 2 кнопки в ряд).
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="🌙 Тихий час")],
            [KeyboardButton(text="🌍 Часовой пояс"), KeyboardButton(text="🗑️ Очистить")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_timezone_keyboard():
    """
    Клавиатура выбора часового пояса.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌍 Автоопределение"), KeyboardButton(text="🇷🇺 Москва (UTC+3)")],
            [KeyboardButton(text="🇷🇺 Екатеринбург (UTC+5)"), KeyboardButton(text="🇷🇺 Владивосток (UTC+10)")],
            [KeyboardButton(text="🇺🇦 Киев (UTC+2)"), KeyboardButton(text="🇧🇾 Минск (UTC+3)")],
            [KeyboardButton(text="🇪🇺 Лондон (UTC+0)"), KeyboardButton(text="🇺🇸 Нью-Йорк (UTC-5)")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите часовой пояс"
    )
    return keyboard

def get_reminder_interval_keyboard(current_interval=1800, notifications_enabled=True):
    """
    Клавиатура для настройки интервала напоминаний с добавлением 5 секунд для тестов.
    """
    # Кнопка статуса
    status_text = "🔔 Вкл" if notifications_enabled else "🔕 Выкл"
    status_button = InlineKeyboardButton(
        text=status_text,
        callback_data="toggle_notif"
    )

    # Кнопки интервалов (по 3 в ряд)
    intervals = [
        [
            InlineKeyboardButton(text="5 сек", callback_data="interval_5"),
            InlineKeyboardButton(text="5 мин", callback_data="interval_300"),
            InlineKeyboardButton(text="15 мин", callback_data="interval_900")
        ],
        [
            InlineKeyboardButton(text="30 мин", callback_data="interval_1800"),
            InlineKeyboardButton(text="1 час", callback_data="interval_3600"),
            InlineKeyboardButton(text="2 часа", callback_data="interval_7200")
        ],
        [
            InlineKeyboardButton(text="4 часа", callback_data="interval_14400"),
            InlineKeyboardButton(text="8 часов", callback_data="interval_28800"),
            InlineKeyboardButton(text="🔕 Выкл", callback_data="interval_0")
        ],
        [status_button],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_settings")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=intervals)

def get_reminder_buttons_keyboard():
    """
    Клавиатура с кнопками выбора интервала для напоминаний (под сообщением с напоминанием).
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 мин", callback_data="remind_10"),
                InlineKeyboardButton(text="30 мин", callback_data="remind_30"),
                InlineKeyboardButton(text="1 час", callback_data="remind_60")
            ]
        ]
    )
    return keyboard

def get_activity_reminder_keyboard():
    """
    Клавиатура с кнопками выбора интервала уведомлений при смене активности.
    Только 10, 30 и 60 минут, без отключения уведомлений.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 мин", callback_data="activity_remind_10"),
                InlineKeyboardButton(text="30 мин", callback_data="activity_remind_30"),
                InlineKeyboardButton(text="1 час", callback_data="activity_remind_60")
            ]
        ]
    )
    return keyboard

def get_quiet_time_keyboard(quiet_enabled=True, start_time="22:00", end_time="06:00"):
    """
    Клавиатура настройки тихого времени.
    """
    # Кнопка статуса
    status_text = "🌙 Вкл" if quiet_enabled else "🌙 Выкл"
    status_button = InlineKeyboardButton(
        text=status_text,
        callback_data="toggle_quiet"
    )

    # Кнопки времени - теперь время прямо на кнопках
    time_buttons = [
        [
            InlineKeyboardButton(text=f"🕘 Начать: {start_time}", callback_data="set_quiet_start")
        ],
        [
            InlineKeyboardButton(text=f"🕖 Закончить: {end_time}", callback_data="set_quiet_end")
        ],
        [status_button],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_settings")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=time_buttons)

def get_clear_confirm_keyboard():
    """
    Клавиатура подтверждения очистки.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="clear_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="clear_no")
            ]
        ]
    )
    return keyboard

def get_timezone_back_keyboard():
    """
    Клавиатура для возврата из настроек часового пояса.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard