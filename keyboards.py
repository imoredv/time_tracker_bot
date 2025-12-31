# keyboards.py
"""
Клавиатуры с поддержкой часовых поясов..
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """
    Основная клавиатура - активности..
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

def get_main_keyboard_with_current(user_id):
    """
    Основная клавиатура - активности с отметкой текущей активности.
    СРАЗУ возвращает обновленную клавиатуру с галочкой.
    """
    from database import get_current_activity
    from utils import get_activity_emoji

    current_activity = get_current_activity(user_id)

    # Определяем текущую активность пользователя
    current_activity_type = None
    if current_activity:
        current_activity_type = current_activity[0]

    # Создаем кнопки с отметкой текущей активности
    activity_buttons = {
        "work": ("💼 Труд", "💼 Труд ✅"),
        "study": ("📚 Учёба", "📚 Учёба ✅"),
        "sport": ("🏃 Спорт", "🏃 Спорт ✅"),
        "hobby": ("🎨 Хобби", "🎨 Хобби ✅"),
        "sleep": ("💤 Сон", "💤 Сон ✅"),
        "rest": ("☕️ Отдых", "☕️ Отдых ✅")
    }

    # Создаем строки клавиатуры
    keyboard_rows = []

    # Первая строка: Труд и Учёба
    row1 = []
    for activity_type in ["work", "study"]:
        button_text = activity_buttons[activity_type][1] if current_activity_type == activity_type else activity_buttons[activity_type][0]
        row1.append(KeyboardButton(text=button_text))
    keyboard_rows.append(row1)

    # Вторая строка: Спорт и Хобби
    row2 = []
    for activity_type in ["sport", "hobby"]:
        button_text = activity_buttons[activity_type][1] if current_activity_type == activity_type else activity_buttons[activity_type][0]
        row2.append(KeyboardButton(text=button_text))
    keyboard_rows.append(row2)

    # Третья строка: Сон и Отдых
    row3 = []
    for activity_type in ["sleep", "rest"]:
        button_text = activity_buttons[activity_type][1] if current_activity_type == activity_type else activity_buttons[activity_type][0]
        row3.append(KeyboardButton(text=button_text))
    keyboard_rows.append(row3)

    # Четвертая строка: Статистика и Настройки
    keyboard_rows.append([
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="⚙️ Настройки")
    ])

    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
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

def get_reminder_buttons_keyboard(current_interval_minutes=None):
    """
    Клавиатура с кнопками выбора интервала для напоминаний (под сообщением с напоминанием).
    С зеленой галочкой напротив текущего интервала.
    """
    intervals = [15, 30, 60, 120, 240, 480]

    # Создаем кнопки с галочками
    buttons = []
    for i in range(0, len(intervals), 3):  # По 3 кнопки в ряд
        row = []
        for interval in intervals[i:i+3]:
            button_text = f"{interval} мин"
            if current_interval_minutes and interval == current_interval_minutes:
                button_text += " ✅"
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"remind_{interval}"
            ))
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_activity_reminder_keyboard(current_interval_minutes=None):
    """
    Клавиатура с кнопками выбора интервала уведомлений при смене активности.
    С зеленой галочкой напротив текущего интервала.
    """
    intervals = [15, 30, 60, 120, 240, 480]

    # Создаем кнопки с галочками
    buttons = []
    for i in range(0, len(intervals), 3):  # По 3 кнопки в ряд
        row = []
        for interval in intervals[i:i+3]:
            button_text = f"{interval} мин"
            if current_interval_minutes and interval == current_interval_minutes:
                button_text += " ✅"
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"activity_remind_{interval}"
            ))
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

def get_enhanced_timezone_keyboard():
    """
    Улучшенная клавиатура для выбора часового пояса.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Поиск по городу", callback_data="tz_search"),
            InlineKeyboardButton(text="⏱️ Проверить время", callback_data="tz_check_time")
        ],
        [
            InlineKeyboardButton(text="🌍 По странам", callback_data="tz_search_country"),
            InlineKeyboardButton(text="📋 Полный список", callback_data="tz_show_all")
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Россия", callback_data="tz_country_rus"),
            InlineKeyboardButton(text="🇺🇸 США", callback_data="tz_country_usa")
        ],
        [
            InlineKeyboardButton(text="🇪🇺 Европа", callback_data="tz_group_Европа"),
            InlineKeyboardButton(text="🌏 Азия", callback_data="tz_group_Азия")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="tz_back_to_settings")
        ]
    ])
    return keyboard

def get_simple_start_timezone_keyboard():
    """
    Простая клавиатура для выбора часового пояса при старте.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📍 Ввести город", callback_data="tz_city_input"),
                InlineKeyboardButton(text="⏱️ Ввести UTC", callback_data="tz_utc_input")
            ],
            [
                InlineKeyboardButton(text="🇷🇺 Москва", callback_data="tz_select_Russian Standard Time"),
                InlineKeyboardButton(text="🇺🇦 Киев", callback_data="tz_select_FLE Standard Time")
            ],
            [
                InlineKeyboardButton(text="🇧🇾 Минск", callback_data="tz_select_Belarus Standard Time"),
                InlineKeyboardButton(text="🇺🇸 Нью-Йорк", callback_data="tz_select_Eastern Standard Time")
            ],
            [
                InlineKeyboardButton(text="🇪🇺 Лондон", callback_data="tz_select_GMT Standard Time"),
                InlineKeyboardButton(text="🗺️ Все пояса", callback_data="tz_show_all")
            ]
        ]
    )
    return keyboard

