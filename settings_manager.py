# settings_manager.py for OR-Client (yaog.py)
# Version: 1.1
# Description: Manages application-wide settings persistence using JSON.
#              Part of Milestone 3, Task 3 (Settings Infrastructure).
#
# Change Log (v1.1):
# - [Config] Updated default API timeout to 360s (Roadmap requirement).

import json
import sys
from pathlib import Path

class SettingsManager:
    """
    Handles loading and saving of user settings to a local JSON file.
    """
    DEFAULT_SETTINGS = {
        "api_timeout": 360,   # Seconds (Default updated to 360s)
        "font_size": 16,      # Pixels
        "model_id": "mistralai/mistral-7b-instruct:free", # Default model
        "system_prompt_id": None # Default system prompt ID
    }

    def __init__(self, filename="settings.json"):
        self.filepath = Path(filename)
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """
        Loads settings from the JSON file. If the file doesn't exist or is invalid,
        it falls back to default values.
        """
        if not self.filepath.exists():
            print(f"[INFO] Settings file '{self.filepath}' not found. Using defaults.")
            return

        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
                # Update defaults with loaded data (preserves new keys if defaults change in future)
                self.settings.update(data)
            print(f"[INFO] Settings loaded from {self.filepath}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"\033[93m[WARNING] Failed to load settings: {e}. Using defaults.\033[0m", file=sys.stderr)

    def save(self):
        """
        Saves the current settings to the JSON file.
        """
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.settings, f, indent=4)
            print(f"[INFO] Settings saved to {self.filepath}")
        except IOError as e:
            print(f"\033[91m[ERROR] Failed to save settings: {e}\033[0m", file=sys.stderr)

    def get(self, key):
        """
        Retrieves a setting value.
        """
        return self.settings.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        """
        Updates a setting value and saves the file.
        """
        self.settings[key] = value
        self.save()
