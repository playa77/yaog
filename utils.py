# utils.py for YaOG (yaog.py)
# Version: 1.6
# Description: General-purpose utility functions and classes.
#              Includes crash handling, file setup, stdout redirection,
#              file content extraction, token counting, and Env management.
#
# Change Log (v1.6):
# - [Build] Added resource_path() to support PyInstaller bundling.
# - [Build] setup_project_files() now skips HTML check if frozen.

import sys
import json
import traceback
import html
import re
import os
from pathlib import Path

# --- PyQt6 Imports ---
try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    print("[FATAL] PyQt6 is not installed. Please run: pip install PyQt6", file=sys.stderr)
    sys.exit(1)

# --- PyMuPDF Import ---
try:
    import fitz  # PyMuPDF
except ImportError:
    print("[WARNING] PyMuPDF (fitz) not found. PDF extraction will fail. Run: pip install pymupdf", file=sys.stderr)
    fitz = None

# --- Tiktoken Import ---
try:
    import tiktoken
except ImportError:
    print("[WARNING] tiktoken not found. Token counting will be disabled. Run: pip install tiktoken", file=sys.stderr)
    tiktoken = None


def crash_handler(exctype, value, tb):
    """
    A global exception handler to catch any uncaught exceptions.
    """
    print("\n\033[91m[CRASH HANDLER] Uncaught Python Exception:\033[0m", file=sys.stderr)
    traceback.print_exception(exctype, value, tb, file=sys.__stderr__)
    sys.exit(1)


