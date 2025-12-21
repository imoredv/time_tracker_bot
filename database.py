"""
База данных SQLite с поддержкой часовых поясов.
"""

import sqlite3
import os
from datetime import datetime, timedelta
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_activities (
            user_id INTEGER,
            activity_type TEXT,
            custom_name TEXT,
            emoji TEXT,
            PRIMARY KEY (user_id, activity_type)
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

def get_daily_stats(user_id, date=None):
    """
    Статистика за день с учетом текущей активности.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if date is None:
        date = datetime.now().date()

    cursor.execute('''
        SELECT activity_type, SUM(duration_seconds)
        FROM activities 
        WHERE user_id = ? 
          AND date(start_time) = date(?)
          AND duration_seconds IS NOT NULL
        GROUP BY activity_type
    ''', (user_id, date.isoformat()))

    completed_stats = cursor.fetchall()

    cursor.execute('''
        SELECT activity_type, start_time 
        FROM activities 
        WHERE user_id = ? 
          AND end_time IS NULL
          AND date(start_time) = date(?)
        LIMIT 1
    ''', (user_id, date.isoformat()))

    current_activity = cursor.fetchone()
    conn.close()

    stats_dict = {}

    for activity_type, duration in completed_stats:
        stats_dict[activity_type] = duration

    if current_activity:
        activity_type, start_time_str = current_activity
        start_time = datetime.fromisoformat(start_time_str)
        current_time = datetime.now()
        current_duration = int((current_time - start_time).total_seconds())

        if activity_type in stats_dict:
            stats_dict[activity_type] += current_duration
        else:
            stats_dict[activity_type] = current_duration

    return [(activity_type, duration) for activity_type, duration in stats_dict.items()]

def get_period_stats(user_id, period_days):
    """
    Статистика за период с учетом текущей активности.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    start_date = (datetime.now() - timedelta(days=period_days)).date()
    today = datetime.now().date()

    cursor.execute('''
        SELECT activity_type, SUM(duration_seconds)
        FROM activities 
        WHERE user_id = ? 
          AND date(start_time) >= date(?)
          AND duration_seconds IS NOT NULL
        GROUP BY activity_type
    ''', (user_id, start_date.isoformat()))

    completed_stats = cursor.fetchall()

    cursor.execute('''
        SELECT activity_type, start_time 
        FROM activities 
        WHERE user_id = ? 
          AND end_time IS NULL
          AND date(start_time) >= date(?)
        LIMIT 1
    ''', (user_id, start_date.isoformat()))

    current_activity = cursor.fetchone()
    conn.close()

    stats_dict = {}

    for activity_type, duration in completed_stats:
        stats_dict[activity_type] = duration

    if current_activity:
        activity_type, start_time_str = current_activity
        start_time = datetime.fromisoformat(start_time_str)
        current_time = datetime.now()

        if start_time.date() >= start_date:
            current_duration = int((current_time - start_time).total_seconds())

            if activity_type in stats_dict:
                stats_dict[activity_type] += current_duration
            else:
                stats_dict[activity_type] = current_duration

    return [(activity_type, duration) for activity_type, duration in stats_dict.items()]

def format_duration_simple(seconds):
    """
    Простое форматирование длительности в формат ЧЧ:ММ:СС.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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
    cursor.execute('DELETE FROM custom_activities WHERE user_id = ?', (user_id,))
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

def update_custom_activity(user_id, activity_type, custom_name, emoji):
    """
    Обновление пользовательского названия активности.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO custom_activities (user_id, activity_type, custom_name, emoji)
        VALUES (?, ?, ?, ?)
    ''', (user_id, activity_type, custom_name, emoji))

    conn.commit()
    conn.close()

def get_custom_activity(user_id, activity_type):
    """
    Получение пользовательского названия активности.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT custom_name, emoji
        FROM custom_activities
        WHERE user_id = ? AND activity_type = ?
    ''', (user_id, activity_type))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'custom_name': result[0],
            'emoji': result[1]
        }
    return None

def get_all_custom_activities(user_id):
    """
    Получение всех пользовательских активностей.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT activity_type, custom_name, emoji
        FROM custom_activities
        WHERE user_id = ?
    ''', (user_id,))

    results = cursor.fetchall()
    conn.close()

    activities = {}
    for activity_type, custom_name, emoji in results:
        activities[activity_type] = {
            'custom_name': custom_name,
            'emoji': emoji
        }
    return activities

def delete_custom_activity(user_id, activity_type):
    """
    Удаление пользовательской активности.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM custom_activities
        WHERE user_id = ? AND activity_type = ?
    ''', (user_id, activity_type))

    conn.commit()
    conn.close()

def get_users_for_reminders():
    """
    Пользователи для напоминаний с учетом тихого времени и часовых поясов.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute

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

        if quiet_time_enabled:
            def time_to_minutes(time_str):
                try:
                    h, m = map(int, time_str.split(':'))
                    return h * 60 + m
                except:
                    return 0

            current_minutes = current_hour * 60 + current_minute
            start_minutes = time_to_minutes(quiet_start)
            end_minutes = time_to_minutes(quiet_end)

            in_quiet_time = False

            if start_minutes > end_minutes:
                if current_minutes >= start_minutes or current_minutes < end_minutes:
                    in_quiet_time = True
            else:
                if start_minutes <= current_minutes < end_minutes:
                    in_quiet_time = True

            if in_quiet_time:
                continue

        if last_reminder:
            last_reminder_time = datetime.fromisoformat(last_reminder)
            time_since_last_reminder = (current_time - last_reminder_time).total_seconds()

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