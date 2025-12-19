"""
Конфигурация.
"""

import os
import sys
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# Проверка токена
if BOT_TOKEN is None:
    print("❌ BOT_TOKEN не найден")
    sys.exit(1)

# Преобразование ADMIN_ID
try:
    if ADMIN_ID:
        ADMIN_ID = int(ADMIN_ID)
    else:
        ADMIN_ID = 0
except ValueError:
    ADMIN_ID = 0

print("✅ Конфигурация")
print(f"🤖 BOT_TOKEN: {'***установлен***' if BOT_TOKEN else '❌ отсутствует'}")
print(f"👑 ADMIN_ID: {ADMIN_ID}")

# Категории активностей
ACTIVITIES = {
    'work': 'Работа',
    'study': 'Учёба',
    'sport': 'Спорт',
    'hobby': 'Хобби',
    'sleep': 'Сон',
    'rest': 'Отдых'
}

# Настройки базы данных
DB_NAME = 'time_tracker.db'

# Настройки напоминаний
DEFAULT_REMINDER_INTERVAL = 30  # 30 минут по умолчанию