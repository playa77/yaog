# conversation_manager.py for YaOG
# Version: 1.2.0 (Regression Fixes)
# Description: Manages conversation state, message history, and DB synchronization.
#              Handles branching (pruning) and token counting.

from utils import TokenCounter, FileExtractor
from database_manager import DatabaseManager

class ConversationManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.token_counter = TokenCounter()
        
        # State
        self.current_conversation_id = None
        self.messages = [] # List of dicts: {id, role, content, ...}
        self.staged_files = [] # List of file paths

    def new_conversation(self):
        """Resets state for a new chat."""
        self.current_conversation_id = None
        self.messages = []
        self.staged_files = []

    def load_conversation(self, conversation_id: int):
        """Loads a conversation and its messages from the DB."""
        self.current_conversation_id = conversation_id
        self.messages = self.db.get_messages_for_conversation(conversation_id)
        self.staged_files = []

    def add_message(self, role: str, content: str, model: str = None, temp: float = None) -> int:
        """
        Adds a message to memory and DB.
        If conversation_id is None, it creates a new conversation first.
        Returns the index of the new message.
        """
        if self.current_conversation_id is None:
            # Auto-generate title from content
            title = (content[:40] + "...") if len(content) > 40 else (content or "New Chat")
            self.current_conversation_id = self.db.add_conversation(title)
        
        msg_id = self.db.add_message(self.current_conversation_id, role, content, model, temp)
        
        msg_data = {
            "id": msg_id,
            "role": role,
            "content": content,
            "model_used": model,
            "temperature_used": temp
        }
        self.messages.append(msg_data)
        return len(self.messages) - 1

    def insert_system_message(self, content: str):
        """
        Inserts a system message at the beginning of the conversation.
        Note: In the DB, this is added as a new message (latest timestamp).
        """
        if self.current_conversation_id is None:
            self.current_conversation_id = self.db.add_conversation("New Chat")

        # Add to DB
        msg_id = self.db.add_message(self.current_conversation_id, "system", content, None, None)
        
        # Insert into Memory at Index 0
        msg_data = {
            "id": msg_id,
            "role": "system",
            "content": content,
            "model_used": None,
            "temperature_used": None
        }
        self.messages.insert(0, msg_data)
        return 0

    def update_message(self, index: int, new_content: str):
        """Updates content of a message at specific index."""
        if 0 <= index < len(self.messages):
            msg = self.messages[index]
            msg['content'] = new_content
            if msg.get('id'):
                self.db.update_message_content(msg['id'], new_content)

    def prune_after(self, index: int):
        """
        Deletes all messages AFTER the given index (Exclusive).
        Used when editing a message (keep the edited one, delete future).
        """
        if index < 0 or index >= len(self.messages) - 1:
            return

        # Identify messages to remove
        to_remove = self.messages[index+1:]
        
        # Remove from DB
        for msg in to_remove:
            if msg.get('id'):
                self.db.delete_message(msg['id'])
        
        # Update memory
        self.messages = self.messages[:index+1]

    def prune_from(self, index: int):
        """
        Deletes the message AT index AND all subsequent messages (Inclusive).
        Used for the "Delete" button.
        """
        if index < 0 or index >= len(self.messages):
            return

        # Identify messages to remove (from index to end)
        to_remove = self.messages[index:]
        
        # Remove from DB
        for msg in to_remove:
            if msg.get('id'):
                self.db.delete_message(msg['id'])
        
        # Update memory (keep everything before index)
        self.messages = self.messages[:index]

    def delete_message_at(self, index: int):
        """Deletes a specific message (and usually implies pruning if not last)."""
        if 0 <= index < len(self.messages):
            msg = self.messages[index]
            if msg.get('id'):
                self.db.delete_message(msg['id'])
            self.messages.pop(index)

    def get_messages_for_api(self):
        """Returns list of {'role': ..., 'content': ...} for the API."""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    def get_token_count(self) -> int:
        """Returns estimated token count of current history."""
        return self.token_counter.count_tokens(self.get_messages_for_api())

    # --- Staging Area Helpers ---
    def add_staged_file(self, path: str):
        if path not in self.staged_files:
            self.staged_files.append(path)

    def remove_staged_file(self, path: str):
        if path in self.staged_files:
            self.staged_files.remove(path)

    def clear_staged_files(self):
        self.staged_files = []

    def get_staged_content(self) -> str:
        """Reads all staged files and returns formatted string."""
        content = ""
        for fpath in self.staged_files:
            try:
                text = FileExtractor.extract_content(fpath)
                filename = fpath.split("/")[-1] # Simple filename
                content += FileExtractor.create_attachment_payload(filename, text)
            except Exception as e:
                print(f"[ERROR] Failed to read staged file {fpath}: {e}")
        return content
