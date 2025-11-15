# YaOG -- Yet another Openrouter GUI
# Version: 2.0
# Description: Instructive Roadmap - M1, T5 (Full Persistence Loop)
#
# Change Log (v2.0):
# - Implemented Milestone 1, Task 5: Full Persistence Loop.
# - Chat history is now fully persistent. The application loads all conversations
#   from the database on startup and populates the history list.
# - Implemented conversation loading: clicking a conversation in the history list
#   now clears the current view and loads the selected chat history.
# - Implemented automatic saving:
#   - When a message is sent in a new chat, a new conversation record is
#     created in the database.
#   - Both user and assistant messages are saved to the database as they
#     are sent and received, respectively.
# - Added "New Chat" and "Delete Chat" buttons to the history dock:
#   - "New Chat" button clears the current session and prepares for a new conversation.
#   - "Delete Chat" button removes the selected conversation from both the UI
#     and the database.
# - Added a `clearChat()` function to `chat_template.html` and call it from
#   Python via `runJavaScript` for efficient UI updates.
# - The application now tracks the active conversation via `self.current_conversation_id`.
#
# Change Log (v1.9):
# - Implemented Milestone 1, Task 4: Database Integration.
# - Created a new, self-contained module `database_manager.py` to handle
#   all SQLite database operations.
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

