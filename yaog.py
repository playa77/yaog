# YaOG -- Yet another Openrouter GUI
# Version: 1.6
# Description: Instructive Roadmap - M1, T2 (API Response Parsing)
#
# Change Log (v1.6):
# - CRITICAL FIX: Implemented correct Server-Sent Events (SSE) parsing.
#   - The previous version failed with a JSONDecodeError because it tried to
#     parse the raw SSE stream as a single JSON object.
#   - ApiManager's `get_completion_stream` now uses `iter_lines()` for
#     line-by-line processing of the stream.
#   - ApiWorker's `run` method has been completely rewritten to:
#     - Check each line for the "data: " prefix.
#     - Handle the "data: [DONE]" termination signal.
#     - Parse each individual JSON chunk from the stream.
#     - Accumulate the 'content' from each message 'delta'.
#     - Reconstruct a final response dictionary that matches the non-streaming
#       format, ensuring the rest of the app works without changes.
#   - This resolves the `JSONDecodeError: Expecting value...` crash.
#
# Change Log (v1.5):
# - Implemented Graceful Shutdown:
#   - The application now terminates correctly when the main window is closed.
#   - Added a `closeEvent` handler in MainWindow to ensure background threads
#     (like API calls) are properly waited for before exiting.
#   - Changed the application exit call to `sys.exit(app.exec())` for robust
#     process termination.
# - Implemented Ctrl+C Handling:
#   - Pressing Ctrl+C in the launching terminal now gracefully quits the
#     application instead of leaving a hanging process.
#
# Change Log (v1.4):
# - Implemented Streaming API Calls:
#   - Changed ApiManager's `get_completion` to use `httpx.stream`. This prevents
#     ReadTimeout errors on slow-to-respond models by processing the response
#     incrementally as data arrives.
#   - The ApiWorker now buffers these stream chunks and assembles the final JSON
#     response before signaling completion.
# - Added Recommended Headers: Included `HTTP-Referer` and `X-Title` in the
#   API request headers as per OpenRouter documentation best practices.
# - Made Timeout Configurable: The timeout is now a class attribute in ApiManager
#   for easier modification.
#
# Change Log (v1.3.1):
# - CRITICAL FIX: Corrected a crash-on-startup bug.

import os
import sys
import json
import time
import signal
import traceback
from pathlib import Path
import html as html_lib

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
    Checks for essential configuration files (.env, models.json) and creates
    placeholders if they don't exist, guiding the user on first run.
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


