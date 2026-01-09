"""
База данных SQLite с поддержкой часовых поясов..
"""

import sqlite3
import os
from datetime import datetime, timedelta, date
from config import DB_NAME

def get_db_path():
    """
    Получение пути к базе данных в директории data.
    """
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"✅ Создана директория data: {data_dir}")
    return os.path.join(data_dir, DB_NAME)

def init_db():
    """
    Инициализация базы данных с поддержкой часовых поясов.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            timezone TEXT DEFAULT 'Europe/Moscow',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_reminder TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            activity_type TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            reminder_interval INTEGER DEFAULT 1800,
            notifications_enabled INTEGER DEFAULT 1,
            quiet_time_enabled INTEGER DEFAULT 1,
            quiet_time_start TEXT DEFAULT '22:00',
            quiet_time_end TEXT DEFAULT '06:00'
        )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ База данных инициализирована: {db_path}")

def add_user(user_id, username, first_name, last_name, timezone='Europe/Moscow'):
    """
    Добавление нового пользователя с часовым поясом.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, timezone)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, timezone))

        cursor.execute('''
            INSERT OR IGNORE INTO user_settings (user_id)
            VALUES (?)
        ''', (user_id,))

        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка добавления пользователя {user_id}: {e}")
    finally:
        conn.close()

def update_user_timezone(user_id, timezone):
    """
    Обновление часового пояса пользователя.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE users 
            SET timezone = ?
            WHERE user_id = ?
        ''', (timezone, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления часового пояса {user_id}: {e}")
        return False
    finally:
        conn.close()

def get_user_timezone(user_id):
    """
    Получение часового пояса пользователя.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT timezone FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    return 'Europe/Moscow'

