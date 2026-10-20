import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                login         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS folders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                name       TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                title       TEXT NOT NULL DEFAULT '',
                text        TEXT NOT NULL DEFAULT '',
                deleted     INTEGER NOT NULL DEFAULT 0,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                folder_id   INTEGER,
                position    INTEGER NOT NULL DEFAULT 0,
                created_at  INTEGER NOT NULL,
                updated_at  INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id, deleted);
            """
        )
        
        # --- АВТОМИГРАЦИЯ ДЛЯ СТАРЫХ БАЗ ---
        try:
            conn.execute("ALTER TABLE notes ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Колонка уже есть
            
        try:
            conn.execute("ALTER TABLE notes ADD COLUMN folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL")
        except sqlite3.OperationalError:
            pass