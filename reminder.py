"""
Модуль для напоминаний.
"""

import asyncio
from datetime import datetime
from aiogram import Bot
from database import (
    get_users_for_reminders,
    update_last_reminder_time,
    get_current_activity,
    get_user_settings,
    get_custom_activity
)
from config import ACTIVITIES
from utils import get_activity_emoji

class ReminderManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.task = None

    async def start(self):
        """Запуск менеджера напоминаний."""
        if self.is_running:
            return

        self.is_running = True
        self.task = asyncio.create_task(self._reminder_loop())
        print("✅ Напоминания запущены")

    async def stop(self):
        """Остановка менеджера напоминаний."""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        print("🛑 Напоминания остановлены")

    async def _reminder_loop(self):
        """Основной цикл напоминаний."""
        while self.is_running:
            try:
                users_to_remind = get_users_for_reminders()

                if users_to_remind:
                    print(f"📨 Отправка {len(users_to_remind)} напоминаний")

                for user_id, first_name, interval in users_to_remind:
                    try:
                        await self.send_reminder(user_id)
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        print(f"Ошибка отправки {user_id}: {e}")
                        continue

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ошибка в цикле: {e}")
                await asyncio.sleep(5)

    async def send_reminder(self, user_id: int):
        """
        Отправка напоминания с названием активности.
        """
        try:
            current_activity = get_current_activity(user_id)

            if current_activity:
                # Получаем название активности
                activity_type, start_time = current_activity

                # Проверяем кастомное название
                custom = get_custom_activity(user_id, activity_type)
                if custom and custom['custom_name'] and custom['emoji']:
                    activity_name = custom['custom_name']
                    emoji = custom['emoji']
                else:
                    activity_name = ACTIVITIES.get(activity_type, activity_type)
                    emoji = get_activity_emoji(activity_type)

                # Рассчитываем время
                start_time_dt = datetime.fromisoformat(start_time)
                duration = int((datetime.now() - start_time_dt).total_seconds())

                # Форматируем время
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                seconds = duration % 60

                if hours > 0:
                    time_str = f"{hours} час {minutes} мин {seconds} сек"
                elif minutes > 0:
                    time_str = f"{minutes} мин {seconds} сек"
                else:
                    time_str = f"{seconds} сек"

                # Отправляем сообщение с названием активности
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"{emoji} {activity_name}?\n{time_str}"
                )
            else:
                # Если нет активности - просто вопрос
                await self.bot.send_message(
                    chat_id=user_id,
                    text="❓ Чем занят?"
                )

            update_last_reminder_time(user_id)

        except Exception as e:
            print(f"Ошибка отправки: {e}")

    async def send_test_reminder(self, user_id: int):
        """
        Тестовое напоминание.
        """
        await self.send_reminder(user_id)