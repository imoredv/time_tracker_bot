"""
База данных SQLite.
"""

import sqlite3
from datetime import datetime, timedelta
from config import DB_NAME

def init_db():
    """
    Инициализация базы данных.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_reminder TIMESTAMP
        )
    ''')

    # Таблица активностей
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

    # Таблица настроек пользователей
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

    # Таблица пользовательских названий активностей
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
    print("✅ База данных инициализирована")

def add_user(user_id, username, first_name, last_name):
    """
    Добавление нового пользователя.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))

        cursor.execute('''
            INSERT OR IGNORE INTO user_settings (user_id)
            VALUES (?)
        ''', (user_id,))

        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка добавления пользователя {user_id}: {e}")
    finally:
        conn.close()

def get_current_activity(user_id):
    """
    Получение текущей активности.
    """
    conn = sqlite3.connect(DB_NAME)
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
    Начало новой активности.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    completed_activity = None

    # Проверяем, активна ли уже такая же активность
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

    # Завершаем текущую активность
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

    # Начинаем новую
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if date is None:
        date = datetime.now().date()

    # Получаем завершенные активности за день
    cursor.execute('''
        SELECT activity_type, SUM(duration_seconds)
        FROM activities 
        WHERE user_id = ? 
          AND date(start_time) = date(?)
          AND duration_seconds IS NOT NULL
        GROUP BY activity_type
    ''', (user_id, date.isoformat()))

    completed_stats = cursor.fetchall()

    # Получаем текущую активность (если она начата сегодня)
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

    # Создаем словарь для статистики
    stats_dict = {}

    # Добавляем завершенные активности
    for activity_type, duration in completed_stats:
        stats_dict[activity_type] = duration

    # Добавляем текущую активность (если есть)
    if current_activity:
        activity_type, start_time_str = current_activity
        start_time = datetime.fromisoformat(start_time_str)
        current_time = datetime.now()
        current_duration = int((current_time - start_time).total_seconds())

        # Добавляем к существующей статистике или создаем новую запись
        if activity_type in stats_dict:
            stats_dict[activity_type] += current_duration
        else:
            stats_dict[activity_type] = current_duration

    # Преобразуем обратно в список
    stats = [(activity_type, duration) for activity_type, duration in stats_dict.items()]

    return stats

def get_period_stats(user_id, period_days):
    """
    Статистика за период с учетом текущей активности.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    start_date = (datetime.now() - timedelta(days=period_days)).date()
    today = datetime.now().date()

    # Получаем завершенные активности за период
    cursor.execute('''
        SELECT activity_type, SUM(duration_seconds)
        FROM activities 
        WHERE user_id = ? 
          AND date(start_time) >= date(?)
          AND duration_seconds IS NOT NULL
        GROUP BY activity_type
    ''', (user_id, start_date.isoformat()))

    completed_stats = cursor.fetchall()

    # Получаем текущую активность (если она начата в период)
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

    # Создаем словарь для статистики
    stats_dict = {}

    # Добавляем завершенные активности
    for activity_type, duration in completed_stats:
        stats_dict[activity_type] = duration

    # Добавляем текущую активность (если есть)
    if current_activity:
        activity_type, start_time_str = current_activity
        start_time = datetime.fromisoformat(start_time_str)
        current_time = datetime.now()

        # Проверяем, начата ли активность сегодня (в пределах периода)
        if start_time.date() >= start_date:
            current_duration = int((current_time - start_time).total_seconds())

            # Добавляем к существующей статистике или создаем новую запись
            if activity_type in stats_dict:
                stats_dict[activity_type] += current_duration
            else:
                stats_dict[activity_type] = current_duration

    # Преобразуем обратно в список
    stats = [(activity_type, duration) for activity_type, duration in stats_dict.items()]

    return stats

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
    Обновление настроек.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

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
    conn.close()

def get_user_settings(user_id):
    """
    Получение настроек.
    """
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM custom_activities
        WHERE user_id = ? AND activity_type = ?
    ''', (user_id, activity_type))

    conn.commit()
    conn.close()

def get_users_for_reminders():
    """
    Пользователи для напоминаний с учетом тихого времени.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute

    cursor.execute('''
        SELECT u.user_id, u.first_name, us.reminder_interval, 
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
        # Распаковываем значения
        user_id = user[0]
        first_name = user[1]
        reminder_interval = user[2]
        quiet_time_enabled = user[3]
        quiet_start = user[4]
        quiet_end = user[5]
        last_reminder = user[6]

        # Проверяем тихое время
        if quiet_time_enabled:
            # Преобразуем время в минуты
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
                continue  # Пропускаем пользователя

        # Проверяем интервал напоминаний
        if last_reminder:
            last_reminder_time = datetime.fromisoformat(last_reminder)
            time_since_last_reminder = (current_time - last_reminder_time).total_seconds()

            if time_since_last_reminder >= reminder_interval:
                users_to_remind.append((user_id, first_name, reminder_interval))
        else:
            # Если напоминание еще не отправлялось
            users_to_remind.append((user_id, first_name, reminder_interval))

    return users_to_remind

def update_last_reminder_time(user_id):
    """
    Обновление времени последнего напоминания.
    """
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, first_name FROM users')
    users = cursor.fetchall()
    conn.close()

    return users

def get_user_stats(user_id):
    """
    Основная статистика пользователя с учетом текущей активности.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Общее количество активностей
    cursor.execute('SELECT COUNT(*) FROM activities WHERE user_id = ?', (user_id,))
    total_activities = cursor.fetchone()[0]

    # Общее время трекинга (завершенные + текущая)
    cursor.execute('SELECT SUM(duration_seconds) FROM activities WHERE user_id = ? AND duration_seconds IS NOT NULL', (user_id,))
    total_seconds = cursor.fetchone()[0] or 0

    # Добавляем текущую активность
    current_activity = get_current_activity(user_id)
    if current_activity:
        start_time = datetime.fromisoformat(current_activity[1])
        current_time = datetime.now()
        current_duration = int((current_time - start_time).total_seconds())
        total_seconds += current_duration

    # Самые частые активности
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