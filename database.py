import sqlite3

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
        INSERT INTO history (user_id, ampm, hour, minute)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, ampm, hour, minute),
    )
    conn.commit()
    conn.close()


def get_history(user_id, limit=5):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT ampm, hour, minute
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
