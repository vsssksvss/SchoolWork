import sqlite3
from collections import Counter

DB_NAME = "sleep.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ampm TEXT NOT NULL,
            hour INTEGER NOT NULL,
            minute TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    columns = [row["name"] for row in c.execute("PRAGMA table_info(history)").fetchall()]
    if "user_id" not in columns:
        c.execute("ALTER TABLE history ADD COLUMN user_id INTEGER")

    if "created_at" not in columns:
        c.execute("ALTER TABLE history ADD COLUMN created_at TIMESTAMP")

    # Backfill rows created before created_at existed.
    c.execute(
        """
        UPDATE history
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
        """
    )

    conn.commit()
    conn.close()


def create_user(username, password_hash):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO users (username, password)
        VALUES (?, ?)
        """,
        (username, password_hash),
    )
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id


def get_user_by_username(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, username, password
        FROM users
        WHERE username = ?
        """,
        (username,),
    )
    user = c.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, username
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    user = c.fetchone()
    conn.close()
    return user


def save_history(user_id, ampm, hour, minute):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO history (user_id, ampm, hour, minute, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (user_id, ampm, hour, minute),
    )
    conn.commit()
    conn.close()


def get_history(user_id, limit=8):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            ampm,
            hour,
            minute,
            created_at,
            strftime('%m-%d %H:%M', created_at) AS created_label
        FROM history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    data = c.fetchall()
    conn.close()
    return data


def get_history_item(user_id, history_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, ampm, hour, minute
        FROM history
        WHERE id = ? AND user_id = ?
        """,
        (history_id, user_id),
    )
    item = c.fetchone()
    conn.close()
    return item


def delete_history_item(user_id, history_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        DELETE FROM history
        WHERE id = ? AND user_id = ?
        """,
        (history_id, user_id),
    )
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def _to_minutes(ampm, hour, minute):
    hour_24 = hour % 12
    if ampm == "PM":
        hour_24 += 12
    return hour_24 * 60 + int(minute)


def _avg_minutes(rows):
    if not rows:
        return None
    total = sum(_to_minutes(row["ampm"], row["hour"], row["minute"]) for row in rows)
    return int(round(total / len(rows)))


def _most_used(rows):
    if not rows:
        return None
    key = Counter((row["ampm"], row["hour"], row["minute"]) for row in rows).most_common(1)[0][0]
    return {"ampm": key[0], "hour": key[1], "minute": key[2]}


def get_history_stats(user_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT ampm, hour, minute
        FROM history
        WHERE user_id = ?
          AND created_at >= datetime('now', '-7 day')
        """,
        (user_id,),
    )
    rows_7d = c.fetchall()

    c.execute(
        """
        SELECT ampm, hour, minute
        FROM history
        WHERE user_id = ?
          AND created_at >= datetime('now', '-30 day')
        """,
        (user_id,),
    )
    rows_30d = c.fetchall()

    conn.close()

    return {
        "count_7d": len(rows_7d),
        "count_30d": len(rows_30d),
        "avg_7d_minutes": _avg_minutes(rows_7d),
        "avg_30d_minutes": _avg_minutes(rows_30d),
        "most_used_30d": _most_used(rows_30d),
    }
