"""
Менеджер часовых поясов для Time Tracker Bot.
"""

import pytz
from datetime import datetime
from typing import Dict, List, Optional
import requests
import locale
import hashlib
import time

class TimezoneManager:
    def __init__(self):
        self.ip_cache = {}
        self.cache_timeout = 3600  # 1 час кэширования

        # Полный список часовых поясов с группировкой по регионам
        self.common_timezones = {
            # Россия
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

            # Украина и Беларусь
            '🇺🇦 Киев (UTC+2)': 'Europe/Kiev',
            '🇧🇾 Минск (UTC+3)': 'Europe/Minsk',

            # Европа
            '🇪🇺 Лондон (UTC+0)': 'Europe/London',
            '🇪🇺 Берлин (UTC+1)': 'Europe/Berlin',
            '🇪🇺 Париж (UTC+1)': 'Europe/Paris',
            '🇪🇺 Мадрид (UTC+1)': 'Europe/Madrid',
            '🇪🇺 Рим (UTC+1)': 'Europe/Rome',
            '🇪🇺 Афины (UTC+2)': 'Europe/Athens',
            '🇪🇺 Хельсинки (UTC+2)': 'Europe/Helsinki',

            # Америка
            '🇺🇸 Нью-Йорк (UTC-5)': 'America/New_York',
            '🇺🇸 Лос-Анджелес (UTC-8)': 'America/Los_Angeles',
            '🇺🇸 Чикаго (UTC-6)': 'America/Chicago',
            '🇺🇸 Денвер (UTC-7)': 'America/Denver',
            '🇨🇦 Торонто (UTC-5)': 'America/Toronto',
            '🇨🇦 Ванкувер (UTC-8)': 'America/Vancouver',
            '🇧🇷 Сан-Паулу (UTC-3)': 'America/Sao_Paulo',
            '🇦🇷 Буэнос-Айрес (UTC-3)': 'America/Argentina/Buenos_Aires',

            # Азия
            '🇨🇳 Пекин (UTC+8)': 'Asia/Shanghai',
            '🇯🇵 Токио (UTC+9)': 'Asia/Tokyo',
            '🇰🇷 Сеул (UTC+9)': 'Asia/Seoul',
            '🇸🇬 Сингапур (UTC+8)': 'Asia/Singapore',
            '🇮🇳 Дели (UTC+5:30)': 'Asia/Kolkata',
            '🇮🇩 Джакарта (UTC+7)': 'Asia/Jakarta',
            '🇹🇭 Бангкок (UTC+7)': 'Asia/Bangkok',
            '🇻🇳 Ханой (UTC+7)': 'Asia/Ho_Chi_Minh',

            # Австралия и Океания
            '🇦🇺 Сидней (UTC+10)': 'Australia/Sydney',
            '🇦🇺 Перт (UTC+8)': 'Australia/Perth',
            '🇳🇿 Окленд (UTC+12)': 'Pacific/Auckland',

            # Африка
            '🇿🇦 Йоханнесбург (UTC+2)': 'Africa/Johannesburg',
            '🇪🇬 Каир (UTC+2)': 'Africa/Cairo',
            '🇳🇬 Лагос (UTC+1)': 'Africa/Lagos',
            '🇰🇪 Найроби (UTC+3)': 'Africa/Nairobi',

            # Ближний Восток
            '🇦🇪 Дубай (UTC+4)': 'Asia/Dubai',
            '🇸🇦 Эр-Рияд (UTC+3)': 'Asia/Riyadh',
            '🇮🇱 Тель-Авив (UTC+2)': 'Asia/Jerusalem',
            '🇹🇷 Стамбул (UTC+3)': 'Europe/Istanbul',

            # UTC и стандартные
            '🌍 UTC (Гринвич)': 'UTC',
            '🌍 UTC-12': 'Etc/GMT+12',
            '🌍 UTC-11': 'Etc/GMT+11',
            '🌍 UTC-10': 'Etc/GMT+10',
            '🌍 UTC-9': 'Etc/GMT+9',
            '🌍 UTC-8': 'Etc/GMT+8',
            '🌍 UTC-7': 'Etc/GMT+7',
            '🌍 UTC-6': 'Etc/GMT+6',
            '🌍 UTC-5': 'Etc/GMT+5',
            '🌍 UTC-4': 'Etc/GMT+4',
            '🌍 UTC-3': 'Etc/GMT+3',
            '🌍 UTC-2': 'Etc/GMT+2',
            '🌍 UTC-1': 'Etc/GMT+1',
            '🌍 UTC+0': 'Etc/GMT',
            '🌍 UTC+1': 'Etc/GMT-1',
            '🌍 UTC+2': 'Etc/GMT-2',
            '🌍 UTC+3': 'Etc/GMT-3',
            '🌍 UTC+4': 'Etc/GMT-4',
            '🌍 UTC+5': 'Etc/GMT-5',
            '🌍 UTC+6': 'Etc/GMT-6',
            '🌍 UTC+7': 'Etc/GMT-7',
            '🌍 UTC+8': 'Etc/GMT-8',
            '🌍 UTC+9': 'Etc/GMT-9',
            '🌍 UTC+10': 'Etc/GMT-10',
            '🌍 UTC+11': 'Etc/GMT-11',
            '🌍 UTC+12': 'Etc/GMT-12',
        }

    def _get_cache_key(self, ip: str = "") -> str:
        """Генерация ключа для кэша."""
        if ip:
            return hashlib.md5(ip.encode()).hexdigest()
        return "default"

    def detect_by_ip(self, force_refresh=False) -> str:
        """
        Определение часового пояса по IP.
        На ботахост.ру определяет IP сервера, поэтому используем кэширование.
        """
        # На ботахост.ру IP сервера всегда один, поэтому кэшируем результат
        cache_key = self._get_cache_key("server_ip")

        # Проверяем кэш (не заставляем обновлять принудительно, если уже есть)
        if not force_refresh and cache_key in self.ip_cache:
            cached_time, timezone = self.ip_cache[cache_key]
            # Кэш на 24 часа для сервера
            if time.time() - cached_time < 86400:
                print(f"✅ Часовой пояс из кэша: {timezone}")
                return timezone

        # Пробуем определить по IP через API
        try:
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                timezone = data.get('timezone', 'UTC')

                # Проверяем, не серверный ли это IP (обычные проверки для ботахост.ру)
                if 'krasnoyarsk' in timezone.lower() or 'novosibirsk' in timezone.lower():
                    # Это сервер ботахост.ру, предлагаем популярные часовые пояса
                    print(f"⚠️ Определен серверный часовой пояс: {timezone}")
                    # Возвращаем Москву как наиболее вероятный для русскоязычных пользователей
                    timezone = 'Europe/Moscow'

                # Сохраняем в кэш
                self.ip_cache[cache_key] = (time.time(), timezone)
                print(f"✅ Определен часовой пояс по IP: {timezone}")
                return timezone
        except Exception as e:
            print(f"⚠️ Не удалось определить часовой пояс по IP: {e}")

        # Fallback: определяем по локали системы
        return self.detect_by_locale()

    def detect_by_locale(self) -> str:
        """
        Определение часового пояса по локали системы.
        """
        try:
            # Получаем локаль системы
            system_locale = locale.getdefaultlocale()[0] or ''

            # Маппинг локалей на часовые пояса
            locale_to_timezone = {
                'ru_RU': 'Europe/Moscow',
                'uk_UA': 'Europe/Kiev',
                'be_BY': 'Europe/Minsk',
                'en_US': 'America/New_York',
                'en_GB': 'Europe/London',
                'de_DE': 'Europe/Berlin',
                'fr_FR': 'Europe/Paris',
                'es_ES': 'Europe/Madrid',
                'it_IT': 'Europe/Rome',
                'pl_PL': 'Europe/Warsaw',
                'zh_CN': 'Asia/Shanghai',
                'ja_JP': 'Asia/Tokyo',
                'ko_KR': 'Asia/Seoul',
                'tr_TR': 'Europe/Istanbul',
                'ar_SA': 'Asia/Riyadh',
                'hi_IN': 'Asia/Kolkata',
                'pt_BR': 'America/Sao_Paulo',
            }

            for locale_prefix, timezone in locale_to_timezone.items():
                if system_locale.startswith(locale_prefix[:2]):
                    print(f"✅ Определен часовой пояс по локали {system_locale}: {timezone}")
                    return timezone

        except Exception as e:
            print(f"⚠️ Не удалось определить часовой пояс по локали: {e}")

        # Резервный вариант - по умолчанию
        default_tz = 'Europe/Moscow'
        print(f"⚠️ Используется часовой пояс по умолчанию: {default_tz}")
        return default_tz

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
        Получение смещения часового пояса от UTC в часах.
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

    def get_grouped_timezones(self) -> Dict[str, List[str]]:
        """
        Получение сгруппированных часовых поясов по регионам.
        """
        grouped = {
            'Россия': [],
            'Украина и Беларусь': [],
            'Европа': [],
            'Америка': [],
            'Азия': [],
            'Австралия и Океания': [],
            'Африка': [],
            'Ближний Восток': [],
            'UTC и стандартные': []
        }

        for display_name in self.common_timezones.keys():
            if '🇷🇺' in display_name:
                grouped['Россия'].append(display_name)
            elif '🇺🇦' in display_name or '🇧🇾' in display_name:
                grouped['Украина и Беларусь'].append(display_name)
            elif '🇪🇺' in display_name:
                grouped['Европа'].append(display_name)
            elif '🇺🇸' in display_name or '🇨🇦' in display_name or '🇧🇷' in display_name or '🇦🇷' in display_name:
                grouped['Америка'].append(display_name)
            elif '🇨🇳' in display_name or '🇯🇵' in display_name or '🇰🇷' in display_name or '🇸🇬' in display_name or '🇮🇳' in display_name or '🇮🇩' in display_name or '🇹🇭' in display_name or '🇻🇳' in display_name:
                grouped['Азия'].append(display_name)
            elif '🇦🇺' in display_name or '🇳🇿' in display_name:
                grouped['Австралия и Океания'].append(display_name)
            elif '🇿🇦' in display_name or '🇪🇬' in display_name or '🇳🇬' in display_name or '🇰🇪' in display_name:
                grouped['Африка'].append(display_name)
            elif '🇦🇪' in display_name or '🇸🇦' in display_name or '🇮🇱' in display_name or '🇹🇷' in display_name:
                grouped['Ближний Восток'].append(display_name)
            elif '🌍' in display_name:
                grouped['UTC и стандартные'].append(display_name)

        return grouped


