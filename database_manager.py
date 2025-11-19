# database_manager.py for OR-Client (yaog.py)
# Version: 2.1
# Description: A dedicated module to handle all SQLite database interactions.
#              Includes schema migration logic for v2.0+ (System Prompts).

import sqlite3
from pathlib import Path
import sys

class DatabaseManager:
    """
    Manages all database operations for the OR-Client application.
    """
    def __init__(self):
        """
        Initializes the DatabaseManager.
        """
        try:
            db_dir = Path.home() / '.or-client'
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / 'or-client.db'
            
            print(f"[INFO] Database path set to: {self.db_path}")
            
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row 
            self.cursor = self.conn.cursor()
            
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self.conn.commit()
            
            self._create_tables()
            self._check_and_migrate_schema()
            
        except (sqlite3.Error, OSError) as e:
            print(f"\033[91m[DB FATAL] Database initialization failed: {e}\033[0m", file=sys.stderr)
            raise

    def _create_tables(self):
        """
        Creates all necessary tables in the database if they do not already exist.
        """
        print("[INFO] Verifying database schema...")
        try:
            # Table for conversations
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime'))
                );
            """)

            # Table for messages
            # Note: role can now be 'system' as well.
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

            # Table for custom system prompts
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    prompt_text TEXT NOT NULL
                );
            """)

            # Table for tags
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
            """)

            # Linking table for tags
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_tags (
                    conversation_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (conversation_id, tag_id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                );
            """)
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to create tables: {e}\033[0m", file=sys.stderr)
            self.conn.rollback()
            raise

    def _check_and_migrate_schema(self):
        """
        Checks if the existing 'messages' table supports the 'system' role.
        If not (legacy schema), it performs a migration.
        """
        try:
            # 1. Get the SQL used to create the messages table
            self.cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='messages'")
            row = self.cursor.fetchone()
            if not row: return

            create_sql = row['sql']

            # 2. Check if 'system' is missing from the CHECK constraint
            if "'system'" not in create_sql:
                print("\033[93m[DB WARNING] Legacy schema detected. Migrating 'messages' table to support System Prompts...\033[0m")
                
                with self.conn:
                    # A. Rename old table
                    self.cursor.execute("ALTER TABLE messages RENAME TO messages_old")
                    
                    # B. Create new table with updated schema
                    self.cursor.execute("""
                        CREATE TABLE messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            conversation_id INTEGER NOT NULL,
                            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                            content TEXT NOT NULL,
                            model_used TEXT,
                            temperature_used REAL,
                            timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
                            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                        )
                    """)
                    
                    # C. Copy data (mapping columns explicitly to be safe)
                    self.cursor.execute("""
                        INSERT INTO messages (id, conversation_id, role, content, model_used, temperature_used, timestamp)
                        SELECT id, conversation_id, role, content, model_used, temperature_used, timestamp
                        FROM messages_old
                    """)
                    
                    # D. Drop old table
                    self.cursor.execute("DROP TABLE messages_old")
                
                print("\033[92m[SUCCESS] Database migration complete.\033[0m")
            else:
                print("[INFO] Database schema is up to date.")

        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Migration failed: {e}\033[0m", file=sys.stderr)
            # We do not exit here, hoping the app might still function partially, 
            # but usually this is fatal for persistence.

    # --- Conversation & Message CRUD ---

    def add_conversation(self, title: str) -> int:
        sql = "INSERT INTO conversations (title) VALUES (?)"
        try:
            with self.conn:
                self.cursor.execute(sql, (title,))
                return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to add conversation: {e}\033[0m", file=sys.stderr)
            return -1

    def add_message(self, conversation_id: int, role: str, content: str, model: str, temp: float):
        sql = """
            INSERT INTO messages (conversation_id, role, content, model_used, temperature_used)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self.conn:
                self.cursor.execute(sql, (conversation_id, role, content, model, temp))
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to add message for conversation {conversation_id}: {e}\033[0m", file=sys.stderr)

    def get_all_conversations(self) -> list:
        sql = "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC"
        try:
            self.cursor.execute(sql)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to get all conversations: {e}\033[0m", file=sys.stderr)
            return []

    def get_messages_for_conversation(self, conversation_id: int) -> list:
        sql = """
            SELECT role, content, model_used, temperature_used, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """
        try:
            self.cursor.execute(sql, (conversation_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to get messages for conversation {conversation_id}: {e}\033[0m", file=sys.stderr)
            return []

    def delete_conversation(self, conversation_id: int):
        sql = "DELETE FROM conversations WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (conversation_id,))
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to delete conversation {conversation_id}: {e}\033[0m", file=sys.stderr)

    # --- System Prompt CRUD (Milestone 2) ---

    def add_system_prompt(self, name: str, prompt_text: str) -> int:
        """Creates a new system prompt."""
        sql = "INSERT INTO system_prompts (name, prompt_text) VALUES (?, ?)"
        try:
            with self.conn:
                self.cursor.execute(sql, (name, prompt_text))
                return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"\033[93m[DB WARNING] System prompt with name '{name}' already exists.\033[0m", file=sys.stderr)
            return -1
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to add system prompt: {e}\033[0m", file=sys.stderr)
            return -1

    def get_all_system_prompts(self) -> list:
        """Retrieves all system prompts."""
        sql = "SELECT id, name, prompt_text FROM system_prompts ORDER BY name ASC"
        try:
            self.cursor.execute(sql)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to get system prompts: {e}\033[0m", file=sys.stderr)
            return []

    def update_system_prompt(self, prompt_id: int, name: str, prompt_text: str) -> bool:
        """Updates an existing system prompt."""
        sql = "UPDATE system_prompts SET name = ?, prompt_text = ? WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (name, prompt_text, prompt_id))
                return True
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to update system prompt {prompt_id}: {e}\033[0m", file=sys.stderr)
            return False

    def delete_system_prompt(self, prompt_id: int) -> bool:
        """Deletes a system prompt."""
        sql = "DELETE FROM system_prompts WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (prompt_id,))
                return True
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to delete system prompt {prompt_id}: {e}\033[0m", file=sys.stderr)
            return False

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
