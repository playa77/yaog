# YaOG -- Yet another Openrouter GUI
# Version: 2.3.2
# Description: Instructive Roadmap - M2, T2 (File Attachment Logic)
#
# Change Log (v2.3.2):
# - [FIX] Updated UI rendering logic to support HTML-based attachment indicators.
# - [FIX] Added HTML escaping for Assistant messages to prevent code blocks
#   from being interpreted as HTML tags by the new frontend renderer.
#
# Change Log (v2.3):
# - Implemented File Attachment Logic.

import os
import sys
import json
import time
import signal
import html
from pathlib import Path

# --- Local Imports ---
from api_manager import ApiManager
from database_manager import DatabaseManager
from utils import crash_handler, setup_project_files, LogStream, FileExtractor
from worker_manager import ApiWorker

# Register the global exception handler.
sys.excepthook = crash_handler

# --- Core Application Logic ---

def main_application():
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
            QSlider, QMessageBox, QListWidgetItem, QDialog, QLineEdit, QSplitter,
            QGroupBox, QFileDialog, QFrame, QSizePolicy
        )
        from PyQt6.QtCore import (
            Qt, QThreadPool, QObject, pyqtSignal, pyqtSlot, QUrl, QTimer, QSize
        )
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile
        from PyQt6.QtWebChannel import QWebChannel
        from dotenv import load_dotenv
        
        app = QApplication(sys.argv)

        # Gracefully handle Ctrl+C
        signal.signal(signal.SIGINT, lambda sig, frame: QApplication.quit())
        def process_signals(): pass
        signal_timer = QTimer()
        signal_timer.setInterval(100)
        signal_timer.timeout.connect(process_signals)
        signal_timer.start()
        
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

        log_stream = LogStream()
        sys.stdout = log_stream 

        def gui_print_info(message): print(f"[INFO] {message}")
        def gui_print_success(message): print(f"<font color='#4CAF50'>[SUCCESS]</font> {message}")
        def gui_print_warning(message): print(f"<font color='#FFC107'>[WARNING]</font> {message}")
        def gui_print_error(message): print(f"<font color='#F44336'>[ERROR]</font> {message}")

        gui_print_info("Loading environment variables from .env file...")
        load_dotenv()

        class ChatBackend(QObject):
            message_added = pyqtSignal(str, str, str, name='message_added')

        # --- System Prompt Dialog ---
        class SystemPromptDialog(QDialog):
            """Dialog for managing system prompts (CRUD)."""
            def __init__(self, db_manager, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Manage System Prompts")
                self.resize(800, 600)
                self.db_manager = db_manager
                self.current_prompt_id = None
                self._init_ui()
                self._load_prompts()

            def _init_ui(self):
                layout = QHBoxLayout(self)
                
                # Left Side: List of Prompts
                left_layout = QVBoxLayout()
                self.prompt_list = QListWidget()
                self.prompt_list.itemClicked.connect(self._on_item_clicked)
                left_layout.addWidget(QLabel("Saved Prompts:"))
                left_layout.addWidget(self.prompt_list)
                
                self.btn_new = QPushButton("New Prompt")
                self.btn_new.clicked.connect(self._reset_form)
                left_layout.addWidget(self.btn_new)
                
                # Right Side: Edit Form
                right_layout = QVBoxLayout()
                self.name_input = QLineEdit()
                self.name_input.setPlaceholderText("Prompt Name (e.g., 'Coding Assistant')")
                right_layout.addWidget(QLabel("Name:"))
                right_layout.addWidget(self.name_input)
                
                self.content_input = QTextEdit()
                self.content_input.setPlaceholderText("Enter system instructions here...")
                right_layout.addWidget(QLabel("Content:"))
                right_layout.addWidget(self.content_input)
                
                btn_row = QHBoxLayout()
                self.btn_save = QPushButton("Save")
                self.btn_save.clicked.connect(self._save_prompt)
                self.btn_delete = QPushButton("Delete")
                self.btn_delete.setStyleSheet("background-color: #d32f2f; color: white;")
                self.btn_delete.clicked.connect(self._delete_prompt)
                btn_row.addWidget(self.btn_save)
                btn_row.addWidget(self.btn_delete)
                right_layout.addLayout(btn_row)

                # Splitter
                splitter = QSplitter(Qt.Orientation.Horizontal)
                left_widget = QWidget()
                left_widget.setLayout(left_layout)
                right_widget = QWidget()
                right_widget.setLayout(right_layout)
                splitter.addWidget(left_widget)
                splitter.addWidget(right_widget)
                splitter.setStretchFactor(1, 2)
                
                layout.addWidget(splitter)

            def _load_prompts(self):
                self.prompt_list.clear()
                prompts = self.db_manager.get_all_system_prompts()
                for p in prompts:
                    item = QListWidgetItem(p['name'])
                    item.setData(Qt.ItemDataRole.UserRole, p)
                    self.prompt_list.addItem(item)
                self._reset_form()

            def _on_item_clicked(self, item):
                data = item.data(Qt.ItemDataRole.UserRole)
                self.current_prompt_id = data['id']
                self.name_input.setText(data['name'])
                self.content_input.setPlainText(data['prompt_text'])
                self.btn_delete.setEnabled(True)

            def _reset_form(self):
                self.current_prompt_id = None
                self.name_input.clear()
                self.content_input.clear()
                self.prompt_list.clearSelection()
                self.btn_delete.setEnabled(False)

            def _save_prompt(self):
                name = self.name_input.text().strip()
                content = self.content_input.toPlainText().strip()
                
                if not name or not content:
                    QMessageBox.warning(self, "Validation Error", "Name and Content cannot be empty.")
                    return

                if self.current_prompt_id:
                    # Update
                    success = self.db_manager.update_system_prompt(self.current_prompt_id, name, content)
                    if success: gui_print_success(f"Updated prompt: {name}")
                else:
                    # Create
                    new_id = self.db_manager.add_system_prompt(name, content)
                    if new_id != -1: gui_print_success(f"Created prompt: {name}")
                    else: QMessageBox.warning(self, "Error", "Name must be unique.")

                self._load_prompts()

            def _delete_prompt(self):
                if not self.current_prompt_id: return
                reply = QMessageBox.question(self, "Confirm Delete", "Are you sure?", 
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.db_manager.delete_system_prompt(self.current_prompt_id)
                    self._load_prompts()

        # --- Main Window ---
        class MainWindow(QMainWindow):
            def __init__(self, log_signal):
                super().__init__()
                self.setWindowTitle("OR-Client (v2.3.2) - File Attachments")
                self.setGeometry(100, 100, 1400, 900)
                
                # Initialize state variables
                self.models = []
                self.current_messages = []
                self.current_conversation_id = None
                self.staged_files = [] # List of file paths
                
                # 1. Setup UI first so widgets (like log_output) exist
                self._create_docks()
                self._setup_central_widget()
                
                # 2. Connect log signal now that log_output exists
                log_signal.connect(self._append_log)
                
                # 3. Initialize Managers (prints will now work)
                self.api_manager = ApiManager()
                self.threadpool = QThreadPool()
                
                try:
                    self.db_manager = DatabaseManager()
                except Exception as e:
                    gui_print_error(f"Database Init failed: {e}")
                    QMessageBox.critical(self, "Database Error", f"Init failed: {e}")
                    sys.exit(1)

                # 4. Load data
                self._load_config()
                self._populate_history_list()
                self._populate_system_prompts()

            def closeEvent(self, event):
                self.threadpool.waitForDone(1000)
                if self.db_manager: self.db_manager.close()
                event.accept()

            @pyqtSlot(str)
            def _append_log(self, text):
                self.log_output.append(text.strip())
                self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

            def _create_docks(self):
                # Left Dock (History)
                self.left_dock = QDockWidget("History & Logs", self)
                self.left_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
                left_widget = QWidget()
                left_layout = QVBoxLayout(left_widget)
                left_layout.setContentsMargins(0, 5, 0, 0)

                hist_btns = QHBoxLayout()
                self.new_chat_button = QPushButton("New Chat")
                self.new_chat_button.clicked.connect(self._new_chat)
                self.delete_chat_button = QPushButton("Delete Chat")
                self.delete_chat_button.clicked.connect(self._delete_chat)
                hist_btns.addWidget(self.new_chat_button)
                hist_btns.addWidget(self.delete_chat_button)
                left_layout.addLayout(hist_btns)
                
                self.history_list = QListWidget()
                self.history_list.itemClicked.connect(self._load_conversation)
                left_layout.addWidget(self.history_list, 2)
                
                self.log_output = QTextEdit()
                self.log_output.setReadOnly(True)
                self.log_output.setStyleSheet("background-color: #2b2b2b; color: #f0f0f0; font-family: monospace;")
                left_layout.addWidget(self.log_output, 1)
                
                self.left_dock.setWidget(left_widget)
                self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)

                # Right Dock (Controls)
                self.controls_dock = QDockWidget("Controls", self)
                self.controls_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
                controls_widget = QWidget()
                controls_layout = QVBoxLayout(controls_widget)
                controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                
                # Model Selection
                controls_layout.addWidget(QLabel("<b>Model Selection:</b>"))
                self.model_combo = QComboBox()
                controls_layout.addWidget(self.model_combo)
                
                controls_layout.addSpacing(10)

                # System Prompt Selection
                controls_layout.addWidget(QLabel("<b>System Prompt:</b>"))
                self.sys_prompt_combo = QComboBox()
                self.sys_prompt_combo.addItem("None (Default)", None)
                controls_layout.addWidget(self.sys_prompt_combo)
                
                self.manage_prompts_btn = QPushButton("Manage Prompts")
                self.manage_prompts_btn.clicked.connect(self._open_prompt_manager)
                controls_layout.addWidget(self.manage_prompts_btn)

                controls_layout.addSpacing(10)
                
                # Temperature
                controls_layout.addWidget(QLabel("<b>Temperature:</b>"))
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
                
                # 1. Chat View
                self.chat_view = QWebEngineView()
                self._setup_web_channel()
                layout.addWidget(self.chat_view, 1)
                
                # 2. Staging Area (Hidden by default)
                self.staging_container = QWidget()
                self.staging_layout = QHBoxLayout(self.staging_container)
                self.staging_layout.setContentsMargins(0, 0, 0, 0)
                self.staging_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self.staging_container.setVisible(False)
                layout.addWidget(self.staging_container)

                # 3. Input Area (Text + Attach Button)
                input_layout = QHBoxLayout()
                
                self.input_box = QTextEdit()
                self.input_box.setPlaceholderText("Enter your message here...")
                self.input_box.setFixedHeight(100)
                input_layout.addWidget(self.input_box)
                
                # Attach Button
                self.attach_btn = QPushButton("Attach")
                self.attach_btn.setToolTip("Attach File (PDF, Text, Code)")
                self.attach_btn.setFixedSize(60, 100)
                self.attach_btn.clicked.connect(self._attach_file)
                input_layout.addWidget(self.attach_btn)
                
                layout.addLayout(input_layout)

                # 4. Send Button
                self.send_button = QPushButton("Send Message")
                self.send_button.clicked.connect(self.send_message)
                layout.addWidget(self.send_button)
                
                self.setCentralWidget(central_widget)

            def _setup_web_channel(self):
                self.chat_backend = ChatBackend()
                self.channel = QWebChannel()
                self.channel.registerObject("backend", self.chat_backend)
                self.chat_view.page().setWebChannel(self.channel)
                html_path = os.path.abspath("chat_template.html")
                self.chat_view.setUrl(QUrl.fromLocalFile(html_path))

            def _load_config(self):
                models_file = Path("models.json")
                try:
                    with open(models_file, "r") as f:
                        data = json.load(f)
                        self.models = data.get("models", [])
                        for model in self.models:
                            self.model_combo.addItem(model.get("name"), model.get("id"))
                except Exception as e:
                    gui_print_error(f"Failed to load models.json: {e}")

            def _populate_history_list(self):
                self.history_list.clear()
                conversations = self.db_manager.get_all_conversations()
                for convo in conversations:
                    item = QListWidgetItem(convo['title'])
                    item.setData(Qt.ItemDataRole.UserRole, convo['id'])
                    self.history_list.addItem(item)

            def _populate_system_prompts(self):
                """Refreshes the system prompt combo box."""
                current_data = self.sys_prompt_combo.currentData()
                self.sys_prompt_combo.clear()
                self.sys_prompt_combo.addItem("None (Default)", None)
                
                prompts = self.db_manager.get_all_system_prompts()
                for p in prompts:
                    self.sys_prompt_combo.addItem(p['name'], p['prompt_text'])
                
                # Restore selection if possible
                index = self.sys_prompt_combo.findData(current_data)
                if index >= 0:
                    self.sys_prompt_combo.setCurrentIndex(index)

            @pyqtSlot()
            def _open_prompt_manager(self):
                dialog = SystemPromptDialog(self.db_manager, self)
                dialog.exec()
                self._populate_system_prompts()

            @pyqtSlot()
            def _new_chat(self):
                self.current_conversation_id = None
                self.current_messages = []
                self.staged_files = []
                self._update_staging_area()
                self.input_box.clear()
                self.history_list.clearSelection()
                self.chat_view.page().runJavaScript("clearChat();")
                # Enable prompt selection for new chat
                self.sys_prompt_combo.setEnabled(True)
                gui_print_info("New chat context initialized.")

            @pyqtSlot()
            def _delete_chat(self):
                selected_item = self.history_list.currentItem()
                if not selected_item: return
                convo_id = selected_item.data(Qt.ItemDataRole.UserRole)
                if QMessageBox.question(self, "Confirm", "Delete this chat?") == QMessageBox.StandardButton.Yes:
                    self.db_manager.delete_conversation(convo_id)
                    self.history_list.takeItem(self.history_list.row(selected_item))
                    if self.current_conversation_id == convo_id: self._new_chat()

            @pyqtSlot(QListWidgetItem)
            def _load_conversation(self, item):
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                if convo_id == self.current_conversation_id: return

                self.chat_view.page().runJavaScript("clearChat();")
                messages_from_db = self.db_manager.get_messages_for_conversation(convo_id)
                
                self.current_messages = []
                self.staged_files = [] # Clear staged files when switching chats
                self._update_staging_area()

                for msg in messages_from_db:
                    role = msg["role"]
                    content = msg["content"]
                    
                    # Reconstruct context (Keep full content for LLM)
                    self.current_messages.append({"role": role, "content": content})
                    
                    # Handle UI rendering
                    if role == "user":
                        # strip_attachments_for_ui returns safe HTML (escaped text + html tags)
                        display_content = FileExtractor.strip_attachments_for_ui(content)
                        self.chat_backend.message_added.emit("user", display_content, "You")
                    elif role == "assistant":
                        model_name = "Unknown"
                        for i in range(self.model_combo.count()):
                            if self.model_combo.itemData(i) == msg["model_used"]:
                                model_name = self.model_combo.itemText(i)
                                break
                        # Escape assistant content because frontend uses innerHTML
                        safe_content = html.escape(content)
                        self.chat_backend.message_added.emit("assistant", safe_content, model_name)
                    elif role == "system":
                        gui_print_info(f"Loaded system prompt: {content[:30]}...")

                self.current_conversation_id = convo_id
                # Disable system prompt selection for existing chats
                self.sys_prompt_combo.setEnabled(False)
                gui_print_success(f"Loaded conversation {convo_id}.")

            # --- File Attachment Logic ---

            @pyqtSlot()
            def _attach_file(self):
                filter_str = FileExtractor.get_supported_extensions()
                file_path, _ = QFileDialog.getOpenFileName(self, "Attach File", "", filter_str)
                
                if file_path:
                    if file_path not in self.staged_files:
                        self.staged_files.append(file_path)
                        self._update_staging_area()
                        gui_print_info(f"Staged file: {Path(file_path).name}")
                    else:
                        gui_print_warning("File already attached.")

            def _remove_staged_file(self, path_to_remove):
                if path_to_remove in self.staged_files:
                    self.staged_files.remove(path_to_remove)
                    self._update_staging_area()

            def _update_staging_area(self):
                # Clear existing widgets
                while self.staging_layout.count():
                    child = self.staging_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

                if not self.staged_files:
                    self.staging_container.setVisible(False)
                    return

                self.staging_container.setVisible(True)
                
                for fpath in self.staged_files:
                    fname = Path(fpath).name
                    
                    # Chip Widget
                    chip = QFrame()
                    chip.setStyleSheet("background-color: #3c3c3c; border-radius: 5px; padding: 2px;")
                    chip_layout = QHBoxLayout(chip)
                    chip_layout.setContentsMargins(5, 2, 5, 2)
                    
                    lbl = QLabel(fname)
                    lbl.setStyleSheet("color: white;")
                    chip_layout.addWidget(lbl)
                    
                    btn_del = QPushButton("x")
                    btn_del.setFixedSize(20, 20)
                    btn_del.setStyleSheet("background-color: #d32f2f; color: white; border: none; border-radius: 10px; font-weight: bold;")
                    # Use default arg in lambda to capture current fpath
                    btn_del.clicked.connect(lambda checked, p=fpath: self._remove_staged_file(p))
                    chip_layout.addWidget(btn_del)
                    
                    self.staging_layout.addWidget(chip)
                
                # Add stretch to push chips to the left
                self.staging_layout.addStretch()

            @pyqtSlot()
            def send_message(self):
                user_text = self.input_box.toPlainText().strip()
                
                # Validate: Must have text OR files
                if not user_text and not self.staged_files:
                    return
                
                if not self.api_manager.is_configured():
                    QMessageBox.warning(self, "Error", "API Key missing.")
                    return

                model_id = self.model_combo.currentData()
                temperature = self.temp_slider.value() / 100.0

                # --- Process Attachments ---
                full_message_content = user_text
                
                if self.staged_files:
                    gui_print_info(f"Processing {len(self.staged_files)} attachments...")
                    for fpath in self.staged_files:
                        try:
                            raw_content = FileExtractor.extract_content(fpath)
                            fname = Path(fpath).name
                            
                            # Create payload for DB/LLM (contains full content)
                            attachment_payload = FileExtractor.create_attachment_payload(fname, raw_content)
                            full_message_content += attachment_payload
                            
                        except Exception as e:
                            gui_print_error(f"Failed to attach {fname}: {e}")
                            QMessageBox.warning(self, "Attachment Error", f"Could not read {fname}:\n{e}")
                            return # Stop sending if attachment fails

                    # Clear staging after successful processing
                    self.staged_files = []
                    self._update_staging_area()

                # --- New Conversation Logic ---
                if self.current_conversation_id is None:
                    # Use original user text for title, not the huge attachment string
                    title_text = user_text if user_text else "File Attachment"
                    title = title_text[:40] + "..." if len(title_text) > 40 else title_text
                    
                    new_id = self.db_manager.add_conversation(title)
                    if new_id == -1: return
                    
                    self.current_conversation_id = new_id
                    
                    new_item = QListWidgetItem(title)
                    new_item.setData(Qt.ItemDataRole.UserRole, new_id)
                    self.history_list.insertItem(0, new_item)
                    self.history_list.setCurrentItem(new_item)
                    
                    # Inject System Prompt
                    sys_prompt_content = self.sys_prompt_combo.currentData()
                    if sys_prompt_content:
                        self.db_manager.add_message(new_id, "system", sys_prompt_content, None, None)
                        self.current_messages.append({"role": "system", "content": sys_prompt_content})
                        self.sys_prompt_combo.setEnabled(False)

                # --- Handle User Message ---
                # 1. Save full content (with attachments) to DB
                self.db_manager.add_message(self.current_conversation_id, "user", full_message_content, None, None)
                
                # 2. Update Context (LLM needs full content)
                self.current_messages.append({"role": "user", "content": full_message_content})
                
                # 3. Update UI (Strip attachments so user NEVER sees them)
                # strip_attachments_for_ui returns safe HTML (escaped text + html tags)
                display_content = FileExtractor.strip_attachments_for_ui(full_message_content)
                self.chat_backend.message_added.emit("user", display_content, "You")
                
                self.input_box.clear()
                self.set_ui_enabled(False)

                worker = ApiWorker(self.api_manager, model_id, self.current_messages, temperature)
                worker.signals.finished.connect(self.handle_api_response)
                worker.signals.error.connect(self.handle_api_error)
                self.threadpool.start(worker)

            @pyqtSlot(dict)
            def handle_api_response(self, response):
                try:
                    content = response['choices'][0]['message']['content']
                    self.current_messages.append({"role": "assistant", "content": content})
                    
                    if self.current_conversation_id:
                        self.db_manager.add_message(
                            self.current_conversation_id, "assistant", content, 
                            self.model_combo.currentData(), self.temp_slider.value() / 100.0
                        )
                    
                    # Escape assistant content because frontend uses innerHTML
                    safe_content = html.escape(content)
                    self.chat_backend.message_added.emit("assistant", safe_content, self.model_combo.currentText())
                except Exception as e:
                    self.handle_api_error(f"Parse error: {e}")
                finally:
                    self.set_ui_enabled(True)

            @pyqtSlot(str)
            def handle_api_error(self, msg):
                gui_print_error(msg)
                self.set_ui_enabled(True)
                QMessageBox.critical(self, "API Error", msg)

            def set_ui_enabled(self, enabled):
                self.send_button.setEnabled(enabled)
                self.input_box.setEnabled(enabled)
                self.attach_btn.setEnabled(enabled)
                self.controls_dock.setEnabled(enabled)
                self.send_button.setText("Send Message" if enabled else "Waiting...")

        window = MainWindow(log_stream.log_signal)
        window.show()
        sys.exit(app.exec())

    except ImportError as e:
        print(f"[FATAL] Missing library: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] Init error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup_project_files()
    main_application()