def detect_by_user_info(self, language_code: str = None, user_agent: str = None) -> str:
    """
    Определение часового пояса по информации о пользователе.
    """
    # Сначала пробуем по языку
    if language_code:
        lang_to_timezone = {
            'ru': 'Europe/Moscow',
            'en': 'America/New_York',  # Для англ. по умолчанию США
            'en-gb': 'Europe/London',
            'en-us': 'America/New_York',
            'uk': 'Europe/Kiev',
            'be': 'Europe/Minsk',
            'de': 'Europe/Berlin',
            'fr': 'Europe/Paris',
            'es': 'Europe/Madrid',
            'es-es': 'Europe/Madrid',
            'es-mx': 'America/Mexico_City',
            'it': 'Europe/Rome',
            'pl': 'Europe/Warsaw',
            'zh': 'Asia/Shanghai',
            'zh-cn': 'Asia/Shanghai',
            'zh-tw': 'Asia/Taipei',
            'ja': 'Asia/Tokyo',
            'ko': 'Asia/Seoul',
            'ar': 'Asia/Riyadh',
            'tr': 'Europe/Istanbul',
            'pt': 'America/Sao_Paulo',
            'pt-br': 'America/Sao_Paulo',
            'pt-pt': 'Europe/Lisbon',
            'nl': 'Europe/Amsterdam',
            'sv': 'Europe/Stockholm',
            'no': 'Europe/Oslo',
            'da': 'Europe/Copenhagen',
            'fi': 'Europe/Helsinki',
            'cs': 'Europe/Prague',
            'hu': 'Europe/Budapest',
            'ro': 'Europe/Bucharest',
            'bg': 'Europe/Sofia',
            'el': 'Europe/Athens',
            'he': 'Asia/Jerusalem',
        }

        # Приводим к нижнему регистру
        lang = language_code.lower()

        # Пробуем полный код языка
        if lang in lang_to_timezone:
            print(f"✅ Определен часовой пояс по языку {lang}: {lang_to_timezone[lang]}")
            return lang_to_timezone[lang]

        # Пробуем первые 2 символа
        lang_prefix = lang[:2] if len(lang) >= 2 else lang
        for lang_key, tz in lang_to_timezone.items():
            if lang_key.startswith(lang_prefix):
                print(f"✅ Определен часовой пояс по префиксу языка {lang_prefix}: {tz}")
                return tz

    # Если не удалось по языку, пробуем по user-agent
    if user_agent:
        # Парсим user-agent для определения региона
        if 'windows' in user_agent.lower():
            # Windows часто показывает локаль системы
            if '; ru' in user_agent or 'ru-ru' in user_agent:
                return 'Europe/Moscow'
            elif '; en-us' in user_agent:
                return 'America/New_York'
            elif '; en-gb' in user_agent:
                return 'Europe/London'
            elif '; de' in user_agent:
                return 'Europe/Berlin'
            elif '; fr' in user_agent:
                return 'Europe/Paris'
            elif '; es' in user_agent:
                return 'Europe/Madrid'

    # Если ничего не помогло, используем IP
    return self.detect_by_ip()

# Создаем глобальный экземпляр менеджера.
timezone_manager = TimezoneManager()