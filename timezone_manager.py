"""
Менеджер часовых поясов для Time Tracker Bot.
"""

import pytz
from datetime import datetime
from typing import Dict, List
import requests


class TimezoneManager:
    def __init__(self):
        self.common_timezones = {
            '🇷🇺 Москва (UTC+3)': 'Europe/Moscow',
            '🇷🇺 Калининград (UTC+2)': 'Europe/Kaliningrad',
            '🇷🇺 Самара (UTC+4)': 'Europe/Samara',
            '🇷🇺 Екатеринбург (UTC+5)': 'Asia/Yekaterinburg',
            '🇷🇺 Омск (UTC+6)': 'Asia/Omsk',
            '🇷🇺 Красноярск (UTC+7)': 'Asia/Krasnoyarsk',
            '🇷🇺 Иркутск (UTC+8)': 'Asia/Irkutsk',
            '🇷🇺 Якутск (UTC+9)': 'Asia/Yakutsk',
            '🇷🇺 Владивосток (UTC+10)': 'Asia/Vladivostok',
            '🇷🇺 Магадан (UTC+11)': 'Asia/Magadan',
            '🇷🇺 Камчатка (UTC+12)': 'Asia/Kamchatka',
            '🇺🇦 Киев (UTC+2)': 'Europe/Kiev',
            '🇧🇾 Минск (UTC+3)': 'Europe/Minsk',
            '🇪🇺 Лондон (UTC+0)': 'Europe/London',
            '🇪🇺 Берлин (UTC+1)': 'Europe/Berlin',
            '🇺🇸 Нью-Йорк (UTC-5)': 'America/New_York',
            '🇺🇸 Лос-Анджелес (UTC-8)': 'America/Los_Angeles',
            '🇨🇳 Пекин (UTC+8)': 'Asia/Shanghai',
            '🇯🇵 Токио (UTC+9)': 'Asia/Tokyo',
            '🌍 UTC (Гринвич)': 'UTC'
        }

    def get_timezone_keyboard(self) -> List[List[str]]:
        """
        Получение списка часовых поясов для клавиатуры.
        """
        timezones = list(self.common_timezones.keys())
        keyboard = []

        # Разбиваем на строки по 2 кнопки
        for i in range(0, len(timezones), 2):
            row = timezones[i:i + 2]
            keyboard.append(row)

        return keyboard

    def detect_by_ip(self) -> str:
        """
        Определение часового пояса по IP через API.
        """
        try:
            # Бесплатный API для определения часового пояса по IP
            response = requests.get('http://ip-api.com/json/', timeout=3)
            if response.status_code == 200:
                data = response.json()
                timezone = data.get('timezone', 'UTC')
                print(f"✅ Определен часовой пояс по IP: {timezone}")
                return timezone
        except Exception as e:
            print(f"⚠️ Не удалось определить часовой пояс по IP: {e}")

        # Резервный вариант - по языку браузера/системы
        return 'Europe/Moscow'  # По умолчанию для русскоязычных

    def get_user_friendly_timezones(self) -> Dict[str, str]:
        """
        Получение словаря "читабельное название -> IANA код".
        """
        return self.common_timezones

    def validate_timezone(self, timezone_str: str) -> bool:
        """
        Проверка валидности часового пояса.
        """
        try:
            pytz.timezone(timezone_str)
            return True
        except pytz.UnknownTimeZoneError:
            return False

    def get_current_time_in_timezone(self, timezone_str: str) -> str:
        """
        Получение текущего времени в указанном часовом поясе.
        """
        try:
            tz = pytz.timezone(timezone_str)
            return datetime.now(tz).strftime("%H:%M")
        except:
            return "ошибка"

    def get_offset_hours(self, timezone_str: str) -> int:
        """
        Получение смещения часового пояса от UTC в часах..
        """
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            offset = now.utcoffset()
            if offset:
                return int(offset.total_seconds() / 3600)
        except:
            pass
        return 0


# Создаем глобальный экземпляр менеджера
timezone_manager = TimezoneManager()