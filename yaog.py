# YaOG -- Yet another Openrouter GUI
# Version: 2.6
# Description: Instructive Roadmap - M3, T2 (Enhanced Feedback & Input)
#
# Change Log (v2.6):
# - [UX] Implemented "Thinking..." -> "Generating..." indicator using new Worker signals.
# - [UX] Implemented Multi-File Upload (QFileDialog.getOpenFileNames).
# - [UX] Implemented FlowLayout for the attachment staging area to prevent window widening.
#
# Change Log (v2.5.1):
# - [FIX] Fixed Input Area resizing.

import os
import sys
import json
import time
import signal
import html
import re
from pathlib import Path

# --- Local Imports ---
from api_manager import ApiManager
from database_manager import DatabaseManager
from utils import crash_handler, setup_project_files, LogStream, FileExtractor, TokenCounter
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
            QGroupBox, QFileDialog, QFrame, QSizePolicy, QCheckBox, QMenu, QInputDialog,
            QLayout
        )
        from PyQt6.QtCore import (
            Qt, QThreadPool, QObject, pyqtSignal, pyqtSlot, QUrl, QTimer, QSize, QPoint, QRect
        )
        from PyQt6.QtGui import QIcon, QAction
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile
        from PyQt6.QtWebChannel import QWebChannel
        from dotenv import load_dotenv
        
        # Import markdown library
        try:
            import markdown
        except ImportError:
            print("[FATAL] 'markdown' library missing. Run: pip install markdown", file=sys.stderr)
            sys.exit(1)

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

        # --- Custom Flow Layout ---
        class FlowLayout(QLayout):
            """
            Standard FlowLayout implementation for PyQt6.
            Arranges widgets left-to-right, wrapping to the next line when space runs out.
            """
            def __init__(self, parent=None, margin=0, spacing=-1):
                super().__init__(parent)
                if parent is not None:
                    self.setContentsMargins(margin, margin, margin, margin)
                self.setSpacing(spacing)
                self.itemList = []

            def __del__(self):
                item = self.takeAt(0)
                while item:
                    item = self.takeAt(0)

            def addItem(self, item):
                self.itemList.append(item)

            def count(self):
                return len(self.itemList)

            def itemAt(self, index):
                if 0 <= index < len(self.itemList):
                    return self.itemList[index]
                return None

            def takeAt(self, index):
                if 0 <= index < len(self.itemList):
                    return self.itemList.pop(index)
                return None

            def expandingDirections(self):
                return Qt.Orientation(0)

            def hasHeightForWidth(self):
                return True

            def heightForWidth(self, width):
                height = self._do_layout(QRect(0, 0, width, 0), True)
                return height

            def setGeometry(self, rect):
                super().setGeometry(rect)
                self._do_layout(rect, False)

            def sizeHint(self):
                return self.minimumSize()

            def minimumSize(self):
                size = QSize()
                for item in self.itemList:
                    size = size.expandedTo(item.minimumSize())
                margin, _, _, _ = self.getContentsMargins()
                size += QSize(2 * margin, 2 * margin)
                return size

            def _do_layout(self, rect, test_only):
                x = rect.x()
                y = rect.y()
                line_height = 0
                spacing = self.spacing()

                for item in self.itemList:
                    wid = item.widget()
                    space_x = spacing + wid.style().layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
                    space_y = spacing + wid.style().layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)
                    
                    next_x = x + item.sizeHint().width() + space_x
                    if next_x - space_x > rect.right() and line_height > 0:
                        x = rect.x()
                        y = y + line_height + space_y
                        next_x = x + item.sizeHint().width() + space_x
                        line_height = 0

                    if not test_only:
                        item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

                    x = next_x
                    line_height = max(line_height, item.sizeHint().height())

                return y + line_height - rect.y()

        class ChatBackend(QObject):
            # Updated signal signature to include index
            message_added = pyqtSignal(int, str, str, str, name='message_added')
            
            def __init__(self, main_window):
                super().__init__()
                self.main_window = main_window

            @pyqtSlot(int)
            def copy_message(self, index):
                """Copies the text of a specific message to clipboard, stripping hidden files."""
                self.main_window.copy_message_to_clipboard(index)

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
                self.setWindowTitle("OR-Client (v2.6) - Enhanced Feedback & Input")
                self.setGeometry(100, 100, 1400, 900)
                
                # Initialize state variables
                self.models = []
                self.current_messages = [] # List of dicts: {role, content, model_name}
                self.current_conversation_id = None
                self.staged_files = [] 
                
                # 1. Setup UI first
                self._create_docks()
                self._setup_central_widget()
                
                # 2. Connect log signal
                log_signal.connect(self._append_log)
                
                # 3. Initialize Managers
                self.api_manager = ApiManager()
                self.threadpool = QThreadPool()
                self.token_counter = TokenCounter()
                
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
                # Left Dock (History & Logs)
                self.left_dock = QDockWidget("History & Logs", self)
                self.left_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
                
                # REMOVE TITLE BAR & DISABLE CLOSING
                self.left_dock.setTitleBarWidget(QWidget())
                self.left_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)

                left_widget = QWidget()
                left_layout = QVBoxLayout(left_widget)
                left_layout.setContentsMargins(5, 5, 5, 5)

                # --- Section 1: History ---
                left_layout.addWidget(QLabel("<b>Saved Conversations:</b>"))

                hist_btns = QHBoxLayout()
                self.new_chat_button = QPushButton("New Chat")
                self.new_chat_button.clicked.connect(self._new_chat)
                hist_btns.addWidget(self.new_chat_button)
                left_layout.addLayout(hist_btns)
                
                self.history_list = QListWidget()
                self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
                self.history_list.itemClicked.connect(self._load_conversation)
                left_layout.addWidget(self.history_list, 2)
                
                left_layout.addSpacing(10)

                # --- Section 2: Logs ---
                left_layout.addWidget(QLabel("<b>Application Logs:</b>"))

                self.log_output = QTextEdit()
                self.log_output.setReadOnly(True)
                # [UX] High Contrast: White background, Black text
                self.log_output.setStyleSheet("background-color: #ffffff; color: #000000; font-family: monospace; border: 1px solid #ccc;")
                left_layout.addWidget(self.log_output, 1)
                
                self.left_dock.setWidget(left_widget)
                self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)

                # Right Dock (Controls)
                self.controls_dock = QDockWidget("Controls", self)
                self.controls_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
                
                # REMOVE TITLE BAR & DISABLE CLOSING
                self.controls_dock.setTitleBarWidget(QWidget())
                self.controls_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)

                controls_widget = QWidget()
                controls_layout = QVBoxLayout(controls_widget)
                controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                
                # Model Selection
                controls_layout.addWidget(QLabel("<b>Model Selection:</b>"))
                self.model_combo = QComboBox()
                controls_layout.addWidget(self.model_combo)
                
                controls_layout.addSpacing(10)

                # System Prompt
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

                controls_layout.addSpacing(10)

                # Toggles
                self.chk_markdown = QCheckBox("Render Markdown")
                self.chk_markdown.setChecked(True)
                self.chk_markdown.toggled.connect(self._refresh_chat_view)
                controls_layout.addWidget(self.chk_markdown)

                self.chk_web_search = QCheckBox("Web Search")
                self.chk_web_search.setToolTip("Enable web search capabilities (if supported by model/API)")
                controls_layout.addWidget(self.chk_web_search)

                controls_layout.addSpacing(20)

                # Copy Full Chat
                self.btn_copy_all = QPushButton("Copy Full Conversation")
                self.btn_copy_all.clicked.connect(self._copy_full_chat)
                controls_layout.addWidget(self.btn_copy_all)

                controls_layout.addStretch()

                # Token Counter
                self.token_label = QLabel("Context: 0 tokens")
                self.token_label.setStyleSheet("color: #888; font-size: 12px;")
                self.token_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                controls_layout.addWidget(self.token_label)
                
                self.controls_dock.setWidget(controls_widget)
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.controls_dock)

            def _setup_central_widget(self):
                central_widget = QWidget()
                layout = QVBoxLayout(central_widget)
                
                # [UX] Resizable Layout: Use QSplitter
                splitter = QSplitter(Qt.Orientation.Vertical)
                
                # 1. Top Pane: Chat View
                self.chat_view = QWebEngineView()
                self._setup_web_channel()
                splitter.addWidget(self.chat_view)
                
                # 2. Bottom Pane: Input Container
                input_container = QWidget()
                input_layout = QVBoxLayout(input_container)
                input_layout.setContentsMargins(0, 5, 0, 0) # Small top margin for separation
                
                # Staging Area (Using FlowLayout)
                self.staging_container = QWidget()
                # [UX] Use FlowLayout to wrap attachments instead of widening window
                self.staging_layout = FlowLayout(self.staging_container) 
                self.staging_layout.setContentsMargins(0, 0, 0, 0)
                self.staging_container.setVisible(False)
                input_layout.addWidget(self.staging_container)

                # Input Row (Text + Attach)
                input_row = QHBoxLayout()
                
                self.input_box = QTextEdit()
                self.input_box.setPlaceholderText("Enter your message here...")
                # [UX] High Contrast: White background, Black text
                self.input_box.setStyleSheet("background-color: #ffffff; color: #000000; border: 1px solid #ccc;")
                
                # [FIX] Remove fixed height, set minimum height instead.
                self.input_box.setMinimumHeight(60) 
                
                input_row.addWidget(self.input_box)
                
                self.attach_btn = QPushButton("Attach")
                self.attach_btn.setToolTip("Attach File(s)")
                self.attach_btn.clicked.connect(self._attach_file)
                
                # [FIX] Allow the attach button to expand vertically with the text box
                self.attach_btn.setFixedWidth(60)
                self.attach_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                
                input_row.addWidget(self.attach_btn)
                
                # [FIX] Add stretch factor 1 to the input row so it claims the vertical space
                input_layout.addLayout(input_row, 1)

                # Send Button
                self.send_button = QPushButton("Send Message")
                self.send_button.clicked.connect(self.send_message)
                input_layout.addWidget(self.send_button)
                
                splitter.addWidget(input_container)
                
                # Set initial sizes (Chat gets priority)
                splitter.setStretchFactor(0, 4)
                splitter.setStretchFactor(1, 1)
                
                layout.addWidget(splitter)
                self.setCentralWidget(central_widget)

            def _setup_web_channel(self):
                self.chat_backend = ChatBackend(self)
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
                current_data = self.sys_prompt_combo.currentData()
                self.sys_prompt_combo.clear()
                self.sys_prompt_combo.addItem("None (Default)", None)
                
                prompts = self.db_manager.get_all_system_prompts()
                for p in prompts:
                    self.sys_prompt_combo.addItem(p['name'], p['prompt_text'])
                
                index = self.sys_prompt_combo.findData(current_data)
                if index >= 0:
                    self.sys_prompt_combo.setCurrentIndex(index)

            # --- Context Menu for History ---
            def _show_history_context_menu(self, position):
                item = self.history_list.itemAt(position)
                if not item: return

                menu = QMenu()
                rename_action = QAction("Rename", self)
                delete_action = QAction("Delete", self)
                
                rename_action.triggered.connect(lambda: self._rename_chat(item))
                delete_action.triggered.connect(lambda: self._delete_chat_item(item))
                
                menu.addAction(rename_action)
                menu.addAction(delete_action)
                menu.exec(self.history_list.viewport().mapToGlobal(position))

            def _rename_chat(self, item):
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                old_title = item.text()
                new_title, ok = QInputDialog.getText(self, "Rename Chat", "New Title:", text=old_title)
                
                if ok and new_title.strip():
                    success = self.db_manager.update_conversation_title(convo_id, new_title.strip())
                    if success:
                        item.setText(new_title.strip())
                        gui_print_success(f"Renamed chat to: {new_title}")

            def _delete_chat_item(self, item):
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                if QMessageBox.question(self, "Confirm", "Delete this chat?") == QMessageBox.StandardButton.Yes:
                    self.db_manager.delete_conversation(convo_id)
                    self.history_list.takeItem(self.history_list.row(item))
                    if self.current_conversation_id == convo_id: self._new_chat()

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
                
                # Reset system prompt combo (remove any temporary items)
                self._populate_system_prompts()
                self.sys_prompt_combo.setEnabled(True)
                
                self._update_token_count()
                gui_print_info("New chat context initialized.")

            @pyqtSlot(QListWidgetItem)
            def _load_conversation(self, item):
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                if convo_id == self.current_conversation_id: return

                self.current_conversation_id = convo_id
                
                # Load from DB
                messages_from_db = self.db_manager.get_messages_for_conversation(convo_id)
                
                self.current_messages = []
                self.staged_files = [] 
                self._update_staging_area()

                # Rebuild memory state
                for msg in messages_from_db:
                    role = msg["role"]
                    content = msg["content"]
                    model_used = msg.get("model_used")
                    
                    model_name = "Unknown"
                    if role == "assistant":
                        for i in range(self.model_combo.count()):
                            if self.model_combo.itemData(i) == model_used:
                                model_name = self.model_combo.itemText(i)
                                break
                    
                    self.current_messages.append({
                        "role": role, 
                        "content": content,
                        "model_name": model_name
                    })

                # --- System Prompt Sync Logic ---
                # 1. Reset the combo first to clear old temp items
                self._populate_system_prompts()
                
                # 2. Check if the conversation has a system prompt
                if self.current_messages and self.current_messages[0]['role'] == 'system':
                    sys_content = self.current_messages[0]['content']
                    
                    # 3. Try to find it in the existing list
                    index = self.sys_prompt_combo.findData(sys_content)
                    if index >= 0:
                        self.sys_prompt_combo.setCurrentIndex(index)
                    else:
                        # 4. If not found (Custom), add it temporarily so the user sees it
                        self.sys_prompt_combo.addItem("[Current Saved Prompt]", sys_content)
                        self.sys_prompt_combo.setCurrentIndex(self.sys_prompt_combo.count() - 1)
                else:
                    # No system prompt in this chat, set to None
                    self.sys_prompt_combo.setCurrentIndex(0)

                # Ensure it is ENABLED so user can change it mid-convo
                self.sys_prompt_combo.setEnabled(True)

                self._refresh_chat_view()
                self._update_token_count()
                gui_print_success(f"Loaded conversation {convo_id}.")

            def _refresh_chat_view(self):
                """Re-renders the entire chat view based on current messages and settings."""
                self.chat_view.page().runJavaScript("clearChat();")
                
                render_markdown = self.chk_markdown.isChecked()
                
                for index, msg in enumerate(self.current_messages):
                    role = msg["role"]
                    content = msg["content"]
                    model_name = msg.get("model_name", "")

                    if role == "system":
                        continue # Don't show system prompts in chat bubble flow

                    # 1. Separate Attachments from Text
                    clean_text, attachments = FileExtractor.strip_attachments_for_ui(content)
                    
                    # 2. Process Text (Markdown or Plain)
                    if render_markdown:
                        # Convert to HTML using markdown lib
                        # extensions=['fenced_code', 'tables'] handles code blocks and tables
                        html_text = markdown.markdown(clean_text, extensions=['fenced_code', 'tables'])
                    else:
                        html_text = html.escape(clean_text)

                    # 3. Re-append Attachment Indicators
                    indicators = ""
                    for filename, _ in attachments:
                        indicators += f'<span class="attachment-indicator">📎 [Attached: {filename}]</span>'
                    
                    final_html = html_text + indicators
                    
                    # 4. Send to Frontend
                    # We pass 'index' so the frontend can ask us to copy the source later
                    self.chat_backend.message_added.emit(index, role, final_html, model_name)

            # --- Token Counting ---
            def _update_token_count(self):
                count = self.token_counter.count_tokens(self.current_messages)
                self.token_label.setText(f"Context: ~{count:,} tokens")

            # --- Copy Logic ---
            def copy_message_to_clipboard(self, index):
                if 0 <= index < len(self.current_messages):
                    msg = self.current_messages[index]
                    raw_content = msg["content"]
                    # Strip hidden file data, keep indicator
                    clean_content = FileExtractor.strip_attachments_for_copy(raw_content)
                    QApplication.clipboard().setText(clean_content)
                    gui_print_info("Message copied to clipboard.")

            def _copy_full_chat(self):
                full_text = ""
                for msg in self.current_messages:
                    role = msg["role"]
                    if role == "system": continue
                    
                    raw_content = msg["content"]
                    clean_content = FileExtractor.strip_attachments_for_copy(raw_content)
                    
                    header = "You" if role == "user" else f"Assistant ({msg.get('model_name', 'AI')})"
                    full_text += f"--- {header} ---\n{clean_content}\n\n"
                
                if full_text:
                    QApplication.clipboard().setText(full_text)
                    gui_print_success("Full conversation copied to clipboard.")
                else:
                    gui_print_warning("Nothing to copy.")

            # --- File Attachment Logic ---

            @pyqtSlot()
            def _attach_file(self):
                filter_str = FileExtractor.get_supported_extensions()
                # [UX] Use getOpenFileNames for multi-selection
                files, _ = QFileDialog.getOpenFileNames(self, "Attach File(s)", "", filter_str)
                
                if files:
                    count = 0
                    for file_path in files:
                        if file_path not in self.staged_files:
                            self.staged_files.append(file_path)
                            count += 1
                    
                    if count > 0:
                        self._update_staging_area()
                        gui_print_info(f"Staged {count} file(s).")
                    else:
                        gui_print_warning("Selected file(s) already attached.")

            def _remove_staged_file(self, path_to_remove):
                if path_to_remove in self.staged_files:
                    self.staged_files.remove(path_to_remove)
                    self._update_staging_area()

            def _update_staging_area(self):
                # Clear existing items from FlowLayout
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
                    btn_del.clicked.connect(lambda checked, p=fpath: self._remove_staged_file(p))
                    chip_layout.addWidget(btn_del)
                    
                    self.staging_layout.addWidget(chip)
                
                # FlowLayout doesn't need addStretch()

            @pyqtSlot()
            def send_message(self):
                user_text = self.input_box.toPlainText().strip()
                
                if not user_text and not self.staged_files:
                    return
                
                if not self.api_manager.is_configured():
                    QMessageBox.warning(self, "Error", "API Key missing.")
                    return

                model_id = self.model_combo.currentData()
                temperature = self.temp_slider.value() / 100.0

                # --- SYSTEM PROMPT SYNC ---
                selected_prompt = self.sys_prompt_combo.currentData()
                
                if self.current_messages and self.current_messages[0]['role'] == 'system':
                    if selected_prompt:
                        self.current_messages[0]['content'] = selected_prompt
                    else:
                        self.current_messages.pop(0)
                elif selected_prompt:
                    self.current_messages.insert(0, {
                        "role": "system", 
                        "content": selected_prompt, 
                        "model_name": "System"
                    })
                # --------------------------

                # --- Process Attachments ---
                full_message_content = user_text
                
                if self.staged_files:
                    gui_print_info(f"Processing {len(self.staged_files)} attachments...")
                    for fpath in self.staged_files:
                        try:
                            raw_content = FileExtractor.extract_content(fpath)
                            fname = Path(fpath).name
                            attachment_payload = FileExtractor.create_attachment_payload(fname, raw_content)
                            full_message_content += attachment_payload
                        except Exception as e:
                            gui_print_error(f"Failed to attach {fname}: {e}")
                            QMessageBox.warning(self, "Attachment Error", f"Could not read {fname}:\n{e}")
                            return 

                    self.staged_files = []
                    self._update_staging_area()

                # --- New Conversation Logic ---
                if self.current_conversation_id is None:
                    title_text = user_text if user_text else "File Attachment"
                    title = title_text[:40] + "..." if len(title_text) > 40 else title_text
                    
                    new_id = self.db_manager.add_conversation(title)
                    if new_id == -1: return
                    
                    self.current_conversation_id = new_id
                    
                    new_item = QListWidgetItem(title)
                    new_item.setData(Qt.ItemDataRole.UserRole, new_id)
                    self.history_list.insertItem(0, new_item)
                    self.history_list.setCurrentItem(new_item)
                    
                    if self.current_messages and self.current_messages[0]['role'] == 'system':
                        self.db_manager.add_message(new_id, "system", self.current_messages[0]['content'], None, None)

                # --- Handle User Message ---
                self.db_manager.add_message(self.current_conversation_id, "user", full_message_content, None, None)
                
                self.current_messages.append({
                    "role": "user", 
                    "content": full_message_content,
                    "model_name": "You"
                })
                
                # Update UI
                new_msg_index = len(self.current_messages) - 1
                
                clean_text, attachments = FileExtractor.strip_attachments_for_ui(full_message_content)
                if self.chk_markdown.isChecked():
                    html_text = markdown.markdown(clean_text, extensions=['fenced_code', 'tables'])
                else:
                    html_text = html.escape(clean_text)
                
                indicators = ""
                for filename, _ in attachments:
                    indicators += f'<span class="attachment-indicator">📎 [Attached: {filename}]</span>'
                
                self.chat_backend.message_added.emit(new_msg_index, "user", html_text + indicators, "You")
                
                self.input_box.clear()
                self.set_ui_enabled(False)
                self._update_token_count()

                # [UX] Show "Thinking..." indicator immediately
                self.chat_view.page().runJavaScript("showThinking();")

                worker = ApiWorker(self.api_manager, model_id, self.current_messages, temperature)
                worker.signals.finished.connect(self.handle_api_response)
                worker.signals.error.connect(self.handle_api_error)
                # [UX] Connect first_token signal to update status
                worker.signals.first_token.connect(self.handle_first_token)
                self.threadpool.start(worker)

            @pyqtSlot()
            def handle_first_token(self):
                """Called when the first token is received from the API."""
                self.chat_view.page().runJavaScript("updateThinking('Generating Response...');")

            @pyqtSlot(dict)
            def handle_api_response(self, response):
                try:
                    # [UX] Remove Thinking indicator (it will be replaced by the message)
                    self.chat_view.page().runJavaScript("removeThinking();")

                    content = response['choices'][0]['message']['content']
                    model_name = self.model_combo.currentText()
                    
                    self.current_messages.append({
                        "role": "assistant", 
                        "content": content,
                        "model_name": model_name
                    })
                    
                    if self.current_conversation_id:
                        self.db_manager.add_message(
                            self.current_conversation_id, "assistant", content, 
                            self.model_combo.currentData(), self.temp_slider.value() / 100.0
                        )
                    
                    # Render Assistant Response
                    new_msg_index = len(self.current_messages) - 1
                    if self.chk_markdown.isChecked():
                        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
                    else:
                        html_content = html.escape(content)
                        
                    self.chat_backend.message_added.emit(new_msg_index, "assistant", html_content, model_name)
                    self._update_token_count()
                except Exception as e:
                    self.handle_api_error(f"Parse error: {e}")
                finally:
                    self.set_ui_enabled(True)

            @pyqtSlot(str)
            def handle_api_error(self, msg):
                # [UX] Ensure thinking indicator is gone on error
                self.chat_view.page().runJavaScript("removeThinking();")
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
