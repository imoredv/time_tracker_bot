"""
Упрощенный менеджер часовых поясов для Time Tracker Bot
"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple
import pytz


class SimpleTimezoneManager:
    """Упрощенный менеджер для работы с часовыми поясами."""

    def __init__(self):
        # Основной словарь часовых поясов
        self.timezones = {
            "(UTC-12:00) Линия перемены дат": "Dateline Standard Time",
            "(UTC-11:00) Время в формате UTC -11": "UTC-11",
            "(UTC-10:00) Гавайи": "Hawaiian Standard Time",
            "(UTC-09:00) Аляска": "Alaskan Standard Time",
            "(UTC-08:00) Тихоокеанское время (США и Канада)": "Pacific Standard Time",
            "(UTC-07:00) Горное время (США и Канада)": "Mountain Standard Time",
            "(UTC-06:00) Центральное время (США и Канада)": "Central Standard Time",
            "(UTC-05:00) Восточное время (США и Канада)": "Eastern Standard Time",
            "(UTC-04:00) Атлантическое время (Канада)": "Atlantic Standard Time",
            "(UTC-03:30) Ньюфаундленд": "Newfoundland Standard Time",
            "(UTC-03:00) Бразилия": "E. South America Standard Time",
            "(UTC-02:00) Время в формате UTC -02": "UTC-02",
            "(UTC-01:00) Азорские о-ва": "Azores Standard Time",
            "(UTC+00:00) Лондон, Дублин": "GMT Standard Time",
            "(UTC+01:00) Берлин, Париж, Рим": "W. Europe Standard Time",
            "(UTC+02:00) Афины, Киев, Хельсинки": "FLE Standard Time",
            "(UTC+03:00) Москва, Санкт-Петербург, Минск": "Russian Standard Time",
            "(UTC+03:30) Тегеран": "Iran Standard Time",
            "(UTC+04:00) Дубай, Баку": "Arabian Standard Time",
            "(UTC+04:30) Кабул": "Afghanistan Standard Time",
            "(UTC+05:00) Екатеринбург, Ташкент": "West Asia Standard Time",
            "(UTC+05:30) Индия (Дели, Мумбаи)": "India Standard Time",
            "(UTC+06:00) Омск, Алматы": "Central Asia Standard Time",
            "(UTC+06:30) Янгон": "Myanmar Standard Time",
            "(UTC+07:00) Красноярск, Бангкок": "SE Asia Standard Time",
            "(UTC+08:00) Иркутск, Пекин, Сингапур": "China Standard Time",
            "(UTC+09:00) Якутск, Токио, Сеул": "Tokyo Standard Time",
            "(UTC+09:30) Аделаида": "Cen. Australia Standard Time",
            "(UTC+10:00) Владивосток, Сидней": "AUS Eastern Standard Time",
            "(UTC+11:00) Магадан": "Magadan Standard Time",
            "(UTC+12:00) Камчатка, Веллингтон": "New Zealand Standard Time",
            "(UTC+13:00) Время в формате UTC +13": "UTC+13",
            "(UTC+14:00) О-в Киритимати": "Line Islands Standard Time",
        }

        # Словарь для быстрого поиска по городам
        self.city_to_tz = self._build_city_dict()

    def _build_city_dict(self) -> Dict[str, str]:
        """Строит словарь для поиска по городам."""
        city_dict = {}

        # Основные города и их часовые пояса
        popular_cities = {
            # Русские названия
            'москва': 'Russian Standard Time',
            'санкт-петербург': 'Russian Standard Time',
            'питер': 'Russian Standard Time',
            'спб': 'Russian Standard Time',
            'киев': 'FLE Standard Time',
            'минск': 'Belarus Standard Time',
            'алматы': 'Central Asia Standard Time',
            'астана': 'Central Asia Standard Time',
            'екатеринбург': 'West Asia Standard Time',
            'екб': 'West Asia Standard Time',
            'новосибирск': 'N. Central Asia Standard Time',
            'омск': 'Central Asia Standard Time',
            'красноярск': 'SE Asia Standard Time',
            'иркутск': 'China Standard Time',
            'якутск': 'Tokyo Standard Time',
            'владивосток': 'AUS Eastern Standard Time',
            'магадан': 'Magadan Standard Time',
            'камчатка': 'New Zealand Standard Time',

            # Английские названия
            'moscow': 'Russian Standard Time',
            'london': 'GMT Standard Time',
            'new york': 'Eastern Standard Time',
            'los angeles': 'Pacific Standard Time',
            'paris': 'W. Europe Standard Time',
            'berlin': 'W. Europe Standard Time',
            'tokyo': 'Tokyo Standard Time',
            'beijing': 'China Standard Time',
            'sydney': 'AUS Eastern Standard Time',
            'dubai': 'Arabian Standard Time',
        }

        city_dict.update(popular_cities)

        # Добавляем города из основного словаря
        for display_name, tz_code in self.timezones.items():
            if ') ' in display_name:
                cities_part = display_name.split(') ')[1]
                cities = [city.strip().lower() for city in cities_part.split(',')]
                for city in cities:
                    if city and city not in city_dict:
                        city_dict[city] = tz_code

        return city_dict

    def parse_input(self, user_input: str) -> Tuple[Optional[str], str]:
        """Парсит ввод пользователя и возвращает часовой пояс."""
        user_input = user_input.strip().lower()

        if not user_input:
            return None, "Пустой ввод"

        # 1. Проверяем смещение UTC
        utc_match = re.match(r'^([+-]?\d{1,2})(?::(\d{2}))?$', user_input)
        if not utc_match:
            utc_match = re.match(r'^utc([+-]?\d{1,2})(?::(\d{2}))?$', user_input)

        if utc_match:
            hours = utc_match.group(1)
            minutes = utc_match.group(2) or '00'

            # Ищем подходящий часовой пояс
            best_match = None
            best_diff = float('inf')

            for display_name, tz_code in self.timezones.items():
                match = re.search(r'\(UTC([+-]\d{1,2}):?(\d{2})?\)', display_name)
                if match:
                    tz_hours = int(match.group(1))
                    tz_minutes = int(match.group(2) or '00')

                    input_hours = int(hours)
                    input_minutes = int(minutes)

                    diff = abs((input_hours * 60 + input_minutes) - (tz_hours * 60 + tz_minutes))

                    if diff < best_diff:
                        best_diff = diff
                        best_match = (display_name, tz_code)

            if best_match and best_diff <= 60:
                display_name, tz_code = best_match
                return tz_code, f"Часовой пояс: {display_name}"

        # 2. Проверяем по городу
        if user_input in self.city_to_tz:
            tz_code = self.city_to_tz[user_input]
            for display_name, code in self.timezones.items():
                if code == tz_code:
                    return tz_code, f"Часовой пояс: {display_name}"

        # 3. Частичное совпадение по городу
        for city, tz_code in self.city_to_tz.items():
            if user_input in city:
                for display_name, code in self.timezones.items():
                    if code == tz_code:
                        return tz_code, f"Часовой пояс: {display_name}"

        return None, "Часовой пояс не найден. Попробуйте другой город или смещение UTC."

    def get_timezone_display_name(self, tz_code: str) -> str:
        """Получение отображаемого имени часового пояса."""
        for display_name, code in self.timezones.items():
            if code == tz_code:
                return display_name
        return tz_code

    def get_current_time_in_timezone(self, tz_code: str) -> str:
        """Получение текущего времени в указанном часовом поясе."""
        try:
            # Преобразуем код часового пояса в формат pytz
            tz_mapping = {
                'Russian Standard Time': 'Europe/Moscow',
                'FLE Standard Time': 'Europe/Kiev',
                'Belarus Standard Time': 'Europe/Minsk',
                'GMT Standard Time': 'Europe/London',
                'W. Europe Standard Time': 'Europe/Berlin',
                'Eastern Standard Time': 'America/New_York',
                'Pacific Standard Time': 'America/Los_Angeles',
                'China Standard Time': 'Asia/Shanghai',
                'Tokyo Standard Time': 'Asia/Tokyo',
                'AUS Eastern Standard Time': 'Australia/Sydney',
            }

            pytz_tz = tz_mapping.get(tz_code, 'UTC')
            tz = pytz.timezone(pytz_tz)
            return datetime.now(tz).strftime("%H:%M")
        except:
            return "ошибка"


# Глобальный экземпляр
timezone_manager = SimpleTimezoneManager()