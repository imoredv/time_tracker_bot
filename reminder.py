"""
Модуль для напоминаний с поддержкой часовых поясов и привязкой к часам
Поддержка тестовых интервалов в 5 секунд...
"""

import asyncio
from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from database import (
    get_users_for_reminders,
    update_last_reminder_time,
    get_current_activity,
    get_user_settings,
    get_user_timezone
)
from config import ACTIVITIES
from utils import get_activity_emoji
from keyboards import get_reminder_buttons_keyboard

class ReminderManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.task = None
        self.user_next_reminder_time = {}  # Словарь для хранения времени следующего напоминания

    async def start(self):
        """Запуск менеджера напоминаний."""
        if self.is_running:
            return

        self.is_running = True
        self.task = asyncio.create_task(self._reminder_loop())
        print("✅ Напоминания запущены (с поддержкой часовых поясов и привязкой к часам, включая тестовые 5 секунд)")

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

    def _calculate_next_reminder_time(self, user_local_time: datetime, interval_seconds: int) -> datetime:
        """
        Расчет времени следующего напоминания.
        Для интервалов меньше 60 секунд - простая логика.
        Для интервалов 60+ секунд - привязка к минутам/часам.
        """
        # Для тестовых интервалов (5 секунд) используем простую логику
        if interval_seconds < 60:
            return user_local_time + timedelta(seconds=interval_seconds)

        # Для интервалов от минуты и больше - привязка к часам/минутам
        interval_minutes = interval_seconds // 60

        # Для интервалов меньше 30 минут - привязка к минутам
        if interval_minutes <= 30:
            current_minute = user_local_time.minute
            minutes_to_next = interval_minutes - (current_minute % interval_minutes)

            next_reminder = user_local_time.replace(
                second=0,
                microsecond=0
            ) + timedelta(minutes=minutes_to_next)
        else:
            # Для больших интервалов - просто добавляем интервал
            next_reminder = user_local_time + timedelta(seconds=interval_seconds)

        return next_reminder

    async def _reminder_loop(self):
        """Основной цикл напоминаний с учетом часовых поясов и привязкой к часам/секундам."""
        while self.is_running:
            try:
                users_to_remind = get_users_for_reminders()

                for user_id, first_name, interval, user_timezone in users_to_remind:
                    try:
                        # Получаем локальное время пользователя
                        try:
                            tz = pytz.timezone(user_timezone)
                            user_local_time = datetime.now(tz)
                        except:
                            user_local_time = datetime.now()

                        # Проверяем тихое время
                        settings = get_user_settings(user_id)
                        if settings and settings['quiet_time_enabled']:
                            quiet_start = settings['quiet_time_start']
                            quiet_end = settings['quiet_time_end']

                            if self._is_in_quiet_time(user_local_time, quiet_start, quiet_end):
                                continue

                        # Проверяем, нужно ли отправлять напоминание
                        cache_key = f"{user_id}_{interval}"

                        if cache_key not in self.user_next_reminder_time:
                            # Первое напоминание - рассчитываем время
                            next_reminder = self._calculate_next_reminder_time(user_local_time, interval)
                            self.user_next_reminder_time[cache_key] = next_reminder

                            # Если текущее время уже близко к следующему напоминанию, отправляем сразу
                            time_diff = (next_reminder - user_local_time).total_seconds()
                            if time_diff < 1:  # Меньше секунды до следующего напоминания
                                await self.send_reminder_with_buttons(user_id)
                                # Для тестовых интервалов (5 секунд) используем простую логику
                                if interval < 60:
                                    self.user_next_reminder_time[cache_key] = user_local_time + timedelta(seconds=interval)
                                else:
                                    self.user_next_reminder_time[cache_key] = self._calculate_next_reminder_time(user_local_time, interval)
                                update_last_reminder_time(user_id)
                        else:
                            next_reminder = self.user_next_reminder_time[cache_key]

                            # Проверяем, настало ли время напоминания
                            # Важно: приводим оба времени к одному типу (aware/naive)
                            if self._is_time_reached(user_local_time, next_reminder):
                                await self.send_reminder_with_buttons(user_id)
                                # Обновляем время следующего напоминания
                                if interval < 60:
                                    # Для тестовых интервалов (5 секунд)
                                    self.user_next_reminder_time[cache_key] = user_local_time + timedelta(seconds=interval)
                                else:
                                    # Для обычных интервалов
                                    self.user_next_reminder_time[cache_key] = self._calculate_next_reminder_time(user_local_time, interval)
                                update_last_reminder_time(user_id)

                    except Exception as e:
                        print(f"Ошибка обработки пользователя {user_id}: {e}")
                        continue

                # Очищаем старые записи из кэша
                self._clean_old_cache_entries()

                # Для тестовых интервалов проверяем чаще (каждую секунду)
                # Для обычных интервалов можно проверять реже
                has_short_intervals = any(interval < 60 for _, _, interval, _ in users_to_remind)
                sleep_time = 1 if has_short_intervals else 30
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ошибка в цикле напоминаний: {e}")
                await asyncio.sleep(5)

    def _is_time_reached(self, current_time, target_time):
        """
        Безопасное сравнение времени с учетом aware/naive типов.
        """
        try:
            # Если оба времени aware или оба naive - сравниваем напрямую
            if (current_time.tzinfo is not None and target_time.tzinfo is not None) or \
               (current_time.tzinfo is None and target_time.tzinfo is None):
                return current_time >= target_time
            else:
                # Если типы разные, приводим к aware
                if current_time.tzinfo is None and target_time.tzinfo is not None:
                    # Делаем current_time aware в той же временной зоне
                    return current_time.replace(tzinfo=target_time.tzinfo) >= target_time
                elif current_time.tzinfo is not None and target_time.tzinfo is None:
                    # Делаем target_time aware в той же временной зоне
                    return current_time >= target_time.replace(tzinfo=current_time.tzinfo)
        except Exception as e:
            print(f"Ошибка сравнения времени: {e}")
            return False

    def _clean_old_cache_entries(self):
        """Очистка старых записей из кэша времени напоминаний."""
        current_time = datetime.now(pytz.UTC)  # Используем UTC как базовое время
        keys_to_remove = []

        for key, next_reminder_time in self.user_next_reminder_time.items():
            try:
                # Приводим оба времени к одному типу для сравнения
                if next_reminder_time.tzinfo is None:
                    # Если время в кэше naive, делаем его aware в UTC
                    cache_time_aware = pytz.UTC.localize(next_reminder_time)
                else:
                    cache_time_aware = next_reminder_time

                # Если время напоминания прошло более чем сутки назад - удаляем
                if (current_time - cache_time_aware).total_seconds() > 86400:
                    keys_to_remove.append(key)
            except Exception as e:
                print(f"Ошибка очистки кэша для ключа {key}: {e}")
                keys_to_remove.append(key)

        for key in keys_to_remove:
            if key in self.user_next_reminder_time:
                del self.user_next_reminder_time[key]

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

    async def send_reminder_with_buttons(self, user_id: int):
        """
        Отправка напоминания с кнопками выбора интервала.
        """
        try:
            current_activity = get_current_activity(user_id)

            if current_activity:
                # Получаем название активности
                activity_type, start_time = current_activity
                activity_name = ACTIVITIES.get(activity_type, activity_type)
                emoji = get_activity_emoji(activity_type)

                # Рассчитываем время с использованием нового формата
                start_time_dt = datetime.fromisoformat(start_time)
                duration = int((datetime.now() - start_time_dt).total_seconds())

                # Форматируем как 19м:39с
                minutes = duration // 60
                seconds = duration % 60
                if minutes > 0:
                    time_str = f"{minutes}м:{seconds:02d}с"
                else:
                    time_str = f"{seconds}с"

                # Отправляем сообщение с кнопками
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"{emoji} {activity_name}?\n{time_str}\n\nУведомлять через:",
                    reply_markup=get_reminder_buttons_keyboard()
                )
            else:
                # Если нет активности
                await self.bot.send_message(
                    chat_id=user_id,
                    text="❓ Чем занят?\n\nУведомлять через:",
                    reply_markup=get_reminder_buttons_keyboard()
                )

        except Exception as e:
            print(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

    async def send_reminder(self, user_id: int):
        """
        Простое напоминание (без кнопок) для обратной совместимости.
        """
        await self.send_reminder_with_buttons(user_id)

    async def send_test_reminder(self, user_id: int):
        """
        Тестовое напоминание.
        """
        await self.send_reminder_with_buttons(user_id)