def main_application():
    """
    The main entry point for the PyQt6 application. Sets up the application
    instance, signal handlers, main window, and starts the event loop.
    """
    
    # On Linux, QWebEngineView can sometimes have issues with sandboxing or GPU acceleration.
    # These flags are common workarounds to improve stability.
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
        # Import PyQt6 components inside the try block to provide a clear
        # error message if they are not installed.
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QDockWidget, QTextEdit, QListWidget,
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
            QSlider, QMessageBox
        )
        from PyQt6.QtCore import (
            Qt, QRunnable, QThreadPool, QObject, pyqtSignal, pyqtSlot, QUrl, QTimer
        )
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile
        
        from dotenv import load_dotenv
        import httpx

        OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
        
        # Create the main application instance.
        app = QApplication(sys.argv)

        # Graceful Ctrl+C Handling
        signal.signal(signal.SIGINT, lambda sig, frame: QApplication.quit())
        
        def process_signals():
            pass
        
        signal_timer = QTimer()
        signal_timer.setInterval(100)
        signal_timer.timeout.connect(process_signals)
        signal_timer.start()
        
        # Configure the web engine profile for privacy and performance.
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

        class LogStream(QObject):
            """Redirects stdout to a PyQt signal."""
            log_signal = pyqtSignal(str)
            def write(self, text):
                self.log_signal.emit(str(text))
            def flush(self): pass

        # Redirect stdout to our custom log stream
        log_stream = LogStream()
        sys.stdout = log_stream 

        # Helper functions for formatted logging
        def gui_print_info(message): print(f"[INFO] {message}")
        def gui_print_success(message): print(f"<font color='#4CAF50'>[SUCCESS]</font> {message}")
        def gui_print_warning(message): print(f"<font color='#FFC107'>[WARNING]</font> {message}")
        def gui_print_error(message): print(f"<font color='#F44336'>[ERROR]</font> {message}")

        gui_print_info("Loading environment variables from .env file...")
        load_dotenv()

        class ApiManager:
            """Handles all communication with the OpenRouter API."""
            REQUEST_TIMEOUT = 120.0

            def __init__(self):
                self.api_key = os.getenv("OPENROUTER_API_KEY")
                self.headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/your-repo/or-client", # TODO: Replace with actual repo
                    "X-Title": "OR-Client"
                }
                
                self.client = httpx.Client(
                    headers=self.headers,
                    timeout=self.REQUEST_TIMEOUT
                )
                if self.is_configured():
                    gui_print_info(f"API Key loaded successfully: {self.api_key[:8]}...")
                else:
                    gui_print_warning("API Key not found or not configured in .env file.")

            def is_configured(self):
                """Checks if the API key is present and not the placeholder value."""
                return self.api_key and self.api_key != "YOUR_API_KEY_HERE"

            def get_completion_stream(self, model_id, messages, temperature):
                """
                Initiates a streaming request to the OpenRouter API.
                This function is a generator, yielding lines of the response as they arrive.
                """
                if not self.is_configured():
                    raise ValueError("API key is not configured.")
                
                clean_messages = [{"role": str(m["role"]), "content": str(m["content"])} for m in messages]
                payload = {"model": model_id, "messages": clean_messages, "temperature": temperature, "stream": True}

                gui_print_info(f"Preparing to send request to model: <b>{model_id}</b>")
                gui_print_info(f" -> Target URL: {OPENROUTER_API_URL}")
                gui_print_info(f" -> Timeout set to: {self.client.timeout.read} seconds")
                gui_print_info(f" -> History contains: {len(clean_messages)} messages")
                
                try:
                    with self.client.stream("POST", OPENROUTER_API_URL, json=payload) as response:
                        gui_print_info(f" <- Stream opened. Status: {response.status_code}")
                        response.raise_for_status()
                        # Use iter_lines() to process the stream line by line, which is
                        # essential for Server-Sent Events (SSE).
                        for line in response.iter_lines():
                            yield line
                except httpx.RequestError as exc:
                    gui_print_error(f"Network request to OpenRouter failed.")
                    gui_print_error(f" -> Error Type: <b>{type(exc).__name__}</b>")
                    gui_print_error(f" -> Request URL: {exc.request.url}")
                    raise exc
                except Exception as e:
                    gui_print_error(f"An unexpected error occurred during the API call: {e}")
                    raise e

        class WorkerSignals(QObject):
            """Defines the signals available from a running worker thread."""
            finished = pyqtSignal(dict)
            error = pyqtSignal(str)

        class ApiWorker(QRunnable):
            """
            A worker thread for handling API requests asynchronously.
            This version correctly parses Server-Sent Events (SSE) streams.
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
                    
                    # Iterate over each line from the streaming response.
                    for line in self.api_manager.get_completion_stream(self.model_id, self.messages, self.temperature):
                        if not line:
                            # Skip empty lines which are sometimes sent as keep-alives.
                            continue

                        # SSE lines are prefixed with "data: ". We must strip this.
                        if line.startswith("data: "):
                            data_str = line[len("data: "):].strip()
                            
                            # The stream is terminated by a special "[DONE]" message.
                            if data_str == "[DONE]":
                                gui_print_info("Stream finished ([DONE] received).")
                                break
                            
                            try:
                                # Each data chunk is its own JSON object.
                                chunk = json.loads(data_str)
                                # The actual text is in choices -> delta -> content.
                                delta = chunk.get('choices', [{}])[0].get('delta', {})
                                content_part = delta.get('content')
                                
                                if content_part:
                                    content_parts.append(content_part)
                                    
                            except json.JSONDecodeError:
                                gui_print_warning(f"Could not decode a JSON chunk from the stream: {data_str}")
                                continue # Ignore malformed chunks and continue.
                    
                    # Join all the collected content parts to form the final message.
                    full_response_content = "".join(content_parts)
                    
                    # To maintain compatibility with the existing `handle_api_response` method,
                    # we reconstruct a dictionary that looks like a non-streaming API response.
                    final_result = {
                        "choices": [
                            {
                                "message": {
                                    "content": full_response_content
                                }
                            }
                        ]
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

        class MainWindow(QMainWindow):
            """The main application window."""
            def __init__(self, log_signal):
                super().__init__()
                self.setWindowTitle("OR-Client (v1.6) - SSE Parsing Fix")
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
                """Handles the window close event to ensure graceful shutdown."""
                gui_print_info("Close event triggered. Cleaning up...")
                self.setEnabled(False)
                
                gui_print_info("Waiting for background threads to finish...")
                if self.threadpool.waitForDone(5000):
                    gui_print_success("All background threads finished cleanly.")
                else:
                    gui_print_warning("Timeout reached while waiting for threads. Some tasks may not have completed.")

                gui_print_success("Cleanup complete. Application will now exit.")
                event.accept()

            @pyqtSlot(str)
            def _append_log(self, text):
                """Appends a message to the log view widget."""
                self.log_output.append(text.strip())
                self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

            def _check_api_key(self):
                """Displays a warning if the API key is not configured."""
                if not self.api_manager.is_configured():
                    QMessageBox.warning(self, "API Key Missing", 
                                        "Your OpenRouter API key is not configured.\n\n"
                                        "Please create a file named '.env' in the same directory as the script "
                                        "and add the line:\n"
                                        "OPENROUTER_API_KEY=\"YOUR_API_KEY_HERE\"")

            def _create_docks(self):
                """Creates and configures the left and right dock widgets."""
                # Left Dock for History and Logs
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

                # Right Dock for Controls
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
                """Sets up the main chat view and input area."""
                central_widget = QWidget()
                layout = QVBoxLayout(central_widget)
                
                self.chat_view = QWebEngineView()
                self.chat_view.setHtml("""
                <html><head><style>
                    body { background-color: #1e1e1e; color: #e0e0e0; font-family: sans-serif; padding: 20px; }
                </style></head><body><h3>Welcome to OR-Client</h3><p>Select a model and type a message to begin.</p></body></html>
                """)
                layout.addWidget(self.chat_view, 1)
                
                self.input_box = QTextEdit()
                self.input_box.setPlaceholderText("Enter your message here...")
                self.input_box.setFixedHeight(100)
                layout.addWidget(self.input_box)
                
                self.send_button = QPushButton("Send Message")
                self.send_button.clicked.connect(self.send_message)
                layout.addWidget(self.send_button)
                
                self.setCentralWidget(central_widget)

            def _load_config(self):
                """Loads the model list from models.json."""
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

            def _render_chat(self):
                """Renders the current conversation history to the QWebEngineView."""
                html = """
                <html><head><style>
                    body { background-color: #1e1e1e; color: #e0e0e0; font-family: sans-serif; padding: 20px; }
                    .user { background-color: #2d2d2d; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #4CAF50; }
                    .assistant { background-color: #383838; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #2196F3; }
                    strong { color: #ffffff; }
                    pre { background-color: #000; padding: 10px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }
                </style></head><body>
                """
                
                for msg in self.current_messages:
                    role_class = "user" if msg['role'] == 'user' else "assistant"
                    role_name = "You" if msg['role'] == 'user' else f"Assistant ({self.model_combo.currentText()})"
                    content = f"<pre><code>{html_lib.escape(msg['content'])}</code></pre>"
                    html += f"<div class='{role_class}'><strong>{role_name}</strong><br>{content}</div>"
                
                html += "</body></html>"
                self.chat_view.setHtml(html)

            @pyqtSlot()
            def send_message(self):
                """Handles the 'Send' button click event."""
                user_text = self.input_box.toPlainText().strip()
                if not user_text: return
                if not self.api_manager.is_configured():
                    self.handle_api_error("API key is not configured. Please set it in the .env file.")
                    return

                model_id = self.model_combo.currentData()
                temperature = self.temp_slider.value() / 100.0

                self.current_messages.append({"role": "user", "content": user_text})
                self._render_chat()
                
                self.input_box.clear()
                self.set_ui_enabled(False)

                worker = ApiWorker(self.api_manager, model_id, self.current_messages, temperature)
                worker.signals.finished.connect(self.handle_api_response)
                worker.signals.error.connect(self.handle_api_error)
                self.threadpool.start(worker)

            @pyqtSlot(dict)
            def handle_api_response(self, response):
                """Handles a successful API response from the worker thread."""
                gui_print_success("API response received and parsed successfully.")
                try:
                    assistant_message = response['choices'][0]['message']['content']
                    self.current_messages.append({"role": "assistant", "content": assistant_message})
                    self._render_chat()
                except (KeyError, IndexError) as e:
                    error_msg = f"Could not parse the API response. Error: {e}. Full Response: {response}"
                    self.handle_api_error(error_msg)
                finally:
                    self.set_ui_enabled(True)

            @pyqtSlot(str)
            def handle_api_error(self, error_message):
                """Handles an error signal from the worker thread."""
                gui_print_error(error_message)
                self.set_ui_enabled(True)
                QMessageBox.critical(self, "API Error", error_message)

            def set_ui_enabled(self, enabled):
                """Enables or disables UI elements during API calls."""
                self.send_button.setEnabled(enabled)
                self.input_box.setEnabled(enabled)
                self.controls_dock.setEnabled(enabled)
                self.send_button.setText("Send Message" if enabled else "Waiting for Response...")

        # Create and show the main window
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
    print("[INFO] --- OR-Client Initializing (v1.6) ---")
    setup_project_files()
    main_application()
    print("[INFO] --- Script Finished ---")
