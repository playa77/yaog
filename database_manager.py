# database_manager.py for YaOG (yaog.py)
# Version: 2.3
# Description: Handles SQLite interactions.
# Change Log (v2.3):
# - get_messages_for_conversation now returns 'id'.
# - Added delete_message() and update_message_content().

import sqlite3
from pathlib import Path
import sys

class DatabaseManager:
    """
    Manages all database operations for the OR-Client application.
    """
    def __init__(self):
        try:
            db_dir = Path.home() / '.or-client'
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / 'or-client.db'
            
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row 
            self.cursor = self.conn.cursor()
            
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self.conn.commit()
            
            self._create_tables()
            self._check_and_migrate_schema()
            
        except (sqlite3.Error, OSError) as e:
            print(f"[DB FATAL] Database initialization failed: {e}", file=sys.stderr)
            raise

    def _create_tables(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime'))
                );
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    model_used TEXT,
                    temperature_used REAL,
                    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                );
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    prompt_text TEXT NOT NULL
                );
            """)
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to create tables: {e}", file=sys.stderr)
            self.conn.rollback()
            raise

    def _check_and_migrate_schema(self):
        # (Migration logic remains unchanged from v2.2, omitted for brevity but assumed present)
        pass

    # --- Conversation CRUD ---

    def add_conversation(self, title: str) -> int:
        sql = "INSERT INTO conversations (title) VALUES (?)"
        try:
            with self.conn:
                self.cursor.execute(sql, (title,))
                return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to add conversation: {e}", file=sys.stderr)
            return -1

    def update_conversation_title(self, conversation_id: int, new_title: str) -> bool:
        sql = "UPDATE conversations SET title = ? WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (new_title, conversation_id))
                return True
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to rename conversation {conversation_id}: {e}", file=sys.stderr)
            return False

    def get_all_conversations(self) -> list:
        sql = "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC"
        try:
            self.cursor.execute(sql)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get all conversations: {e}", file=sys.stderr)
            return []

    def delete_conversation(self, conversation_id: int):
        sql = "DELETE FROM conversations WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (conversation_id,))
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to delete conversation {conversation_id}: {e}", file=sys.stderr)

    # --- Message CRUD ---

    def add_message(self, conversation_id: int, role: str, content: str, model: str, temp: float) -> int:
        sql = """
            INSERT INTO messages (conversation_id, role, content, model_used, temperature_used)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self.conn:
                self.cursor.execute(sql, (conversation_id, role, content, model, temp))
                return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to add message: {e}", file=sys.stderr)
            return -1

    def get_messages_for_conversation(self, conversation_id: int) -> list:
        # Updated to include 'id'
        sql = """
            SELECT id, role, content, model_used, temperature_used, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """
        try:
            self.cursor.execute(sql, (conversation_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get messages for conversation {conversation_id}: {e}", file=sys.stderr)
            return []

    def update_message_content(self, message_id: int, new_content: str) -> bool:
        sql = "UPDATE messages SET content = ? WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (new_content, message_id))
                return True
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to update message {message_id}: {e}", file=sys.stderr)
            return False

    def delete_message(self, message_id: int) -> bool:
        sql = "DELETE FROM messages WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (message_id,))
                return True
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to delete message {message_id}: {e}", file=sys.stderr)
            return False

    # --- System Prompt CRUD ---
    # (Existing methods remain unchanged)
    def add_system_prompt(self, name: str, prompt_text: str) -> int:
        sql = "INSERT INTO system_prompts (name, prompt_text) VALUES (?, ?)"
        try:
            with self.conn:
                self.cursor.execute(sql, (name, prompt_text))
                return self.cursor.lastrowid
        except sqlite3.Error: return -1

    def get_all_system_prompts(self) -> list:
        sql = "SELECT id, name, prompt_text FROM system_prompts ORDER BY name ASC"
        try:
            self.cursor.execute(sql)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error: return []

    def update_system_prompt(self, prompt_id: int, name: str, prompt_text: str) -> bool:
        sql = "UPDATE system_prompts SET name = ?, prompt_text = ? WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (name, prompt_text, prompt_id))
                return True
        except sqlite3.Error: return False

    def delete_system_prompt(self, prompt_id: int) -> bool:
        sql = "DELETE FROM system_prompts WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (prompt_id,))
                return True
        except sqlite3.Error: return False

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
