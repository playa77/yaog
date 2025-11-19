# utils.py for OR-Client (yaog.py)
# Version: 1.0
# Description: A module for general-purpose utility functions and classes
#              to keep the main application script clean. This includes
#              crash handling, initial file setup, and stdout redirection.

import sys
import json
import traceback
from pathlib import Path

# --- PyQt6 Imports ---
# Note: It's good practice to keep imports even in utility files,
# as it makes them self-contained and easier to understand.
try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    print("[FATAL] PyQt6 is not installed. Please run: pip install PyQt6", file=sys.stderr)
    sys.exit(1)


def crash_handler(exctype, value, tb):
    """
    A global exception handler to catch any uncaught exceptions, print them
    in a formatted way, and ensure the application exits.
    """
    print("\n\033[91m[CRASH HANDLER] Uncaught Python Exception:\033[0m", file=sys.stderr)
    # Using sys.__stderr__ to ensure output even if stderr is redirected.
    traceback.print_exception(exctype, value, tb, file=sys.__stderr__)
    sys.exit(1)


def setup_project_files():
    """
    Checks for essential configuration files (.env, models.json, chat_template.html)
    and creates placeholders if they don't exist.
    """
    print("[INFO] Verifying essential project files...")
    # Check for .env file
    if not Path(".env").exists():
        print("[INFO] '.env' file not found. Creating a placeholder.")
        try:
            with open(".env", "w") as f:
                f.write("OPENROUTER_API_KEY=\"YOUR_API_KEY_HERE\"\n")
            print("\033[92m[SUCCESS] Created dummy '.env' file. Please edit it with your OpenRouter API key.\033[0m")
        except IOError as e:
            print(f"\033[91m[ERROR] Could not create .env file: {e}\033[0m")

    # Check for models.json file
    if not Path("models.json").exists():
        print("[INFO] 'models.json' not found. Creating a default version with some free models.")
        default_models = {
            "models": [
                {"name": "Mistral 7B Instruct (Free)", "id": "mistralai/mistral-7b-instruct:free"},
                {"name": "Llama 3 8B Instruct (Free)", "id": "meta-llama/llama-3-8b-instruct:free"},
                {"name": "Gemma 7B Instruct (Free)", "id": "google/gemma-7b-it:free"}
            ]
        }
        try:
            with open("models.json", "w") as f:
                json.dump(default_models, f, indent=2)
            print("\033[92m[SUCCESS] Created default 'models.json' file.\033[0m")
        except IOError as e:
            print(f"\033[91m[ERROR] Could not create models.json file: {e}\033[0m")

    # Check for chat_template.html
    if not Path("chat_template.html").exists():
        print("\033[91m[FATAL] 'chat_template.html' is missing. Please create it or restore it from the source.\033[0m")
        sys.exit(1)
    
    print("[INFO] Project file verification complete.")


class LogStream(QObject):
    """
    A QObject subclass that captures stdout/stderr and emits it as a signal.
    This allows redirecting console output to a GUI widget.
    """
    log_signal = pyqtSignal(str)

    def write(self, text):
        """
        This method is called when anything is printed to the console.
        It emits the text as a signal.
        """
        self.log_signal.emit(str(text))

    def flush(self):
        """
        This method is required for the stream interface but is a no-op here.
        """
        pass
