# settings_manager.py for YaOG (yaog.py)
# Version: 3.5.3 (Phase 3: Model Management)
# Description: Manages application-wide settings and Model configurations.

import json
import sys
from pathlib import Path

class SettingsManager:
    """
    Handles loading and saving of user settings to a local JSON file.
    """
    DEFAULT_SETTINGS = {
        "api_timeout": 360,
        "font_size": 16,
        "model_id": "mistralai/mistral-7b-instruct:free",
        "system_prompt_id": None
    }

    def __init__(self, filename="settings.json"):
        self.filepath = Path(filename)
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if not self.filepath.exists():
            return
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
                self.settings.update(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING] Failed to load settings: {e}", file=sys.stderr)

    def save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            print(f"[ERROR] Failed to save settings: {e}", file=sys.stderr)

    def get(self, key):
        return self.settings.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()


class ModelManager:
    """
    Handles loading and saving of model definitions to models.json.
    """
    def __init__(self, filename="models.json"):
        self.filepath = Path(filename)
        self.models = []
        self.load()

    def load(self):
        if not self.filepath.exists():
            self.models = []
            return
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
                self.models = data.get("models", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ERROR] Failed to load models.json: {e}", file=sys.stderr)
            self.models = []

    def save(self):
        data = {"models": self.models}
        try:
            with open(self.filepath, "w") as f:
                json.dump(data, f, indent=2)
            print("[INFO] models.json updated.")
        except IOError as e:
            print(f"[ERROR] Failed to save models.json: {e}", file=sys.stderr)

    def get_all(self):
        return self.models

    def add_model(self, name, model_id):
        for m in self.models:
            if m['id'] == model_id:
                return False
        self.models.append({"name": name, "id": model_id})
        self.save()
        return True

    def update_model(self, index, name, model_id):
        if 0 <= index < len(self.models):
            self.models[index] = {"name": name, "id": model_id}
            self.save()
            return True
        return False

    def delete_model(self, index):
        if 0 <= index < len(self.models):
            self.models.pop(index)
            self.save()
            return True
        return False

    def move_up(self, index):
        if index > 0 and index < len(self.models):
            self.models[index], self.models[index-1] = self.models[index-1], self.models[index]
            self.save()
            return True
        return False

    def move_down(self, index):
        if index >= 0 and index < len(self.models) - 1:
            self.models[index], self.models[index+1] = self.models[index+1], self.models[index]
            self.save()
            return True
        return False