def get_user_timezone_info(user_id):
    """
    Получение информации о часовом поясе пользователя.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, first_name, timezone FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'user_id': result[0],
            'first_name': result[1],
            'timezone': result[2]
        }
    return None

def get_current_activity(user_id):
    """
    Получение текущей активности с учетом часового пояса пользователя.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT activity_type, start_time 
        FROM activities 
        WHERE user_id = ? AND end_time IS NULL
        LIMIT 1
    ''', (user_id,))

    current_activity = cursor.fetchone()
    conn.close()

    return current_activity

def start_activity(user_id, activity_type):
    """
    Начало новой активности с учетом локального времени пользователя.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    completed_activity = None

    cursor.execute('''
        SELECT activity_type, start_time 
        FROM activities 
        WHERE user_id = ? AND end_time IS NULL AND activity_type = ?
        LIMIT 1
    ''', (user_id, activity_type))

    same_activity = cursor.fetchone()

    if same_activity:
        conn.close()
        return None

    cursor.execute('''
        SELECT activity_type, start_time 
        FROM activities 
        WHERE user_id = ? AND end_time IS NULL
        LIMIT 1
    ''', (user_id,))

    current_activity = cursor.fetchone()

    if current_activity:
        end_time = datetime.now()
        start_time = datetime.fromisoformat(current_activity[1])
        duration = int((end_time - start_time).total_seconds())

        cursor.execute('''
            UPDATE activities 
            SET end_time = ?, duration_seconds = ?
            WHERE user_id = ? AND end_time IS NULL
        ''', (end_time.isoformat(), duration, user_id))

        completed_activity = current_activity

    start_time = datetime.now()
    cursor.execute('''
        INSERT INTO activities (user_id, activity_type, start_time)
        VALUES (?, ?, ?)
    ''', (user_id, activity_type, start_time.isoformat()))

    conn.commit()
    conn.close()

    return completed_activity


def get_stats_last_24_hours(user_id):
    """
    Статистика за последние 24 часа с учетом текущей активности.
    Возвращает только реальные данные без заполнения пустого времени.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем часовой пояс пользователя
    timezone_code = get_user_timezone(user_id)

    # Маппинг часовых поясов для pytz
    tz_mapping = {
        'Russian Standard Time': 'Europe/Moscow',
        'FLE Standard Time': 'Europe/Kiev',
        'Belarus Standard Time': 'Europe/Minsk',
        'West Asia Standard Time': 'Asia/Yekaterinburg',
        'Central Asia Standard Time': 'Asia/Almaty',
        'SE Asia Standard Time': 'Asia/Bangkok',
        'China Standard Time': 'Asia/Shanghai',
        'Tokyo Standard Time': 'Asia/Tokyo',
        'GMT Standard Time': 'Europe/London',
        'W. Europe Standard Time': 'Europe/Berlin',
        'Eastern Standard Time': 'America/New_York',
        'Pacific Standard Time': 'America/Los_Angeles',
        'UTC': 'UTC',
    }

    user_tz_name = tz_mapping.get(timezone_code, 'UTC')

    try:
        import pytz
        user_tz = pytz.timezone(user_tz_name)
        user_now = datetime.now(user_tz)
        time_24_hours_ago = user_now - timedelta(hours=24)
        time_24_hours_ago_utc = time_24_hours_ago.astimezone(pytz.UTC)
    except Exception as e:
        print(f"Ошибка определения времени 24 часа назад: {e}")
        user_now = datetime.utcnow()
        time_24_hours_ago = user_now - timedelta(hours=24)
        time_24_hours_ago_utc = time_24_hours_ago

    # Получаем только завершенные активности за последние 24 часа
    cursor.execute('''
        SELECT activity_type, start_time, duration_seconds
        FROM activities 
        WHERE user_id = ? 
          AND start_time >= ?
          AND duration_seconds IS NOT NULL
        ORDER BY start_time
    ''', (user_id, time_24_hours_ago_utc.isoformat()))

    completed_activities = cursor.fetchall()

    # Получаем текущую активность отдельно
    current_activity = get_current_activity(user_id)

    conn.close()

    # Словарь для статистики - ТОЛЬКО реальные активности
    stats_dict = {}

    # Обрабатываем завершенные активности
    for activity_type, start_time_str, duration in completed_activities:
        if duration and duration > 0:  # Проверяем, что продолжительность положительная
            if activity_type in stats_dict:
                stats_dict[activity_type] += duration
            else:
                stats_dict[activity_type] = duration

    # Обрабатываем текущую активность, если она началась в последние 24 часа
    if current_activity:
        current_activity_type, start_time_str = current_activity
        start_time_utc = datetime.fromisoformat(start_time_str)

        try:
            if 'user_tz' in locals():
                start_time_local = start_time_utc.replace(tzinfo=pytz.UTC).astimezone(user_tz)
            else:
                start_time_local = start_time_utc
        except:
            start_time_local = start_time_utc

        # Проверяем, началась ли текущая активность в последние 24 часа
        if start_time_local >= time_24_hours_ago:
            current_duration = int((user_now - start_time_local).total_seconds())
            if current_duration > 0:  # Убедимся, что продолжительность положительная
                if current_activity_type in stats_dict:
                    stats_dict[current_activity_type] += current_duration
                else:
                    stats_dict[current_activity_type] = current_duration

    from config import ACTIVITIES
    result = []
    for activity_type in ACTIVITIES.keys():
        duration = stats_dict.get(activity_type, 0)
        # Возвращаем ТОЛЬКО активности с продолжительностью > 0
        if duration > 0:
            result.append((activity_type, duration))

    # Сортируем по убыванию времени
    result.sort(key=lambda x: x[1], reverse=True)

    return result


def get_daily_stats(user_id, target_date=None):
    """
    Статистика за день с учетом текущей активности и часового пояса пользователя.
    Теперь учитывает активность, начатую в предыдущий день, но продолжающуюся в целевой день.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем часовой пояс пользователя
    timezone_code = get_user_timezone(user_id)

    # Маппинг часовых поясов для pytz
    tz_mapping = {
        'Russian Standard Time': 'Europe/Moscow',
        'FLE Standard Time': 'Europe/Kiev',
        'Belarus Standard Time': 'Europe/Minsk',
        'West Asia Standard Time': 'Asia/Yekaterinburg',
        'Central Asia Standard Time': 'Asia/Almaty',
        'SE Asia Standard Time': 'Asia/Bangkok',
        'China Standard Time': 'Asia/Shanghai',
        'Tokyo Standard Time': 'Asia/Tokyo',
        'GMT Standard Time': 'Europe/London',
        'W. Europe Standard Time': 'Europe/Berlin',
        'Eastern Standard Time': 'America/New_York',
        'Pacific Standard Time': 'America/Los_Angeles',
        'UTC': 'UTC',
    }

    user_tz_name = tz_mapping.get(timezone_code, 'UTC')

    # Определяем целевую дату
    try:
        import pytz
        user_tz = pytz.timezone(user_tz_name)
        user_now = datetime.now(user_tz)
        if target_date is None:
            target_date = user_now.date()
        elif isinstance(target_date, date):
            target_date = target_date
        else:
            target_date = user_now.date()
    except Exception as e:
        print(f"Ошибка при определении даты: {e}")
        user_now = datetime.utcnow()
        if target_date is None:
            target_date = user_now.date()
        elif isinstance(target_date, date):
            target_date = target_date
        else:
            target_date = user_now.date()

    # Получаем текущую активность
    current_activity = get_current_activity(user_id)

    # Получаем все активности пользователя, включая завершенные
    cursor.execute('''
        SELECT activity_type, start_time, duration_seconds
        FROM activities 
        WHERE user_id = ?
        ORDER BY start_time
    ''', (user_id,))

    all_activities = cursor.fetchall()

    # Добавляем текущую активность, если она есть и еще не в списке
    activities_list = list(all_activities)
    if current_activity:
        activity_type, start_time_str = current_activity

        # Проверяем, есть ли уже эта активность в списке (как незавершенная)
        found = False
        for act in activities_list:
            if act[0] == activity_type and act[1] == start_time_str and act[2] is None:
                found = True
                break

        if not found:
            # Добавляем текущую активность в список
            activities_list.append((activity_type, start_time_str, None))

    conn.close()

    stats_dict = {}

    # Получаем начало и конец целевого дня в часовом поясе пользователя
    try:
        import pytz
        user_tz = pytz.timezone(user_tz_name)
        # Начало дня (00:00:00)
        day_start = user_tz.localize(datetime.combine(target_date, datetime.min.time()))
        # Конец дня (23:59:59.999999)
        day_end = user_tz.localize(datetime.combine(target_date, datetime.max.time()))
        day_end = day_end.replace(hour=23, minute=59, second=59, microsecond=999999)
    except:
        # Fallback на UTC
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())
        day_end = day_end.replace(hour=23, minute=59, second=59, microsecond=999999)

    for activity_type, start_time_str, duration_seconds in activities_list:
        start_time_utc = datetime.fromisoformat(start_time_str)

        try:
            # Конвертируем время начала активности в часовой пояс пользователя
            if 'user_tz' in locals():
                start_time_local = start_time_utc.replace(tzinfo=pytz.UTC).astimezone(user_tz)
            else:
                start_time_local = start_time_utc
        except:
            start_time_local = start_time_utc

        # Определяем время окончания активности
        if duration_seconds is not None:
            # Завершенная активность
            end_time_utc = start_time_utc + timedelta(seconds=duration_seconds)
            try:
                if 'user_tz' in locals():
                    end_time_local = end_time_utc.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                else:
                    end_time_local = end_time_utc
            except:
                end_time_local = end_time_utc
        else:
            # Текущая активность (не завершена) - используем текущее время
            current_time = datetime.now()
            try:
                if 'user_tz' in locals():
                    current_time_local = current_time.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                    end_time_local = current_time_local
                    end_time_utc = current_time.replace(tzinfo=pytz.UTC)
                else:
                    end_time_local = current_time
                    end_time_utc = current_time
            except:
                end_time_local = current_time
                end_time_utc = current_time

        # Проверяем, пересекается ли активность с целевым днем
        # Активность пересекается с днем, если:
        # 1. Она началась в этот день ИЛИ
        # 2. Она закончилась в этот день ИЛИ
        # 3. Она началась до этого дня и закончилась после него

        # Если активность началась и закончилась до начала дня - пропускаем
        if end_time_local < day_start:
            continue

        # Если активность началась после конца дня - пропускаем
        if start_time_local > day_end:
            continue

        # Активность пересекается с днем
        # Рассчитываем продолжительность активности в рамках этого дня
        # Начало периода активности в рамках дня
        activity_start_in_day = max(start_time_local, day_start)
        # Конец периода активности в рамках дня
        activity_end_in_day = min(end_time_local, day_end)

        # Продолжительность в секундах
        duration_in_day = int((activity_end_in_day - activity_start_in_day).total_seconds())

        if duration_in_day > 0:
            if activity_type in stats_dict:
                stats_dict[activity_type] += duration_in_day
            else:
                stats_dict[activity_type] = duration_in_day

    from config import ACTIVITIES
    result = []
    for activity_type in ACTIVITIES.keys():
        duration = stats_dict.get(activity_type, 0)
        result.append((activity_type, duration))

    return result


def get_daily_stats_sorted(user_id, target_date=None):
    """
    Статистика за день с учетом текущей активности и часового пояса, отсортированная по убыванию времени.
    """
    stats = get_daily_stats(user_id, target_date)
    # Сортируем по убыванию времени
    return sorted(stats, key=lambda x: x[1], reverse=True)

def get_period_stats(user_id, period_days):
    """
    Статистика за период с учетом текущей активности.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=period_days-1)

    cursor.execute('''
        SELECT activity_type, SUM(duration_seconds)
        FROM activities 
        WHERE user_id = ? 
          AND date(start_time) BETWEEN date(?) AND date(?)
          AND duration_seconds IS NOT NULL
        GROUP BY activity_type
    ''', (user_id, start_date.isoformat(), end_date.isoformat()))

    completed_stats = dict(cursor.fetchall())

    # Добавляем текущую активность, если она есть
    current_activity = get_current_activity(user_id)
    if current_activity:
        activity_type, start_time_str = current_activity
        start_time = datetime.fromisoformat(start_time_str)

        # Проверяем, попадает ли текущая активность в период
        if start_date <= start_time.date() <= end_date:
            current_time = datetime.now()
            current_duration = int((current_time - start_time).total_seconds())

            if activity_type in completed_stats:
                completed_stats[activity_type] += current_duration
            else:
                completed_stats[activity_type] = current_duration

    # Добавляем все активности, даже с нулевым временем
    from config import ACTIVITIES
    result = []
    for activity_type in ACTIVITIES.keys():
        duration = completed_stats.get(activity_type, 0)
        result.append((activity_type, duration))

    # Сортируем по убыванию времени
    result.sort(key=lambda x: x[1], reverse=True)

    conn.close()
    return result


def get_hourly_activity_stats(user_id, days=1):
    """
    Получение статистики активности по часовым интервалам за указанное количество дней.
    С учетом часового пояса пользователя. Возвращает список кортежей (дата, статистика).
    Теперь: 24 интервала (каждый 1 час) вместо 48 (каждый 30 минут).
    Для текущего дня возвращает только прошедшие часы.
    Возвращает только дни, в которых есть реальные данные из базы.
    Для каждого часа выбирается активность с МАКСИМАЛЬНОЙ продолжительностью в этом часу.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем часовой пояс пользователя
    timezone_code = get_user_timezone(user_id)

    # Преобразуем код часового пояса в формат pytz
    tz_mapping = {
        'Russian Standard Time': 'Europe/Moscow',
        'FLE Standard Time': 'Europe/Kiev',
        'Belarus Standard Time': 'Europe/Minsk',
        'West Asia Standard Time': 'Asia/Yekaterinburg',
        'Central Asia Standard Time': 'Asia/Almaty',
        'SE Asia Standard Time': 'Asia/Bangkok',
        'China Standard Time': 'Asia/Shanghai',
        'Tokyo Standard Time': 'Asia/Tokyo',
        'GMT Standard Time': 'Europe/London',
        'W. Europe Standard Time': 'Europe/Berlin',
        'Eastern Standard Time': 'America/New_York',
        'Pacific Standard Time': 'America/Los_Angeles',
    }

    user_tz_name = tz_mapping.get(timezone_code, 'UTC')

    try:
        import pytz
        user_tz = pytz.timezone(user_tz_name)
        user_now = datetime.now(user_tz)
        current_date = user_now.date()
        current_hour = user_now.hour  # Текущий час в часовом поясе пользователя
    except:
        user_now = datetime.utcnow()
        current_date = user_now.date()
        current_hour = user_now.hour

    start_date = current_date - timedelta(days=days - 1)

    # Получаем все активности за период
    cursor.execute('''
        SELECT activity_type, start_time, 
               COALESCE(duration_seconds, 
                       strftime('%s', 'now') - strftime('%s', start_time)) as duration
        FROM activities 
        WHERE user_id = ? 
          AND start_time >= ?
        ORDER BY start_time
    ''', (user_id, (datetime.utcnow() - timedelta(days=days)).isoformat()))

    activities = cursor.fetchall()
    conn.close()

    days_stats_with_dates = []

    # Создаем словарь для группировки активностей по дням
    activities_by_day = {}

    for activity_type, start_time_str, duration in activities:
        # Время в базе хранится в UTC
        start_time_utc = datetime.fromisoformat(start_time_str)

        try:
            # Конвертируем в локальное время пользователя
            if 'user_tz' not in locals():
                try:
                    import pytz
                    user_tz = pytz.timezone(user_tz_name)
                except:
                    user_tz = None

            if user_tz:
                start_time_local = start_time_utc.replace(tzinfo=pytz.UTC).astimezone(user_tz)
            else:
                start_time_local = start_time_utc
        except Exception as e:
            print(f"Ошибка конвертации времени: {e}")
            start_time_local = start_time_utc

        # Группируем по дням
        day_key = start_time_local.date()
        if day_key not in activities_by_day:
            activities_by_day[day_key] = []
        activities_by_day[day_key].append((activity_type, start_time_str, duration))

    # Теперь обрабатываем только те дни, для которых есть данные
    for day_offset in range(days):
        current_day = start_date + timedelta(days=day_offset)
        is_today = current_day == current_date

        # Проверяем, есть ли данные для этого дня
        if current_day not in activities_by_day:
            continue  # Пропускаем дни без данных

        # Для текущего дня показываем только прошедшие часы
        hours_to_show = current_hour if is_today else 24

        # Создаем структуру для хранения статистики по активностям в каждом часу
        # hourly_activity_stats[hour] = {activity_type: total_seconds}
        hourly_activity_stats = []
        for hour in range(hours_to_show):
            hourly_activity_stats.append({})

        day_activities = activities_by_day[current_day]

        for activity_type, start_time_str, duration in day_activities:
            start_time_utc = datetime.fromisoformat(start_time_str)

            try:
                if user_tz:
                    start_time_local = start_time_utc.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                else:
                    start_time_local = start_time_utc
            except:
                start_time_local = start_time_utc

            end_time_utc = start_time_utc + timedelta(seconds=duration)

            try:
                if user_tz:
                    end_time_local = end_time_utc.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                else:
                    end_time_local = end_time_utc
            except:
                end_time_local = end_time_utc

            # Разбиваем активность на часовые интервалы в ЛОКАЛЬНОМ времени
            interval_start = start_time_local
            remaining_seconds = duration

            while remaining_seconds > 0 and interval_start < end_time_local:
                hour = interval_start.hour

                # Проверяем, не выходит ли час за пределы прошедших часов (для сегодня)
                if is_today and hour >= hours_to_show:
                    break

                interval_num = hour  # Теперь напрямую час = номер интервала (0-23)

                if interval_num < 0 or interval_num >= 24:
                    break

                # Увеличиваем счетчик секунд для этой активности в этом часу
                interval_end_time = interval_start.replace(
                    minute=0,
                    second=0,
                    microsecond=0
                ) + timedelta(hours=1)

                seconds_in_interval = min(
                    remaining_seconds,
                    (min(interval_end_time, end_time_local) - interval_start).total_seconds()
                )

                # Добавляем секунды к соответствующей активности в этом часу
                if activity_type not in hourly_activity_stats[interval_num]:
                    hourly_activity_stats[interval_num][activity_type] = seconds_in_interval
                else:
                    hourly_activity_stats[interval_num][activity_type] += seconds_in_interval

                interval_start = interval_end_time
                remaining_seconds -= seconds_in_interval

        # После обработки всех активностей, для каждого часа выбираем доминирующую активность
        processed_hourly_stats = []
        for hour_stats in hourly_activity_stats:
            if hour_stats:
                # Находим активность с максимальной продолжительностью в этом часу
                dominant_activity = max(hour_stats.items(), key=lambda x: x[1])
                activity_type, total_seconds = dominant_activity
                processed_hourly_stats.append((activity_type, total_seconds))
            else:
                # Если в этом часу не было активности - ставим отдых
                processed_hourly_stats.append(('rest', 0))

        days_stats_with_dates.append((current_day, processed_hourly_stats))

    return days_stats_with_dates

def get_total_stats_by_activity(user_id, days=1):
    """
    Получение общей статистики по активностям за указанное количество дней.
    Для days=1 использует последние 24 часа.
    """
    # Если запрашиваем 1 день, используем статистику за 24 часа
    if days == 1:
        return get_stats_last_24_hours(user_id)

    # Используем функцию get_period_stats для days > 1
    return get_period_stats(user_id, days)

def update_user_setting(user_id, setting_name, value):
    """
    Обновление настроек пользователя.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if setting_name == 'reminder_interval':
            cursor.execute('''
                UPDATE user_settings 
                SET reminder_interval = ?
                WHERE user_id = ?
            ''', (value, user_id))
        elif setting_name == 'notifications_enabled':
            cursor.execute('''
                UPDATE user_settings 
                SET notifications_enabled = ?
                WHERE user_id = ?
            ''', (value, user_id))
        elif setting_name == 'quiet_time_enabled':
            cursor.execute('''
                UPDATE user_settings 
                SET quiet_time_enabled = ?
                WHERE user_id = ?
            ''', (value, user_id))
        elif setting_name == 'quiet_time_start':
            cursor.execute('''
                UPDATE user_settings 
                SET quiet_time_start = ?
                WHERE user_id = ?
            ''', (value, user_id))
        elif setting_name == 'quiet_time_end':
            cursor.execute('''
                UPDATE user_settings 
                SET quiet_time_end = ?
                WHERE user_id = ?
            ''', (value, user_id))

        conn.commit()
        print(f"✅ Настройка {setting_name} обновлена для пользователя {user_id}: {value}")

    except Exception as e:
        print(f"❌ Ошибка обновления настроек {user_id}: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_user_settings(user_id):
    """
    Получение настроек.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT reminder_interval, notifications_enabled, 
               quiet_time_enabled, quiet_time_start, quiet_time_end
        FROM user_settings 
        WHERE user_id = ?
    ''', (user_id,))

    settings = cursor.fetchone()
    conn.close()

    if settings:
        return {
            'reminder_interval': settings[0],
            'notifications_enabled': bool(settings[1]),
            'quiet_time_enabled': bool(settings[2]),
            'quiet_time_start': settings[3],
            'quiet_time_end': settings[4]
        }
    return None

