"""
Запуск бота для ботхост.ру
Простая версия без webhook проблем
"""

import asyncio
import sys
import os

# Добавляем путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import main

if __name__ == "__main__":
    print("🚀 Запуск Time Tracker Bot v4.3.1...")
    print("✅ Поддержка тестовых уведомлений 5 секунд")
    print("✅ Упрощенные интервалы при смене активности")
    print("✅ Исправленная статистика с графиками")
    print("=" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)