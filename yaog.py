# YaOG -- Yet another Openrouter GUI
# Version: 1.8
# Description: Instructive Roadmap - M1, T3 (QWebChannel Chat Rendering)
#
# Change Log (v1.8):
# - Implemented Milestone 1, Task 3: Dynamic Chat Rendering via QWebChannel.
# - Replaced the old `_render_chat` method, which rebuilt the entire HTML
#   on every turn, with a performant, signal-based approach.
# - Created a new `chat_template.html` file to serve as the static frontend.
#   This file contains the necessary JavaScript to communicate with Python.
# - Added a new `ChatBackend(QObject)` class in Python. An instance of this
#   class is exposed to the JavaScript context of the QWebEngineView.
# - The `ChatBackend` class has a `message_added` signal that carries new
#   message data (role, content, model name).
# - JavaScript code in `chat_template.html` listens for this signal and
#   dynamically creates and appends new message elements to the DOM.
# - This new architecture is scalable and critical for future features that
#   require JS-to-Python communication (e.g., a "Copy" button).
#
# Change Log (v1.7):
# - Refactored Codebase for Maintainability:
#   - Moved the `ApiManager` class into its own dedicated module, `api_manager.py`.
#
# (Previous change logs omitted for brevity)

import os
import sys
import json
import time
import signal
import traceback
from pathlib import Path
import html as html_lib

# --- Import the refactored ApiManager ---
from api_manager import ApiManager

# --- Crash Diagnosis & Safety ---
def crash_handler(exctype, value, tb):
    """
    A global exception handler to catch any uncaught exceptions, print them
    in a formatted way, and ensure the application exits.
    """
    print("\n\033[91m[CRASH HANDLER] Uncaught Python Exception:\033[0m", file=sys.stderr)
    traceback.print_exception(exctype, value, tb, file=sys.stderr)
    sys.exit(1)

# Register the global exception handler.
sys.excepthook = crash_handler

# --- Core Application Logic ---

def setup_project_files():
    """
    Checks for essential configuration files (.env, models.json, chat_template.html)
    and creates placeholders if they don't exist.
    """
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
        # In a real app, you might create a default one, but here we'll exit
        # as it's a core component provided with the script.
        sys.exit(1)