# --- Import refactored and new managers ---
from api_manager import ApiManager
from database_manager import DatabaseManager

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
            QSlider, QMessageBox, QListWidgetItem
        )
        from PyQt6.QtCore import (
            Qt, QRunnable, QThreadPool, QObject, pyqtSignal, pyqtSlot, QUrl, QTimer
        )
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
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

        class ChatBackend(QObject):
            """
            This object is exposed to the JavaScript context of the QWebEngineView.
            It provides signals that the JavaScript code can connect to.
            """
            message_added = pyqtSignal(str, str, str, name='message_added')

        class MainWindow(QMainWindow):
            """The main application window."""
            def __init__(self, log_signal):
                super().__init__()
                self.setWindowTitle("OR-Client (v2.0) - Full Persistence Loop")
                self.setGeometry(100, 100, 1400, 900)
                self.models = []
                self.current_messages = []
                # --- NEW: State variable to track the current conversation ID ---
                self.current_conversation_id = None
                
                log_signal.connect(self._append_log)

                self._create_docks()
                self._setup_central_widget()
                
                self.api_manager = ApiManager()
                self.threadpool = QThreadPool()
                gui_print_info(f"Thread pool configured with max threads: {self.threadpool.maxThreadCount()}")
                
                # --- Initialize the Database Manager ---
                try:
                    self.db_manager = DatabaseManager()
                    gui_print_success("DatabaseManager initialized successfully.")
                except Exception as e:
                    gui_print_error(f"Failed to initialize DatabaseManager: {e}")
                    QMessageBox.critical(self, "Database Error", f"Could not initialize the database: {e}\n\nThe application may not function correctly.")
                    self.db_manager = None

                self._load_config()
                self._check_api_key()
                
                # --- NEW: Populate history list from database on startup ---
                if self.db_manager:
                    self._populate_history_list()

            def closeEvent(self, event):
                gui_print_info("Close event triggered. Cleaning up...")
                self.setEnabled(False)
                
                gui_print_info("Waiting for background threads to finish...")
                if self.threadpool.waitForDone(5000):
                    gui_print_success("All background threads finished cleanly.")
                else:
                    gui_print_warning("Timeout reached while waiting for threads.")

                # --- Close the database connection ---
                if self.db_manager:
                    gui_print_info("Closing database connection...")
                    self.db_manager.close()
                    gui_print_success("Database connection closed.")

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

                # --- NEW: Add New/Delete buttons ---
                history_controls_layout = QHBoxLayout()
                self.new_chat_button = QPushButton("New Chat")
                self.new_chat_button.clicked.connect(self._new_chat)
                self.delete_chat_button = QPushButton("Delete Chat")
                self.delete_chat_button.clicked.connect(self._delete_chat)
                history_controls_layout.addWidget(self.new_chat_button)
                history_controls_layout.addWidget(self.delete_chat_button)
                left_layout.addLayout(history_controls_layout)
                
                self.history_list = QListWidget()
                # --- NEW: Connect itemClicked signal to load a conversation ---
                self.history_list.itemClicked.connect(self._load_conversation)
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
                self.chat_backend = ChatBackend()
                self.channel = QWebChannel()
                self.channel.registerObject("backend", self.chat_backend)
                self.chat_view.page().setWebChannel(self.channel)
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

            # --- NEW: Methods for persistence and conversation management ---

            def _populate_history_list(self):
                """Fetches all conversations from the DB and populates the history list."""
                gui_print_info("Populating conversation history from database...")
                self.history_list.clear()
                conversations = self.db_manager.get_all_conversations()
                for convo in conversations:
                    item = QListWidgetItem(convo['title'])
                    # Store the database ID in the item for later retrieval
                    item.setData(Qt.ItemDataRole.UserRole, convo['id'])
                    self.history_list.addItem(item)
                gui_print_success(f"Loaded {len(conversations)} conversations into history list.")

            @pyqtSlot()
            def _new_chat(self):
                """Resets the application state for a new conversation."""
                gui_print_info("Starting new chat.")
                self.current_conversation_id = None
                self.current_messages = []
                self.input_box.clear()
                self.history_list.clearSelection()
                # Use runJavaScript to call the new function in the HTML
                self.chat_view.page().runJavaScript("clearChat();")

            @pyqtSlot()
            def _delete_chat(self):
                """Deletes the currently selected conversation."""
                selected_item = self.history_list.currentItem()
                if not selected_item:
                    QMessageBox.information(self, "Delete Chat", "Please select a conversation to delete.")
                    return

                convo_id = selected_item.data(Qt.ItemDataRole.UserRole)
                convo_title = selected_item.text()

                reply = QMessageBox.question(self, "Confirm Delete",
                                             f"Are you sure you want to delete the conversation:\n'{convo_title}'?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)

                if reply == QMessageBox.StandardButton.Yes:
                    gui_print_info(f"Deleting conversation ID: {convo_id}")
                    self.db_manager.delete_conversation(convo_id)
                    
                    # Remove from the list widget
                    row = self.history_list.row(selected_item)
                    self.history_list.takeItem(row)
                    
                    # If the deleted chat was the active one, start a new chat
                    if self.current_conversation_id == convo_id:
                        self._new_chat()
                    
                    gui_print_success(f"Successfully deleted conversation '{convo_title}'.")

            @pyqtSlot(QListWidgetItem)
            def _load_conversation(self, item):
                """Loads messages for the selected conversation from the DB into the view."""
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                if convo_id == self.current_conversation_id:
                    gui_print_info(f"Conversation {convo_id} is already loaded.")
                    return

                gui_print_info(f"Loading conversation ID: {convo_id}")
                
                # Clear the current view first
                self.chat_view.page().runJavaScript("clearChat();")
                
                messages_from_db = self.db_manager.get_messages_for_conversation(convo_id)
                
                self.current_messages = []
                for msg in messages_from_db:
                    # Reconstruct the message format for the API
                    self.current_messages.append({"role": msg["role"], "content": msg["content"]})
                    
                    # Determine model name for display
                    if msg["role"] == "user":
                        model_name = "You"
                    else:
                        # Find the display name from the combo box data
                        model_display_name = "Unknown Model"
                        for i in range(self.model_combo.count()):
                            if self.model_combo.itemData(i) == msg["model_used"]:
                                model_display_name = self.model_combo.itemText(i)
                                break
                        model_name = model_display_name

                    # Render the message in the frontend
                    self.chat_backend.message_added.emit(msg["role"], msg["content"], model_name)

                self.current_conversation_id = convo_id
                gui_print_success(f"Finished loading {len(self.current_messages)} messages for conversation {convo_id}.")

            # --- Modified Core Logic ---

            @pyqtSlot()
            def send_message(self):
                user_text = self.input_box.toPlainText().strip()
                if not user_text: return
                if not self.api_manager.is_configured():
                    self.handle_api_error("API key is not configured. Please set it in the .env file.")
                    return

                model_id = self.model_combo.currentData()
                temperature = self.temp_slider.value() / 100.0

                # --- NEW: Persistence Logic ---
                # If this is the first message of a new chat, create the conversation first.
                if self.current_conversation_id is None:
                    # Create a title from the first 40 characters of the message.
                    title = user_text[:40] + "..." if len(user_text) > 40 else user_text
                    new_id = self.db_manager.add_conversation(title)
                    if new_id != -1:
                        self.current_conversation_id = new_id
                        gui_print_success(f"Created new conversation with ID: {new_id} and title: '{title}'")
                        # Add to the top of the history list and select it
                        new_item = QListWidgetItem(title)
                        new_item.setData(Qt.ItemDataRole.UserRole, new_id)
                        self.history_list.insertItem(0, new_item)
                        self.history_list.setCurrentItem(new_item)
                    else:
                        self.handle_api_error("Failed to create a new conversation in the database.")
                        return
                
                # Save the user's message to the database.
                self.db_manager.add_message(self.current_conversation_id, "user", user_text, None, None)
                # --- End of Persistence Logic ---

                self.current_messages.append({"role": "user", "content": user_text})
                
                gui_print_info("Emitting user message to frontend...")
                self.chat_backend.message_added.emit("user", user_text, "You")
                
                self.input_box.clear()
                self.set_ui_enabled(False)

                worker = ApiWorker(self.api_manager, model_id, self.current_messages, temperature)
                worker.signals.finished.connect(self.handle_api_response)
                worker.signals.error.connect(self.handle_api_error)
                self.threadpool.start(worker)

            @pyqtSlot(dict)
            def handle_api_response(self, response):
                gui_print_success("API response received and parsed successfully.")
                try:
                    assistant_message = response['choices'][0]['message']['content']
                    
                    self.current_messages.append({"role": "assistant", "content": assistant_message})
                    
                    current_model_id = self.model_combo.currentData()
                    current_model_name = self.model_combo.currentText()
                    current_temp = self.temp_slider.value() / 100.0
                    
                    # --- NEW: Save assistant's message to the database ---
                    if self.current_conversation_id:
                        self.db_manager.add_message(
                            self.current_conversation_id, 
                            "assistant", 
                            assistant_message, 
                            current_model_id, 
                            current_temp
                        )
                    # --- End of Persistence Logic ---
                    
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
    print("[INFO] --- OR-Client Initializing (v2.0) ---")
    setup_project_files()
    main_application()
    print("[INFO] --- Script Finished ---")
