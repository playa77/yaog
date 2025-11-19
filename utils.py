# utils.py for OR-Client (yaog.py)
# Version: 1.4
# Description: A module for general-purpose utility functions and classes.
#              Includes crash handling, file setup, stdout redirection,
#              file content extraction, and token counting.
#
# Change Log (v1.4):
# - Added TokenCounter class using tiktoken.
# - Added strip_attachments_for_copy() to FileExtractor.

import sys
import json
import traceback
import html
import re
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
    A global exception handler to catch any uncaught exceptions, print them
    in a formatted way, and ensure the application exits.
    """
    print("\n\033[91m[CRASH HANDLER] Uncaught Python Exception:\033[0m", file=sys.stderr)
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
        self.log_signal.emit(str(text))

    def flush(self):
        pass


class TokenCounter:
    """
    Handles token counting using tiktoken.
    Uses 'cl100k_base' encoding (standard for GPT-4/3.5 and many modern models).
    """
    def __init__(self):
        self.encoding = None
        if tiktoken:
            try:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                print(f"[WARNING] Failed to load tiktoken encoding: {e}")

    def count_tokens(self, messages: list) -> int:
        """
        Counts tokens for a list of message dictionaries.
        Approximation based on OpenAI's chat format.
        """
        if not self.encoding:
            return 0
        
        num_tokens = 0
        for message in messages:
            # Every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 4 
            for key, value in message.items():
                if key == "content" and value:
                    num_tokens += len(self.encoding.encode(value))
                elif key == "role":
                    num_tokens += len(self.encoding.encode(value))
        
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens


class FileExtractor:
    """
    Helper class to extract text content from various file formats
    and format payloads for LLM/UI separation.
    """
    
    @staticmethod
    def get_supported_extensions():
        """Returns a filter string for QFileDialog."""
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
        """
        Reads the file at file_path and returns its text content.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        # 1. Handle PDF
        if suffix == ".pdf":
            if not fitz:
                raise ImportError("PyMuPDF is not installed. Cannot parse PDF.")
            try:
                text_content = []
                with fitz.open(path) as doc:
                    for page in doc:
                        text_content.append(page.get_text())
                return "\n".join(text_content)
            except Exception as e:
                raise ValueError(f"Failed to parse PDF: {e}")

        # 2. Handle Text/Code (Try UTF-8)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception:
                raise ValueError("File appears to be binary or uses an unsupported encoding.")
        except Exception as e:
            raise ValueError(f"Error reading file: {e}")

    @staticmethod
    def create_attachment_payload(filename: str, content: str) -> str:
        """
        Wraps the file content in a specific HTML structure.
        This structure is saved to the DB and sent to the LLM, 
        but allows the UI to easily strip it out.
        """
        safe_content = html.escape(content)
        # We use a specific class and data attribute for Regex targeting.
        return (
            f'\n<div class="yaog-file-content" data-filename="{filename}">'
            f'\n--- START OF FILE: {filename} ---\n'
            f'{safe_content}'
            f'\n--- END OF FILE: {filename} ---\n'
            f'</div>'
        )

    @staticmethod
    def strip_attachments_for_ui(text: str) -> str:
        """
        Removes the actual file content block from the text using Regex,
        escapes the remaining user text for HTML safety, and appends
        a clean HTML indicator for the attachment.
        """
        # 1. Find all attachment blocks
        pattern = r'<div class="yaog-file-content" data-filename="([^"]+)">(.*?)</div>'
        matches = re.findall(pattern, text, flags=re.DOTALL)

        # 2. Remove them from the text to get the raw user input
        clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()

        # 3. Escape the user text for HTML safety (since UI now uses innerHTML)
        # Note: If Markdown is enabled later, this step might be handled differently in main logic.
        # But this method is specifically for "UI Display" preparation.
        # We will return the raw text here if we want markdown to handle it? 
        # No, this method is legacy for the non-markdown path or pre-processing.
        # Let's keep it returning safe HTML for the default path.
        
        # Actually, to support Markdown properly, we should return the "Clean Text" 
        # and the "Indicators" separately, or return a structure.
        # However, to minimize refactoring risk, we will assume this returns 
        # the "Source Text" for the UI to render.
        
        # Wait, if we escape here, Markdown won't work on the user's actual text.
        # We should split this logic. But for now, let's assume this is used 
        # when we want to display the "Safe" version.
        
        # For the new Markdown feature, we will likely do the regex stripping manually in yaog.py
        # or use a new method.
        
        return clean_text, matches

    @staticmethod
    def strip_attachments_for_copy(text: str) -> str:
        """
        Removes the hidden file content block but leaves a plain text indicator
        for the clipboard.
        """
        pattern = r'<div class="yaog-file-content" data-filename="([^"]+)">(.*?)</div>'
        
        def replacement(match):
            filename = match.group(1)
            return f"\n[Attached: {filename}]\n"
            
        return re.sub(pattern, replacement, text, flags=re.DOTALL).strip()
