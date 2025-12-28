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
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Время 24 часа назад от текущего момента
    time_24_hours_ago = datetime.now() - timedelta(hours=24)

    cursor.execute('''
        SELECT activity_type, SUM(duration_seconds)
        FROM activities 
        WHERE user_id = ? 
          AND start_time >= ?
          AND duration_seconds IS NOT NULL
        GROUP BY activity_type
    ''', (user_id, time_24_hours_ago.isoformat()))

    completed_stats = cursor.fetchall()

    # Добавляем текущую активность, если она есть и началась в последние 24 часа
    current_activity = get_current_activity(user_id)
    if current_activity:
        activity_type, start_time_str = current_activity
        start_time = datetime.fromisoformat(start_time_str)

        # Проверяем, началась ли текущая активность в последние 24 часа
        if start_time >= time_24_hours_ago:
            current_time = datetime.now()
            current_duration = int((current_time - start_time).total_seconds())

            # Ищем текущую активность в завершенных
            found = False
            completed_stats_list = list(completed_stats)
            for i, (act_type, duration) in enumerate(completed_stats_list):
                if act_type == activity_type:
                    completed_stats_list[i] = (act_type, duration + current_duration)
                    found = True
                    break

            if not found:
                completed_stats_list.append((activity_type, current_duration))

            completed_stats = completed_stats_list

    # Преобразуем в словарь для удобства
    stats_dict = {}
    for activity_type, duration in completed_stats:
        stats_dict[activity_type] = duration

    # Добавляем все активности, даже с нулевым временем
    from config import ACTIVITIES
    result = []
    for activity_type in ACTIVITIES.keys():
        duration = stats_dict.get(activity_type, 0)
        result.append((activity_type, duration))

    # Сортируем по убыванию времени
    result.sort(key=lambda x: x[1], reverse=True)

    conn.close()
    return result

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


def get_hourly_activity_stats(user_id, days=1):
    """
    Получение статистики активности по 30-минутным интервалам за указанное количество дней.
    Теперь с учетом часового пояса пользователя.
    Возвращает список из 48 элементов (24 часа * 2 интервала) для каждого дня.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем часовой пояс пользователя
    timezone = get_user_timezone(user_id)

    # Получаем локальную дату пользователя
    try:
        import pytz
        user_tz = pytz.timezone(timezone)
        user_now = datetime.now(user_tz)
        end_date = user_now.date()
    except:
        user_now = datetime.now()
        end_date = user_now.date()

    start_date = end_date - timedelta(days=days - 1)

    # Получаем все активности за период
    cursor.execute('''
        SELECT activity_type, start_time, 
               COALESCE(duration_seconds, 
                       strftime('%s', 'now') - strftime('%s', start_time)) as duration
        FROM activities 
        WHERE user_id = ? 
          AND date(start_time) BETWEEN date(?) AND date(?)
    ''', (user_id, start_date.isoformat(), end_date.isoformat()))

    activities = cursor.fetchall()
    conn.close()

    # Создаем структуру для хранения статистики
    days_stats = []

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)

        # 48 интервалов по 30 минут (00:00-00:30, 00:30-01:00, ... 23:30-00:00)
        hourly_stats = [None] * 48

        for activity_type, start_time_str, duration in activities:
            start_time = datetime.fromisoformat(start_time_str)

            # Конвертируем время в часовой пояс пользователя
            try:
                user_tz = pytz.timezone(timezone)
                start_time_user = start_time.astimezone(user_tz)
            except:
                start_time_user = start_time

            # Проверяем, относится ли активность к текущему дню в часовом поясе пользователя
            if start_time_user.date() != current_date:
                continue

            # Рассчитываем время окончания активности
            end_time = start_time + timedelta(seconds=duration)

            # Конвертируем время окончания в часовой пояс пользователя
            try:
                end_time_user = end_time.astimezone(user_tz)
            except:
                end_time_user = end_time

            # Разбиваем активность на 30-минутные интервалы
            interval_start = start_time_user
            remaining_seconds = duration

            while remaining_seconds > 0:
                # Определяем час и минуту в локальном времени пользователя
                hour = interval_start.hour
                minute = interval_start.minute

                # Определяем номер интервала (0-47)
                interval_num = (hour * 2) + (minute // 30)

                # Определяем конец текущего интервала
                interval_end_time = interval_start.replace(
                    minute=(minute // 30) * 30,
                    second=0,
                    microsecond=0
                ) + timedelta(minutes=30)

                # Сколько секунд активности попадает в этот интервал
                seconds_in_interval = min(
                    remaining_seconds,
                    (interval_end_time - interval_start).total_seconds()
                )

                # Если в этом интервале еще нет активности или эта активность дольше
                if hourly_stats[interval_num] is None or seconds_in_interval > hourly_stats[interval_num][1]:
                    hourly_stats[interval_num] = (activity_type, seconds_in_interval)

                # Переходим к следующему интервалу
                interval_start = interval_end_time
                remaining_seconds -= seconds_in_interval

        # Заменяем None на 'rest' (отдых) для интервалов без активности
        for i in range(48):
            if hourly_stats[i] is None:
                hourly_stats[i] = ('rest', 0)

        days_stats.append(hourly_stats)

    return days_stats

def get_total_stats_by_activity(user_id, days=1):
    """
    Получение общей статистики по активностям за указанное количество дней.
    Для days=1 использует последние 24 часа.
    """
    # Если запрашиваем 1 день, используем статистику за 24 часа
    if days == 1:
        return get_stats_last_24_hours(user_id)

    # Остальной код функции для days > 1
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    # Статистика по завершенным активностям
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

    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_second = current_time.second

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

        # Для тестовых интервалов (5 секунд) пропускаем проверку тихого времени
        # чтобы можно было тестировать в любое время
        if quiet_time_enabled and reminder_interval >= 60:  # Только для интервалов >= 1 минуты
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
                # Ночное время (например, 22:00-06:00)
                if current_minutes >= start_minutes or current_minutes < end_minutes:
                    in_quiet_time = True
            else:
                # Дневное время
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

def get_daily_stats_sorted(user_id, date=None):
    """
    Статистика за день с учетом текущей активности, отсортированная по убыванию времени.
    """
    stats = get_daily_stats(user_id, date)
    # Сортируем по убыванию времени
    return sorted(stats, key=lambda x: x[1], reverse=True)