def get_timezone_main_keyboard():
    """
    Основная клавиатура для выбора часового пояса.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти город", callback_data="tz_search_city"),
                InlineKeyboardButton(text="⏱️ Смещение UTC", callback_data="tz_search_offset")
            ],
            [
                InlineKeyboardButton(text="🕐 Ввести время", callback_data="tz_input_time"),
                InlineKeyboardButton(text="🌍 По странам", callback_data="tz_search_country")
            ],
            [
                InlineKeyboardButton(text="🇷🇺 Россия", callback_data="tz_country_rus"),
                InlineKeyboardButton(text="🇺🇸 США", callback_data="tz_country_usa")
            ],
            [
                InlineKeyboardButton(text="🇪🇺 Европа", callback_data="tz_group_Европа"),
                InlineKeyboardButton(text="🌏 Азия", callback_data="tz_group_Азия")
            ],
            [
                InlineKeyboardButton(text="📋 Полный список", callback_data="tz_show_all"),
                InlineKeyboardButton(text="🚀 Москва (UTC+3)", callback_data="tz_select_Russian Standard Time")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="tz_cancel")
            ]
        ]
    )

def get_timezone_search_keyboard():
    """
    Клавиатура для поиска часового пояса.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📍 Поиск по городу", callback_data="tz_search_city"),
            InlineKeyboardButton(text="⏱️ По смещению UTC", callback_data="tz_search_offset")
        ],
        [
            InlineKeyboardButton(text="🌍 По странам", callback_data="tz_search_country"),
            InlineKeyboardButton(text="📋 Полный список", callback_data="tz_show_all")
        ],
        [
            InlineKeyboardButton(text="🕐 Проверить по времени", callback_data="tz_input_time")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="tz_cancel")
        ]
    ])

def get_timezone_with_time_keyboard():
    """
    Клавиатура для выбора часового пояса с проверкой времени.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Россия", callback_data="tz_country_rus"),
            InlineKeyboardButton(text="🇪🇺 Европа", callback_data="tz_country_eu")
        ],
        [
            InlineKeyboardButton(text="🇺🇸 США/Канада", callback_data="tz_country_usa"),
            InlineKeyboardButton(text="🌏 Азия", callback_data="tz_country_asia")
        ],
        [
            InlineKeyboardButton(text="🔍 Поиск", callback_data="tz_search_again"),
            InlineKeyboardButton(text="📋 Список", callback_data="tz_show_all")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="tz_cancel")
        ]
    ])

def get_simple_timezone_keyboard():
    """Простая клавиатура часового пояса."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📍 Город", callback_data="tz_search_city"),
            InlineKeyboardButton(text="⏱️ UTC", callback_data="tz_search_offset")
        ],
        [
            InlineKeyboardButton(text="🗺️ Список", callback_data="tz_show_offsets")
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Москва", callback_data="tz_select_Europe/Moscow"),
            InlineKeyboardButton(text="🇺🇦 Киев", callback_data="tz_select_Europe/Kiev")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="tz_back_to_settings")
        ]
    ])

def get_simple_settings_timezone_keyboard():
    """
    Простая клавиатура для смены часового пояса в настройках.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📍 Ввести город", callback_data="tz_city_input"),
                InlineKeyboardButton(text="⏱️ Ввести UTC", callback_data="tz_utc_input")
            ],
            [
                InlineKeyboardButton(text="🇷🇺 Москва", callback_data="tz_select_Russian Standard Time"),
                InlineKeyboardButton(text="🇺🇦 Киев", callback_data="tz_select_FLE Standard Time")
            ],
            [
                InlineKeyboardButton(text="🇧🇾 Минск", callback_data="tz_select_Belarus Standard Time"),
                InlineKeyboardButton(text="🇺🇸 Нью-Йорк", callback_data="tz_select_Eastern Standard Time")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="tz_back_settings")
            ]
        ]
    )
    return keyboard

def get_utc_offsets_keyboard():
    """
    Клавиатура с выбором смещения UTC.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="UTC-12", callback_data="tz_utc_-12"),
                InlineKeyboardButton(text="UTC-8", callback_data="tz_utc_-8"),
                InlineKeyboardButton(text="UTC-5", callback_data="tz_utc_-5")
            ],
            [
                InlineKeyboardButton(text="UTC-3", callback_data="tz_utc_-3"),
                InlineKeyboardButton(text="UTC+0", callback_data="tz_utc_0"),
                InlineKeyboardButton(text="UTC+3", callback_data="tz_utc_+3")
            ],
            [
                InlineKeyboardButton(text="UTC+5", callback_data="tz_utc_+5"),
                InlineKeyboardButton(text="UTC+8", callback_data="tz_utc_+8"),
                InlineKeyboardButton(text="UTC+12", callback_data="tz_utc_+12")
            ],
            [
                InlineKeyboardButton(text="🔍 Поиск", callback_data="tz_search_again"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="tz_back_to_simple")
            ]
        ]
    )
    return keyboard