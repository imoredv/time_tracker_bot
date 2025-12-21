"""
Запуск бота для ботахост.ру
Простая версия без webhook проблем
"""

import asyncio
import sys
import os

# Добавляем путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import main

if __name__ == "__main__":
    print("🚀 Запуск Time Tracker Bot на ботахост.ру...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)