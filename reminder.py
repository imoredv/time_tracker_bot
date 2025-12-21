"""
Модуль для напоминаний с поддержкой часовых поясов.
"""

import asyncio
from datetime import datetime
import pytz
from aiogram import Bot
from database import (
    get_users_for_reminders,
    update_last_reminder_time,
    get_current_activity,
    get_user_settings,
    get_custom_activity,
    get_user_timezone
)
from config import ACTIVITIES
from utils import get_activity_emoji, get_user_local_time

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
        print("✅ Напоминания запущены (с поддержкой часовых поясов)")

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
        """Основной цикл напоминаний с учетом часовых поясов."""
        while self.is_running:
            try:
                users_to_remind = get_users_for_reminders()

                if users_to_remind:
                    print(f"📨 Проверка {len(users_to_remind)} пользователей для напоминаний")

                for user_id, first_name, interval, user_timezone in users_to_remind:
                    try:
                        # Проверяем локальное время пользователя
                        try:
                            tz = pytz.timezone(user_timezone)
                            user_local_time = datetime.now(tz)
                        except:
                            user_local_time = datetime.now()

                        # Проверяем, не в тихом ли времени пользователь
                        settings = get_user_settings(user_id)
                        if settings and settings['quiet_time_enabled']:
                            quiet_start = settings['quiet_time_start']
                            quiet_end = settings['quiet_time_end']

                            if self._is_in_quiet_time(user_local_time, quiet_start, quiet_end):
                                continue  # Пропускаем напоминание в тихое время

                        await self.send_reminder(user_id)
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        print(f"Ошибка отправки {user_id}: {e}")
                        continue

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ошибка в цикле напоминаний: {e}")
                await asyncio.sleep(5)

    def _is_in_quiet_time(self, local_time, quiet_start, quiet_end):
        """
        Проверка, находится ли локальное время в тихом времени.
        """
        current_hour = local_time.hour
        current_minute = local_time.minute

        def time_to_minutes(time_str):
            try:
                h, m = map(int, time_str.split(':'))
                return h * 60 + m
            except:
                return 0

        current_minutes = current_hour * 60 + current_minute
        start_minutes = time_to_minutes(quiet_start)
        end_minutes = time_to_minutes(quiet_end)

        # Проверка попадания в тихое время
        if start_minutes > end_minutes:
            # Ночное время (например, 22:00-06:00)
            if current_minutes >= start_minutes or current_minutes < end_minutes:
                return True
        else:
            # Дневное время
            if start_minutes <= current_minutes < end_minutes:
                return True

        return False

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
            print(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

    async def send_test_reminder(self, user_id: int):
        """
        Тестовое напоминание.
        """
        await self.send_reminder(user_id)