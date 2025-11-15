# database_manager.py for OR-Client (yaog.py)
# Version: 1.9
# Description: A dedicated module to handle all SQLite database interactions.
#              This class encapsulates all SQL logic, following the separation
#              of concerns principle. It manages the database file, schema
#              creation, and provides CRUD methods for the application.

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
        - Sets up the database path in a user-specific directory.
        - Connects to the SQLite database.
        - Enables foreign key support.
        - Ensures the database schema is created.
        """
        # Determine the path for the database file.
        # Using Path.home() / '.or-client' is a simple cross-platform way
        # to store user-specific application data.
        try:
            db_dir = Path.home() / '.or-client'
            db_dir.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
            self.db_path = db_dir / 'or-client.db'
            
            print(f"[INFO] Database path set to: {self.db_path}")
            
            self.conn = sqlite3.connect(self.db_path)
            # This row_factory allows accessing columns by name (e.g., row['id']),
            # which is much more readable and robust than using indices.
            self.conn.row_factory = sqlite3.Row 
            self.cursor = self.conn.cursor()
            
            # Enable foreign key support. It's off by default in SQLite and is
            # crucial for maintaining data integrity (e.g., cascading deletes).
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self.conn.commit()
            
            # Ensure the database schema is created.
            self._create_tables()
            
        except (sqlite3.Error, OSError) as e:
            print(f"\033[91m[DB FATAL] Database initialization failed: {e}\033[0m", file=sys.stderr)
            # If the DB can't be initialized, the app can't function with persistence.
            # Re-raising the exception to be handled by the main application.
            raise

    def _create_tables(self):
        """
        Creates all necessary tables in the database if they do not already exist.
        This method is idempotent and safe to run on every application startup.
        """
        print("[INFO] Verifying database schema...")
        try:
            # Using multiline strings for readability of SQL commands.
            
            # Table for storing conversations
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime'))
                );
            """)

            # Table for storing individual messages within a conversation
            # ON DELETE CASCADE ensures that if a conversation is deleted,
            # all its associated messages are also deleted automatically.
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
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

            # A linking table for the many-to-many relationship between conversations and tags
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
            print("[INFO] Database schema verified successfully.")
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to create tables: {e}\033[0m", file=sys.stderr)
            self.conn.rollback() # Rollback changes if an error occurs
            raise

    # --- Core CRUD Methods ---

    def add_conversation(self, title: str) -> int:
        """
        Creates a new conversation record and returns the new conversation_id.
        
        Args:
            title (str): The initial title for the conversation.
            
        Returns:
            int: The ID of the newly created conversation, or -1 on failure.
        """
        sql = "INSERT INTO conversations (title) VALUES (?)"
        try:
            # 'with self.conn:' automatically handles commits and rollbacks.
            with self.conn:
                self.cursor.execute(sql, (title,))
                return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to add conversation: {e}\033[0m", file=sys.stderr)
            return -1 # Return an invalid ID on failure

    def add_message(self, conversation_id: int, role: str, content: str, model: str, temp: float):
        """
        Saves a message linked to a specific conversation.
        
        Args:
            conversation_id (int): The ID of the conversation this message belongs to.
            role (str): The role of the sender ('user' or 'assistant').
            content (str): The text content of the message.
            model (str): The model ID used for the assistant's response.
            temp (float): The temperature setting used for the response.
        """
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
        """
        Retrieves a list of all conversations, ordered by creation date (newest first).
        
        Returns:
            list: A list of dictionaries, where each dictionary represents a conversation.
                  Returns an empty list on failure.
        """
        sql = "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC"
        try:
            # No need for 'with self.conn' for read-only queries, but it's harmless.
            self.cursor.execute(sql)
            # Convert the list of sqlite3.Row objects to a list of dictionaries.
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to get all conversations: {e}\033[0m", file=sys.stderr)
            return [] # Return an empty list on failure

    def get_messages_for_conversation(self, conversation_id: int) -> list:
        """
        Retrieves all messages for a given conversation, ordered by timestamp.
        
        Args:
            conversation_id (int): The ID of the conversation to retrieve messages for.
            
        Returns:
            list: A list of dictionaries representing the messages. Empty list on failure.
        """
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
        """
        Deletes a conversation and its associated messages (via cascading delete).
        
        Args:
            conversation_id (int): The ID of the conversation to delete.
        """
        sql = "DELETE FROM conversations WHERE id = ?"
        try:
            with self.conn:
                self.cursor.execute(sql, (conversation_id,))
        except sqlite3.Error as e:
            print(f"\033[91m[DB ERROR] Failed to delete conversation {conversation_id}: {e}\033[0m", file=sys.stderr)

    def close(self):
        """Closes the database connection gracefully."""
        if self.conn:
            self.conn.close()
            self.conn = None