def clear_user_data(user_id):
    """
    Удаление данных.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM activities WHERE user_id = ?', (user_id,))
    cursor.execute('''
        UPDATE user_settings 
        SET reminder_interval = 1800, 
            notifications_enabled = 1,
            quiet_time_enabled = 1,
            quiet_time_start = '22:00',
            quiet_time_end = '06:00'
        WHERE user_id = ?
    ''', (user_id,))

    conn.commit()
    conn.close()


def get_users_for_reminders():
    """
    Пользователи для напоминаний с учетом тихого времени и часовых поясов.
    Поддержка тестовых интервалов (5 секунд).
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.user_id, u.first_name, u.timezone,
               us.reminder_interval, 
               us.quiet_time_enabled, us.quiet_time_start, us.quiet_time_end,
               u.last_reminder
        FROM users u
        JOIN user_settings us ON u.user_id = us.user_id
        WHERE us.notifications_enabled = 1 AND us.reminder_interval > 0
    ''')

    users = cursor.fetchall()
    conn.close()

    users_to_remind = []

    for user in users:
        user_id = user[0]
        first_name = user[1]
        user_timezone = user[2]
        reminder_interval = user[3]
        quiet_time_enabled = user[4]
        quiet_start = user[5]
        quiet_end = user[6]
        last_reminder = user[7]

        # Получаем ЛОКАЛЬНОЕ время пользователя для проверки тихого часа
        try:
            # Преобразуем код часового пояса в формат pytz
            tz_mapping = {
                'Russian Standard Time': 'Europe/Moscow',
                'FLE Standard Time': 'Europe/Kiev',
                'Belarus Standard Time': 'Europe/Minsk',
                'West Asia Standard Time': 'Asia/Yekaterinburg',
                'Central Asia Standard Time': 'Asia/Almaty',
                'SE Asia Standard Time': 'Asia/Bangkok',
                'China Standard Time': 'Asia/Shanghai',
                'Tokyo Standard Time': 'Asia/Tokyo',
                'GMT Standard Time': 'Europe/London',
                'W. Europe Standard Time': 'Europe/Berlin',
                'Eastern Standard Time': 'America/New_York',
                'Pacific Standard Time': 'America/Los_Angeles',
                'UTC': 'UTC',
            }

            user_tz_name = tz_mapping.get(user_timezone, 'UTC')
            import pytz
            user_tz = pytz.timezone(user_tz_name)
            user_local_time = datetime.now(user_tz)
        except Exception as e:
            # Если ошибка, используем UTC время
            print(f"Ошибка получения локального времени для {user_id}: {e}")
            user_local_time = datetime.utcnow()

        # Проверяем тихий час для ВСЕХ интервалов, если он включен
        if quiet_time_enabled:
            def time_to_minutes(time_str):
                try:
                    h, m = map(int, time_str.split(':'))
                    return h * 60 + m
                except:
                    return 0

            current_hour = user_local_time.hour
            current_minute = user_local_time.minute
            current_minutes = current_hour * 60 + current_minute

            start_minutes = time_to_minutes(quiet_start)
            end_minutes = time_to_minutes(quiet_end)

            in_quiet_time = False

            if start_minutes > end_minutes:
                # Ночное время (например, 22:00-06:00)
                if current_minutes >= start_minutes or current_minutes < end_minutes:
                    in_quiet_time = True
            else:
                # Дневное время
                if start_minutes <= current_minutes < end_minutes:
                    in_quiet_time = True

            if in_quiet_time:
                continue  # Пропускаем пользователя, если сейчас тихое время в его часовом поясе

        # Для проверки интервала используем время сервера (как и раньше)
        server_current_time = datetime.now()

        if last_reminder:
            last_reminder_time = datetime.fromisoformat(last_reminder)
            time_since_last_reminder = (server_current_time - last_reminder_time).total_seconds()

            if time_since_last_reminder >= reminder_interval:
                users_to_remind.append((user_id, first_name, reminder_interval, user_timezone))
        else:
            users_to_remind.append((user_id, first_name, reminder_interval, user_timezone))

    return users_to_remind

def update_last_reminder_time(user_id):
    """
    Обновление времени последнего напоминания.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    current_time = datetime.now().isoformat()

    cursor.execute('''
        UPDATE users 
        SET last_reminder = ?
        WHERE user_id = ?
    ''', (current_time, user_id))

    conn.commit()
    conn.close()

def get_all_users():
    """
    Все пользователи.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, first_name, timezone FROM users')
    users = cursor.fetchall()
    conn.close()

    return users

def get_timezone_stats():
    """
    Статистика по часовым поясам.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT timezone, COUNT(*) as user_count
        FROM users
        GROUP BY timezone
        ORDER BY user_count DESC
    ''')

    stats = cursor.fetchall()
    conn.close()

    return stats