def main_application():
    """
    The main entry point for the PyQt6 application. Sets up the application
    instance, signal handlers, main window, and starts the event loop.
    """
    
    if sys.platform == "linux":
        args_added = []
        if '--no-sandbox' not in sys.argv:
            sys.argv.append('--no-sandbox')
            args_added.append('--no-sandbox')
        if '--disable-gpu' not in sys.argv:
            sys.argv.append('--disable-gpu')
            args_added.append('--disable-gpu')
        
        if args_added:
            print(f"[INFO] Applied Linux WebEngine workarounds: {', '.join(args_added)}")

    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QDockWidget, QTextEdit, QListWidget,
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
            QSlider, QMessageBox
        )
        from PyQt6.QtCore import (
            Qt, QRunnable, QThreadPool, QObject, pyqtSignal, pyqtSlot, QUrl, QTimer
        )
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
        # --- NEW: QWebChannel is required for the Python-JS bridge ---
        from PyQt6.QtWebChannel import QWebChannel
        
        from dotenv import load_dotenv
        
        app = QApplication(sys.argv)

        signal.signal(signal.SIGINT, lambda sig, frame: QApplication.quit())
        
        def process_signals(): pass
        
        signal_timer = QTimer()
        signal_timer.setInterval(100)
        signal_timer.timeout.connect(process_signals)
        signal_timer.start()
        
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

        class LogStream(QObject):
            log_signal = pyqtSignal(str)
            def write(self, text): self.log_signal.emit(str(text))
            def flush(self): pass

        log_stream = LogStream()
        sys.stdout = log_stream 

        def gui_print_info(message): print(f"[INFO] {message}")
        def gui_print_success(message): print(f"<font color='#4CAF50'>[SUCCESS]</font> {message}")
        def gui_print_warning(message): print(f"<font color='#FFC107'>[WARNING]</font> {message}")
        def gui_print_error(message): print(f"<font color='#F44336'>[ERROR]</font> {message}")

        gui_print_info("Loading environment variables from .env file...")
        load_dotenv()

        class WorkerSignals(QObject):
            finished = pyqtSignal(dict)
            error = pyqtSignal(str)

        class ApiWorker(QRunnable):
            """
            A worker thread for handling API requests asynchronously.
            It uses an instance of ApiManager to perform the actual request.
            """
            def __init__(self, api_manager, model_id, messages, temperature):
                super().__init__()
                self.api_manager = api_manager
                self.model_id = model_id
                self.messages = messages
                self.temperature = temperature
                self.signals = WorkerSignals()

            @pyqtSlot()
            def run(self):
                """The main logic of the worker thread: consumes and parses an SSE stream."""
                try:
                    content_parts = []
                    gui_print_info("Worker started, consuming response stream line-by-line...")
                    
                    for line in self.api_manager.get_completion_stream(self.model_id, self.messages, self.temperature):
                        if not line:
                            continue

                        if line.startswith("data: "):
                            data_str = line[len("data: "):].strip()
                            
                            if data_str == "[DONE]":
                                gui_print_info("Stream finished ([DONE] received).")
                                break
                            
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get('choices', [{}])[0].get('delta', {})
                                content_part = delta.get('content')
                                
                                if content_part:
                                    content_parts.append(content_part)
                                    
                            except json.JSONDecodeError:
                                gui_print_warning(f"Could not decode a JSON chunk from the stream: {data_str}")
                                continue
                    
                    full_response_content = "".join(content_parts)
                    
                    final_result = {
                        "choices": [{"message": {"content": full_response_content}}]
                    }
                    self.signals.finished.emit(final_result)

                except Exception as e:
                    error_message = (
                        f"<b>API Call Failed</b><br>"
                        f"Model: {self.model_id}<br>"
                        f"Error Type: {type(e).__name__}<br>"
                        f"Details: {str(e)}<br><br>"
                        "Please check your network, API key, and the console logs for details."
                    )
                    print("\n\033[91m--- [API WORKER EXCEPTION] ---\033[0m", file=sys.__stderr__)
                    traceback.print_exception(type(e), e, e.__traceback__, file=sys.__stderr__)
                    print("\033[91m------------------------------\033[0m\n", file=sys.__stderr__)
                    self.signals.error.emit(error_message)

        # --- NEW: Backend class for QWebChannel communication ---
        class ChatBackend(QObject):
            """
            This object is exposed to the JavaScript context of the QWebEngineView.
            It provides signals that the JavaScript code can connect to.
            """
            # Signal to send a new message to the frontend for rendering.
            # Arguments: role (str), content (str), modelName (str)
            message_added = pyqtSignal(str, str, str, name='message_added')

        class MainWindow(QMainWindow):
            """The main application window."""
            def __init__(self, log_signal):
                super().__init__()
                self.setWindowTitle("OR-Client (v1.8) - QWebChannel")
                self.setGeometry(100, 100, 1400, 900)
                self.models = []
                self.current_messages = []
                
                log_signal.connect(self._append_log)

                self._create_docks()
                self._setup_central_widget()
                
                self.api_manager = ApiManager()
                self.threadpool = QThreadPool()
                gui_print_info(f"Thread pool configured with max threads: {self.threadpool.maxThreadCount()}")
                
                self._load_config()
                self._check_api_key()

            def closeEvent(self, event):
                gui_print_info("Close event triggered. Cleaning up...")
                self.setEnabled(False)
                
                gui_print_info("Waiting for background threads to finish...")
                if self.threadpool.waitForDone(5000):
                    gui_print_success("All background threads finished cleanly.")
                else:
                    gui_print_warning("Timeout reached while waiting for threads.")

                gui_print_success("Cleanup complete. Application will now exit.")
                event.accept()

            @pyqtSlot(str)
            def _append_log(self, text):
                self.log_output.append(text.strip())
                self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

            def _check_api_key(self):
                if not self.api_manager.is_configured():
                    QMessageBox.warning(self, "API Key Missing", 
                                        "Your OpenRouter API key is not configured.\n\n"
                                        "Please create a file named '.env' in the same directory as the script "
                                        "and add the line:\n"
                                        "OPENROUTER_API_KEY=\"YOUR_API_KEY_HERE\"")

            def _create_docks(self):
                self.left_dock = QDockWidget("History & Logs", self)
                self.left_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
                left_widget = QWidget()
                left_layout = QVBoxLayout(left_widget)
                left_layout.setContentsMargins(0, 5, 0, 0)
                
                self.history_list = QListWidget()
                self.history_list.addItem("Conversation 1 (Placeholder)")
                left_layout.addWidget(self.history_list, 2)
                
                self.log_output = QTextEdit()
                self.log_output.setReadOnly(True)
                self.log_output.setStyleSheet("background-color: #2b2b2b; color: #f0f0f0; font-family: monospace;")
                left_layout.addWidget(self.log_output, 1)
                
                self.left_dock.setWidget(left_widget)
                self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)

                self.controls_dock = QDockWidget("Controls", self)
                self.controls_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
                controls_widget = QWidget()
                controls_layout = QVBoxLayout(controls_widget)
                controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                
                controls_layout.addWidget(QLabel("Model:"))
                self.model_combo = QComboBox()
                controls_layout.addWidget(self.model_combo)
                
                controls_layout.addWidget(QLabel("Temperature:"))
                temp_layout = QHBoxLayout()
                self.temp_slider = QSlider(Qt.Orientation.Horizontal)
                self.temp_slider.setRange(0, 200)
                self.temp_slider.setValue(100)
                self.temp_label = QLabel("1.00")
                self.temp_slider.valueChanged.connect(lambda val: self.temp_label.setText(f"{val/100.0:.2f}"))
                temp_layout.addWidget(self.temp_slider)
                temp_layout.addWidget(self.temp_label)
                controls_layout.addLayout(temp_layout)
                
                self.controls_dock.setWidget(controls_widget)
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.controls_dock)

            def _setup_central_widget(self):
                central_widget = QWidget()
                layout = QVBoxLayout(central_widget)
                
                self.chat_view = QWebEngineView()
                # --- NEW: Setup QWebChannel ---
                self._setup_web_channel()
                layout.addWidget(self.chat_view, 1)
                
                self.input_box = QTextEdit()
                self.input_box.setPlaceholderText("Enter your message here...")
                self.input_box.setFixedHeight(100)
                layout.addWidget(self.input_box)
                
                self.send_button = QPushButton("Send Message")
                self.send_button.clicked.connect(self.send_message)
                layout.addWidget(self.send_button)
                
                self.setCentralWidget(central_widget)

            def _setup_web_channel(self):
                """Initializes the QWebChannel and connects it to the QWebEngineView."""
                gui_print_info("Setting up QWebChannel bridge...")
                
                # 1. Create the Python object that will be exposed to JavaScript
                self.chat_backend = ChatBackend()
                
                # 2. Create the QWebChannel
                self.channel = QWebChannel()
                
                # 3. Register the Python object with the channel under a specific name.
                #    This name ("backend") must match the name used in the JavaScript code.
                self.channel.registerObject("backend", self.chat_backend)
                
                # 4. Set the channel on the web page of the view.
                #    This makes the `qt.webChannelTransport` object available in JS.
                self.chat_view.page().setWebChannel(self.channel)
                
                # 5. Load the HTML file that contains the frontend logic.
                #    We use an absolute path to ensure it's found correctly.
                html_path = os.path.abspath("chat_template.html")
                self.chat_view.setUrl(QUrl.fromLocalFile(html_path))
                gui_print_success(f"QWebChannel setup complete. Loaded view from: {html_path}")

            def _load_config(self):
                models_file = Path("models.json")
                try:
                    with open(models_file, "r") as f:
                        data = json.load(f)
                        self.models = data.get("models", [])
                        for model in self.models:
                            self.model_combo.addItem(model.get("name"), model.get("id"))
                        gui_print_success(f"Loaded {len(self.models)} models from 'models.json'.")
                except Exception as e:
                    gui_print_error(f"Failed to load or parse 'models.json': {e}")
                    QMessageBox.critical(self, "Config Error", f"Could not load models.json: {e}")

            # --- REMOVED: The _render_chat method is now obsolete. ---
            # The JavaScript in chat_template.html handles all rendering.

            @pyqtSlot()
            def send_message(self):
                user_text = self.input_box.toPlainText().strip()
                if not user_text: return
                if not self.api_manager.is_configured():
                    self.handle_api_error("API key is not configured. Please set it in the .env file.")
                    return

                model_id = self.model_combo.currentData()
                temperature = self.temp_slider.value() / 100.0

                # 1. Add message to the internal history for the API call
                self.current_messages.append({"role": "user", "content": user_text})
                
                # 2. Emit a signal to the JavaScript frontend to render the user's message
                gui_print_info("Emitting user message to frontend...")
                self.chat_backend.message_added.emit("user", user_text, "You")
                
                self.input_box.clear()
                self.set_ui_enabled(False)

                # 3. Start the API call in a background thread
                worker = ApiWorker(self.api_manager, model_id, self.current_messages, temperature)
                worker.signals.finished.connect(self.handle_api_response)
                worker.signals.error.connect(self.handle_api_error)
                self.threadpool.start(worker)

            @pyqtSlot(dict)
            def handle_api_response(self, response):
                gui_print_success("API response received and parsed successfully.")
                try:
                    assistant_message = response['choices'][0]['message']['content']
                    
                    # 1. Add the new message to the internal history
                    self.current_messages.append({"role": "assistant", "content": assistant_message})
                    
                    # 2. Emit a signal to the JavaScript frontend to render the assistant's message
                    current_model_name = self.model_combo.currentText()
                    gui_print_info("Emitting assistant message to frontend...")
                    self.chat_backend.message_added.emit("assistant", assistant_message, current_model_name)

                except (KeyError, IndexError) as e:
                    error_msg = f"Could not parse the API response. Error: {e}. Full Response: {response}"
                    self.handle_api_error(error_msg)
                finally:
                    self.set_ui_enabled(True)

            @pyqtSlot(str)
            def handle_api_error(self, error_message):
                gui_print_error(error_message)
                self.set_ui_enabled(True)
                QMessageBox.critical(self, "API Error", error_message)

            def set_ui_enabled(self, enabled):
                self.send_button.setEnabled(enabled)
                self.input_box.setEnabled(enabled)
                self.controls_dock.setEnabled(enabled)
                self.send_button.setText("Send Message" if enabled else "Waiting for Response...")

        window = MainWindow(log_stream.log_signal)
        window.show()
        
        exit_code = app.exec()
        gui_print_info(f"Application event loop finished with exit code {exit_code}.")
        sys.exit(exit_code)

    except ImportError as e:
        print(f"\n\033[91m[FATAL IMPORT ERROR] {e}\033[0m", file=sys.stderr)
        print("A required library is missing.", file=sys.stderr)
        print("Please run: pip install PyQt6 PyQt6-WebEngine python-dotenv httpx", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n\033[91m[FATAL ERROR DURING INITIALIZATION] {e}\033[0m", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print("[INFO] --- OR-Client Initializing (v1.8) ---")
    setup_project_files()
    main_application()
    print("[INFO] --- Script Finished ---")