def resource_path(relative_path):
    """ 
    Get absolute path to resource, works for dev and for PyInstaller.
    PyInstaller unpacks data into a temp folder at sys._MEIPASS.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def setup_project_files():
    """
    Checks for essential configuration files and creates placeholders if missing.
    """
    print("[INFO] Verifying essential project files...")
    
    # .env
    if not Path(".env").exists():
        print("[INFO] '.env' file not found. Creating a placeholder.")
        try:
            with open(".env", "w") as f:
                f.write("OPENROUTER_API_KEY=\"YOUR_API_KEY_HERE\"\n")
        except IOError as e:
            print(f"\033[91m[ERROR] Could not create .env file: {e}\033[0m")

    # models.json
    if not Path("models.json").exists():
        print("[INFO] 'models.json' not found. Creating defaults.")
        default_models = {
            "models": [
                {"name": "Mistral 7B Instruct (Free)", "id": "mistralai/mistral-7b-instruct:free"},
                {"name": "Google Gemini 2.0 Flash (Free)", "id": "google/gemini-2.0-flash-exp:free"},
                {"name": "DeepSeek V3 (Free)", "id": "deepseek/deepseek-chat-v3-0324:free"}
            ]
        }
        try:
            with open("models.json", "w") as f:
                json.dump(default_models, f, indent=2)
        except IOError as e:
            print(f"\033[91m[ERROR] Could not create models.json: {e}\033[0m")

    # chat_template.html
    # If frozen (bundled), the HTML is inside the executable, so we don't check disk.
    is_frozen = getattr(sys, 'frozen', False)
    if not is_frozen and not Path("chat_template.html").exists():
        print("\033[91m[FATAL] 'chat_template.html' is missing.\033[0m")
        sys.exit(1)
    
    print("[INFO] Project file verification complete.")


class EnvManager:
    """
    Helper to manage the .env file.
    """
    @staticmethod
    def get_api_key():
        """Reads the API key from environment or file."""
        key = "YOUR_API_KEY_HERE"
        if Path(".env").exists():
            try:
                with open(".env", "r") as f:
                    for line in f:
                        if line.strip().startswith("OPENROUTER_API_KEY="):
                            parts = line.strip().split("=", 1)
                            if len(parts) == 2:
                                raw_val = parts[1].strip()
                                if (raw_val.startswith('"') and raw_val.endswith('"')) or \
                                   (raw_val.startswith("'") and raw_val.endswith("'")):
                                    key = raw_val[1:-1]
                                else:
                                    key = raw_val
            except Exception as e:
                print(f"[ERROR] Failed to parse .env: {e}")
        return key

    @staticmethod
    def save_api_key(new_key):
        """Writes the new API key to the .env file."""
        lines = []
        found = False
        if Path(".env").exists():
            with open(".env", "r") as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith("OPENROUTER_API_KEY="):
                new_lines.append(f'OPENROUTER_API_KEY="{new_key}"\n')
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f'OPENROUTER_API_KEY="{new_key}"\n')

        try:
            with open(".env", "w") as f:
                f.writelines(new_lines)
            os.environ["OPENROUTER_API_KEY"] = new_key
            return True
        except IOError as e:
            print(f"[ERROR] Failed to write .env: {e}")
            return False


class LogStream(QObject):
    log_signal = pyqtSignal(str)
    def write(self, text):
        self.log_signal.emit(str(text))
    def flush(self): pass


class TokenCounter:
    def __init__(self):
        self.encoding = None
        if tiktoken:
            try:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            except Exception: pass

    def count_tokens(self, messages: list) -> int:
        if not self.encoding: return 0
        num_tokens = 0
        for message in messages:
            num_tokens += 4 
            for key, value in message.items():
                if key == "content" and value:
                    num_tokens += len(self.encoding.encode(value))
                elif key == "role":
                    num_tokens += len(self.encoding.encode(value))
        num_tokens += 2
        return num_tokens


class FileExtractor:
    @staticmethod
    def get_supported_extensions():
        return (
            "All Supported (*.txt *.md *.markdown *.json *.yml *.yaml *.csv *.xml *.html *.css *.ini *.toml *.log "
            "*.py *.sh *.js *.ts *.c *.cpp *.h *.java *.go *.rs *.php *.rb *.sql *.bat *.pdf);;"
            "Text/Data (*.txt *.md *.json *.csv *.xml *.log);;"
            "Code (*.py *.js *.ts *.c *.cpp *.java *.go *.rs *.sql);;"
            "PDF Documents (*.pdf);;"
            "All Files (*)"
        )

    @staticmethod
    def extract_content(file_path: str) -> str:
        path = Path(file_path)
        if not path.exists(): raise FileNotFoundError(f"File not found: {file_path}")
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            if not fitz: raise ImportError("PyMuPDF is not installed.")
            try:
                text_content = []
                with fitz.open(path) as doc:
                    for page in doc: text_content.append(page.get_text())
                return "\n".join(text_content)
            except Exception as e: raise ValueError(f"Failed to parse PDF: {e}")

        try:
            with open(path, "r", encoding="utf-8") as f: return f.read()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="latin-1") as f: return f.read()
            except Exception: raise ValueError("Binary or unsupported encoding.")
        except Exception as e: raise ValueError(f"Error reading file: {e}")

    @staticmethod
    def create_attachment_payload(filename: str, content: str) -> str:
        safe_content = html.escape(content)
        return (
            f'\n<div class="yaog-file-content" data-filename="{filename}">'
            f'\n--- START OF FILE: {filename} ---\n'
            f'{safe_content}'
            f'\n--- END OF FILE: {filename} ---\n'
            f'</div>'
        )

    @staticmethod
    def strip_attachments_for_ui(text: str):
        pattern = r'<div class="yaog-file-content" data-filename="([^"]+)">(.*?)</div>'
        matches = re.findall(pattern, text, flags=re.DOTALL)
        clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        return clean_text, matches

    @staticmethod
    def strip_attachments_for_copy(text: str) -> str:
        pattern = r'<div class="yaog-file-content" data-filename="([^"]+)">(.*?)</div>'
        def replacement(match): return f"\n[Attached: {match.group(1)}]\n"
        return re.sub(pattern, replacement, text, flags=re.DOTALL).strip()