def get_user_stats(user_id):
    """
    Основная статистика пользователя с учетом текущей активности.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM activities WHERE user_id = ?', (user_id,))
    total_activities = cursor.fetchone()[0]

    cursor.execute('SELECT SUM(duration_seconds) FROM activities WHERE user_id = ? AND duration_seconds IS NOT NULL', (user_id,))
    total_seconds = cursor.fetchone()[0] or 0

    current_activity = get_current_activity(user_id)
    if current_activity:
        start_time = datetime.fromisoformat(current_activity[1])
        current_time = datetime.now()
        current_duration = int((current_time - start_time).total_seconds())
        total_seconds += current_duration

    cursor.execute('''
        SELECT activity_type, COUNT(*) as count
        FROM activities 
        WHERE user_id = ?
        GROUP BY activity_type
        ORDER BY count DESC
        LIMIT 3
    ''', (user_id,))

    top_activities = cursor.fetchall()

    conn.close()

    return {
        'total_activities': total_activities,
        'total_seconds': total_seconds,
        'top_activities': top_activities
    }

def debug_user_settings(user_id):
    """
    Отладочная информация о настройках пользователя.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT reminder_interval, notifications_enabled, 
               quiet_time_enabled, quiet_time_start, quiet_time_end
        FROM user_settings 
        WHERE user_id = ?
    ''', (user_id,))

    settings = cursor.fetchone()
    conn.close()

    if settings: 
        return f"""
        Настройки пользователя {user_id}:
        • Интервал: {settings[0]} сек ({settings[0] // 60} мин)
        • Уведомления: {'✅ Вкл' if settings[1] else '❌ Выкл'}
        • Тихий час: {'✅ Вкл' if settings[2] else '❌ Выкл'}
        • Начало: {settings[3]}
        • Конец: {settings[4]}
        """
    return f"❌ Настройки пользователя {user_id} не найдены"

def get_user_current_date(user_id):
    """
    Получение текущей даты в часовом поясе пользователя.
    """
    timezone_code = get_user_timezone(user_id)

    tz_mapping = {
        'Russian Standard Time': 'Europe/Moscow',
        'FLE Standard Time': 'Europe/Kiev',
        'Belarus Standard Time': 'Europe/Minsk',
        'West Asia Standard Time': 'Asia/Yekaterinburg',
        'Central Asia Standard Time': 'Asia/Almaty',
        'SE Asia Standard Time': 'Asia/Bangkok',
        'China Standard Time': 'Asia/Shanghai',
        'Tokyo Standard Time': 'Asia/Tokyo',
        'GMT Standard Time': 'Europe/London',
        'W. Europe Standard Time': 'Europe/Berlin',
        'Eastern Standard Time': 'America/New_York',
        'Pacific Standard Time': 'America/Los_Angeles',
        'UTC': 'UTC',
    }

    user_tz_name = tz_mapping.get(timezone_code, 'UTC')

    try:
        import pytz
        user_tz = pytz.timezone(user_tz_name)
        user_now = datetime.now(user_tz)
        return user_now.date()
    except:
        return datetime.now().date()


def debug_stats_last_24_hours(user_id):
    """
    Отладочная информация о статистике за 24 часа.
    """
    stats = get_stats_last_24_hours(user_id)

    print(f"\n=== DEBUG STATS FOR USER {user_id} ===")
    total_seconds = 0
    for activity_type, seconds in stats:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        print(f"{activity_type}: {seconds} сек = {hours}ч:{minutes:02d}м")
        total_seconds += seconds

    total_hours = total_seconds // 3600
    total_minutes = (total_seconds % 3600) // 60
    print(f"ИТОГО: {total_seconds} сек = {total_hours}ч:{total_minutes:02d}м")
    print("===============================\n")

    return stats


def get_activity_log_data(user_id, days=7):
    """
    Получение лога смен активностей за указанное количество дней.

    Args:
        user_id: ID пользователя
        days: количество дней (по умолчанию 7)

    Returns:
        list: список кортежей (timestamp, from_activity, to_activity)
        Для самой первой активности за всю историю: (timestamp, None, activity_type) - СТАРТ
        Для всех остальных смен: (timestamp, from_activity, to_activity) - смена активности
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Рассчитываем дату начала периода
    start_date = datetime.now() - timedelta(days=days)

    try:
        # Получаем ВСЕ активности пользователя за ВСЕ время, отсортированные по времени
        cursor.execute('''
            SELECT start_time, activity_type 
            FROM activities 
            WHERE user_id = ?
            ORDER BY start_time ASC
        ''', (user_id,))

        all_activities = cursor.fetchall()
        print(f"DEBUG: Всего активностей у пользователя: {len(all_activities)}")

        # Фильтруем по дате в коде (только за указанный период)
        activities = []
        for start_time_str, activity_type in all_activities:
            try:
                # Пробуем разные форматы даты
                if 'T' in start_time_str:
                    # ISO format: 2024-01-01T12:00:00
                    activity_time = datetime.fromisoformat(start_time_str.replace('T', ' '))
                else:
                    # Пытаемся разобрать как есть
                    activity_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')

                if activity_time >= start_date:
                    activities.append((start_time_str, activity_type))
            except Exception as parse_error:
                print(f"DEBUG: Ошибка парсинга даты '{start_time_str}': {parse_error}")

        print(f"DEBUG: Активностей за период {days} дней: {len(activities)}")

    except Exception as e:
        print(f"DEBUG: Ошибка SQL запроса: {e}")
        # Альтернативный запрос
        cursor.execute('''
            SELECT start_time, activity_type 
            FROM activities 
            WHERE user_id = ? AND start_time >= ?
            ORDER BY start_time ASC
        ''', (user_id, start_date.strftime('%Y-%m-%d %H:%M:%S')))

        activities = cursor.fetchall()

    conn.close()

    # Формируем лог смен активностей
    log_entries = []

    if activities:
        # Проверяем, является ли первая активность в выборке самой первой активностью за всю историю
        is_first_activity_in_history = False

        # Получаем самую первую активность пользователя за всю историю
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT start_time, activity_type 
            FROM activities 
            WHERE user_id = ?
            ORDER BY start_time ASC
            LIMIT 1
        ''', (user_id,))

        first_activity_in_history = cursor.fetchone()
        conn.close()

        if first_activity_in_history:
            first_history_time_str, first_history_activity = first_activity_in_history
            first_in_period_time_str, first_in_period_activity = activities[0]

            # Сравниваем время первой активности в периоде с самой первой активностью в истории
            try:
                if 'T' in first_history_time_str:
                    first_history_time = datetime.fromisoformat(first_history_time_str.replace('T', ' '))
                else:
                    first_history_time = datetime.strptime(first_history_time_str, '%Y-%m-%d %H:%M:%S')

                if 'T' in first_in_period_time_str:
                    first_in_period_time = datetime.fromisoformat(first_in_period_time_str.replace('T', ' '))
                else:
                    first_in_period_time = datetime.strptime(first_in_period_time_str, '%Y-%m-%d %H:%M:%S')

                # Если это одна и та же активность по времени - это СТАРТ
                if first_history_time == first_in_period_time:
                    is_first_activity_in_history = True
                    print(f"DEBUG: Первая активность в периоде является СТАРТом")
            except:
                # В случае ошибки парсинга, считаем по строковому сравнению
                if first_history_time_str == first_in_period_time_str:
                    is_first_activity_in_history = True
                    print(f"DEBUG: Первая активность в периоде является СТАРТом")

        # Добавляем записи
        for i in range(len(activities)):
            current_time, current_activity = activities[i]

            if i == 0 and is_first_activity_in_history:
                # Это самая первая активность за всю историю - добавляем как СТАРТ
                log_entries.append((current_time, None, current_activity))
            elif i > 0:
                # Это смена активности
                prev_time, prev_activity = activities[i - 1]
                log_entries.append((current_time, prev_activity, current_activity))
            else:
                # Это первая активность в периоде, но не первая в истории - просто пропускаем?
                # Или все-таки показываем как смену с "неизвестной" предыдущей активности?
                # Лучше показывать как есть, без СТАРТа
                if i > 0:
                    prev_time, prev_activity = activities[i - 1]
                    log_entries.append((current_time, prev_activity, current_activity))

    return log_entries