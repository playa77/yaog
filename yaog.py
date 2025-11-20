# YaOG -- Yet another Openrouter GUI
# Version: 3.2
# Description: Instructive Roadmap - M3/M4 (Settings, Data Management, Models)
#
# Change Log (v3.2):
# - [Build] Implemented resource_path() for single-file executable bundling.
#
# Change Log (v3.1):
# - [Branding] Corrected application name to "YaOG".
# - [UX] Moved "Import Chat" to the History List context menu.
# - [UX] Context menu now functions on empty space (for Import) and items (for Edit/Export).

import os
import sys
import json
import time
import signal
import html
import re
from pathlib import Path
from datetime import datetime

# --- Local Imports ---
from api_manager import ApiManager
from database_manager import DatabaseManager
from settings_manager import SettingsManager, ModelManager
from utils import crash_handler, setup_project_files, LogStream, FileExtractor, TokenCounter, EnvManager, resource_path
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
            QLayout, QFormLayout, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
            QHeaderView, QAbstractItemView
        )
        from PyQt6.QtCore import (
            Qt, QThreadPool, QObject, pyqtSignal, pyqtSlot, QUrl, QTimer, QSize, QPoint, QRect
        )
        from PyQt6.QtGui import QIcon, QAction, QFont
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineProfile
        from PyQt6.QtWebChannel import QWebChannel
        from dotenv import load_dotenv
        
        try:
            import markdown
        except ImportError:
            print("[FATAL] 'markdown' library missing. Run: pip install markdown", file=sys.stderr)
            sys.exit(1)

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
            def __init__(self, parent=None, margin=0, spacing=-1):
                super().__init__(parent)
                if parent is not None: self.setContentsMargins(margin, margin, margin, margin)
                self.setSpacing(spacing)
                self.itemList = []
            def __del__(self):
                item = self.takeAt(0)
                while item: item = self.takeAt(0)
            def addItem(self, item): self.itemList.append(item)
            def count(self): return len(self.itemList)
            def itemAt(self, index): return self.itemList[index] if 0 <= index < len(self.itemList) else None
            def takeAt(self, index): return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None
            def expandingDirections(self): return Qt.Orientation(0)
            def hasHeightForWidth(self): return True
            def heightForWidth(self, width): return self._do_layout(QRect(0, 0, width, 0), True)
            def setGeometry(self, rect): super().setGeometry(rect); self._do_layout(rect, False)
            def sizeHint(self): return self.minimumSize()
            def minimumSize(self):
                size = QSize()
                for item in self.itemList: size = size.expandedTo(item.minimumSize())
                margin, _, _, _ = self.getContentsMargins()
                size += QSize(2 * margin, 2 * margin)
                return size
            def _do_layout(self, rect, test_only):
                x, y = rect.x(), rect.y()
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
                    if not test_only: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                    x = next_x
                    line_height = max(line_height, item.sizeHint().height())
                return y + line_height - rect.y()

        class ChatBackend(QObject):
            message_added = pyqtSignal(int, str, str, str, name='message_added')
            def __init__(self, main_window):
                super().__init__()
                self.main_window = main_window
            @pyqtSlot(int)
            def copy_message(self, index):
                self.main_window.copy_message_to_clipboard(index)

        # --- Settings Dialog (Tabbed) ---
        class SettingsDialog(QDialog):
            def __init__(self, settings_manager, model_manager, db_manager, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Settings & Configuration")
                self.resize(600, 500)
                self.settings_manager = settings_manager
                self.model_manager = model_manager
                self.db_manager = db_manager
                self._init_ui()

            def _init_ui(self):
                layout = QVBoxLayout(self)
                self.tabs = QTabWidget()
                
                self.tabs.addTab(self._create_general_tab(), "General")
                self.tabs.addTab(self._create_api_tab(), "API & Network")
                self.tabs.addTab(self._create_models_tab(), "Models")
                self.tabs.addTab(self._create_data_tab(), "Data & Backup")
                
                layout.addWidget(self.tabs)
                
                # Bottom Buttons
                btn_layout = QHBoxLayout()
                self.btn_close = QPushButton("Close")
                self.btn_close.clicked.connect(self.accept)
                btn_layout.addStretch()
                btn_layout.addWidget(self.btn_close)
                layout.addLayout(btn_layout)

            def _create_general_tab(self):
                widget = QWidget()
                layout = QFormLayout(widget)
                
                self.font_spin = QSpinBox()
                self.font_spin.setRange(8, 32)
                self.font_spin.setSuffix(" px")
                self.font_spin.setValue(self.settings_manager.get("font_size"))
                self.font_spin.valueChanged.connect(self._save_general)
                
                layout.addRow("Chat Font Size:", self.font_spin)
                return widget

            def _save_general(self):
                self.settings_manager.set("font_size", self.font_spin.value())

            def _create_api_tab(self):
                widget = QWidget()
                layout = QVBoxLayout(widget)
                
                form = QFormLayout()
                
                # Timeout
                self.timeout_spin = QSpinBox()
                self.timeout_spin.setRange(10, 600)
                self.timeout_spin.setSuffix(" s")
                self.timeout_spin.setValue(self.settings_manager.get("api_timeout"))
                self.timeout_spin.valueChanged.connect(lambda: self.settings_manager.set("api_timeout", self.timeout_spin.value()))
                form.addRow("Request Timeout:", self.timeout_spin)
                
                layout.addLayout(form)
                layout.addSpacing(20)
                
                # API Key
                layout.addWidget(QLabel("<b>OpenRouter API Key:</b>"))
                
                key_layout = QHBoxLayout()
                self.key_input = QLineEdit()
                self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
                self.key_input.setText(EnvManager.get_api_key())
                
                self.btn_reveal = QPushButton("Show")
                self.btn_reveal.setCheckable(True)
                self.btn_reveal.toggled.connect(lambda checked: self.key_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password))
                self.btn_reveal.toggled.connect(lambda checked: self.btn_reveal.setText("Hide" if checked else "Show"))
                
                key_layout.addWidget(self.key_input)
                key_layout.addWidget(self.btn_reveal)
                layout.addLayout(key_layout)
                
                self.btn_save_key = QPushButton("Update API Key")
                self.btn_save_key.clicked.connect(self._save_api_key)
                layout.addWidget(self.btn_save_key)
                
                layout.addWidget(QLabel("<small>Updates .env file. Requires restart for some libraries, but app will try to reload.</small>"))
                layout.addStretch()
                return widget

            def _save_api_key(self):
                new_key = self.key_input.text().strip()
                if EnvManager.save_api_key(new_key):
                    QMessageBox.information(self, "Success", "API Key updated in .env file.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to write to .env file.")

            def _create_models_tab(self):
                widget = QWidget()
                layout = QVBoxLayout(widget)
                
                self.model_table = QTableWidget()
                self.model_table.setColumnCount(2)
                self.model_table.setHorizontalHeaderLabels(["Name", "Model ID"])
                self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                self.model_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                self.model_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                self.model_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
                
                layout.addWidget(self.model_table)
                
                btn_row = QHBoxLayout()
                self.btn_add_model = QPushButton("Add")
                self.btn_edit_model = QPushButton("Edit")
                self.btn_del_model = QPushButton("Delete")
                
                self.btn_add_model.clicked.connect(self._add_model)
                self.btn_edit_model.clicked.connect(self._edit_model)
                self.btn_del_model.clicked.connect(self._del_model)
                
                btn_row.addWidget(self.btn_add_model)
                btn_row.addWidget(self.btn_edit_model)
                btn_row.addWidget(self.btn_del_model)
                layout.addLayout(btn_row)
                
                self._refresh_model_list()
                return widget

            def _refresh_model_list(self):
                self.model_table.setRowCount(0)
                models = self.model_manager.get_all()
                self.model_table.setRowCount(len(models))
                for i, m in enumerate(models):
                    self.model_table.setItem(i, 0, QTableWidgetItem(m['name']))
                    self.model_table.setItem(i, 1, QTableWidgetItem(m['id']))

            def _add_model(self):
                name, ok1 = QInputDialog.getText(self, "Add Model", "Display Name:")
                if not ok1 or not name: return
                mid, ok2 = QInputDialog.getText(self, "Add Model", "Model ID (e.g. vendor/name):")
                if not ok2 or not mid: return
                
                if self.model_manager.add_model(name, mid):
                    self._refresh_model_list()
                else:
                    QMessageBox.warning(self, "Error", "Model ID already exists.")

            def _edit_model(self):
                row = self.model_table.currentRow()
                if row < 0: return
                
                old_name = self.model_table.item(row, 0).text()
                old_id = self.model_table.item(row, 1).text()
                
                name, ok1 = QInputDialog.getText(self, "Edit Model", "Display Name:", text=old_name)
                if not ok1: return
                mid, ok2 = QInputDialog.getText(self, "Edit Model", "Model ID:", text=old_id)
                if not ok2: return
                
                self.model_manager.update_model(row, name, mid)
                self._refresh_model_list()

            def _del_model(self):
                row = self.model_table.currentRow()
                if row < 0: return
                if QMessageBox.question(self, "Confirm", "Delete this model?") == QMessageBox.StandardButton.Yes:
                    self.model_manager.delete_model(row)
                    self._refresh_model_list()

            def _create_data_tab(self):
                widget = QWidget()
                layout = QVBoxLayout(widget)
                
                layout.addWidget(QLabel("<b>Data Management</b>"))
                
                info_label = QLabel(
                    "To <b>Import</b> or <b>Export</b> chats, please right-click inside the "
                    "'Saved Conversations' list on the main screen."
                )
                info_label.setWordWrap(True)
                layout.addWidget(info_label)
                
                layout.addStretch()
                return widget

        # --- System Prompt Dialog (Updated) ---
        class SystemPromptDialog(QDialog):
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
                
                # Left Side
                left_layout = QVBoxLayout()
                self.prompt_list = QListWidget()
                self.prompt_list.itemClicked.connect(self._on_item_clicked)
                left_layout.addWidget(QLabel("Saved Prompts:"))
                left_layout.addWidget(self.prompt_list)
                
                self.btn_new = QPushButton("New Prompt")
                self.btn_new.clicked.connect(self._reset_form)
                left_layout.addWidget(self.btn_new)
                
                # Import/Export Buttons
                io_layout = QHBoxLayout()
                self.btn_import = QPushButton("Import")
                self.btn_export = QPushButton("Export")
                self.btn_import.clicked.connect(self._import_prompt)
                self.btn_export.clicked.connect(self._export_prompt)
                io_layout.addWidget(self.btn_import)
                io_layout.addWidget(self.btn_export)
                left_layout.addLayout(io_layout)
                
                # Right Side
                right_layout = QVBoxLayout()
                self.name_input = QLineEdit()
                self.name_input.setPlaceholderText("Prompt Name")
                right_layout.addWidget(QLabel("Name:"))
                right_layout.addWidget(self.name_input)
                
                self.content_input = QTextEdit()
                self.content_input.setPlaceholderText("Enter system instructions...")
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

                splitter = QSplitter(Qt.Orientation.Horizontal)
                left_widget = QWidget(); left_widget.setLayout(left_layout)
                right_widget = QWidget(); right_widget.setLayout(right_layout)
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
                self.btn_export.setEnabled(True)

            def _reset_form(self):
                self.current_prompt_id = None
                self.name_input.clear()
                self.content_input.clear()
                self.prompt_list.clearSelection()
                self.btn_delete.setEnabled(False)
                self.btn_export.setEnabled(False)

            def _save_prompt(self):
                name = self.name_input.text().strip()
                content = self.content_input.toPlainText().strip()
                if not name or not content: return
                if self.current_prompt_id:
                    self.db_manager.update_system_prompt(self.current_prompt_id, name, content)
                else:
                    self.db_manager.add_system_prompt(name, content)
                self._load_prompts()

            def _delete_prompt(self):
                if self.current_prompt_id:
                    self.db_manager.delete_system_prompt(self.current_prompt_id)
                    self._load_prompts()

            def _export_prompt(self):
                if not self.current_prompt_id: return
                name = self.name_input.text()
                content = self.content_input.toPlainText()
                data = {"type": "or-client-prompt", "name": name, "content": content}
                
                fpath, _ = QFileDialog.getSaveFileName(self, "Export Prompt", f"{name}.json", "JSON Files (*.json)")
                if fpath:
                    with open(fpath, "w") as f: json.dump(data, f, indent=2)

            def _import_prompt(self):
                fpath, _ = QFileDialog.getOpenFileName(self, "Import Prompt", "", "JSON Files (*.json)")
                if fpath:
                    try:
                        with open(fpath, "r") as f: data = json.load(f)
                        if data.get("type") != "or-client-prompt": raise ValueError("Invalid type")
                        self.name_input.setText(data.get("name", "") + " (Imported)")
                        self.content_input.setPlainText(data.get("content", ""))
                        self.current_prompt_id = None # Treat as new
                        self.btn_save.setFocus()
                    except Exception as e:
                        QMessageBox.warning(self, "Error", str(e))

        # --- Main Window ---
        class MainWindow(QMainWindow):
            def __init__(self, log_signal):
                super().__init__()
                self.setWindowTitle("YaOG (v3.2)")
                self.setGeometry(100, 100, 1400, 900)
                
                self.current_messages = []
                self.current_conversation_id = None
                self.staged_files = [] 
                self.is_web_ready = False
                
                self.settings_manager = SettingsManager()
                self.model_manager = ModelManager()
                
                # Reload API manager with current key/timeout
                self._init_api_manager()
                
                self.threadpool = QThreadPool()
                self.token_counter = TokenCounter()
                self.db_manager = DatabaseManager()

                self._create_docks()
                self._setup_central_widget()
                log_signal.connect(self._append_log)
                
                self._populate_history_list()
                self._populate_system_prompts()
                self._populate_models()
                self._apply_ui_settings()

            def _init_api_manager(self):
                # Re-reads env var in case it changed
                load_dotenv(override=True)
                timeout = self.settings_manager.get("api_timeout")
                self.api_manager = ApiManager(timeout=timeout)

            def closeEvent(self, event):
                self.threadpool.waitForDone(1000)
                if self.db_manager: self.db_manager.close()
                event.accept()

            @pyqtSlot(str)
            def _append_log(self, text):
                self.log_output.append(text.strip())
                self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

            def _apply_ui_settings(self):
                font_size = self.settings_manager.get("font_size")
                font = QFont()
                font.setPixelSize(font_size)
                self.input_box.setFont(font)
                self.history_list.setFont(font)
                if self.is_web_ready:
                    self.chat_view.page().runJavaScript(f"setFontSize('{font_size}px');")

            def _create_docks(self):
                # Left Dock
                self.left_dock = QDockWidget("History & Logs", self)
                self.left_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
                self.left_dock.setTitleBarWidget(QWidget())
                self.left_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
                left_widget = QWidget()
                left_layout = QVBoxLayout(left_widget)
                left_layout.setContentsMargins(5, 5, 5, 5)

                hist_btns = QHBoxLayout()
                self.new_chat_button = QPushButton("New Chat")
                self.new_chat_button.clicked.connect(self._new_chat)
                hist_btns.addWidget(self.new_chat_button)
                left_layout.addLayout(hist_btns)

                left_layout.addWidget(QLabel("<b>Saved Conversations:</b>"))
                self.history_list = QListWidget()
                self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
                self.history_list.itemClicked.connect(self._load_conversation)
                left_layout.addWidget(self.history_list, 2)
                
                left_layout.addSpacing(10)
                left_layout.addWidget(QLabel("<b>Application Logs:</b>"))
                self.log_output = QTextEdit()
                self.log_output.setReadOnly(True)
                self.log_output.setStyleSheet("background-color: #ffffff; color: #000000; font-family: monospace; border: 1px solid #ccc;")
                left_layout.addWidget(self.log_output, 1)
                self.left_dock.setWidget(left_widget)
                self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)

                # Right Dock
                self.controls_dock = QDockWidget("Controls", self)
                self.controls_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
                self.controls_dock.setTitleBarWidget(QWidget())
                self.controls_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
                controls_widget = QWidget()
                controls_layout = QVBoxLayout(controls_widget)
                controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                
                controls_layout.addWidget(QLabel("<b>Model Selection:</b>"))
                self.model_combo = QComboBox()
                controls_layout.addWidget(self.model_combo)
                controls_layout.addSpacing(10)

                controls_layout.addWidget(QLabel("<b>System Prompt:</b>"))
                self.sys_prompt_combo = QComboBox()
                self.sys_prompt_combo.addItem("None (Default)", None)
                controls_layout.addWidget(self.sys_prompt_combo)
                
                self.manage_prompts_btn = QPushButton("Manage Prompts")
                self.manage_prompts_btn.clicked.connect(self._open_prompt_manager)
                controls_layout.addWidget(self.manage_prompts_btn)
                controls_layout.addSpacing(10)
                
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

                self.chk_markdown = QCheckBox("Render Markdown")
                self.chk_markdown.setChecked(True)
                self.chk_markdown.toggled.connect(self._refresh_chat_view)
                controls_layout.addWidget(self.chk_markdown)
                self.chk_web_search = QCheckBox("Web Search")
                controls_layout.addWidget(self.chk_web_search)
                controls_layout.addSpacing(20)

                self.btn_settings = QPushButton("Settings")
                self.btn_settings.setIcon(QIcon.fromTheme("preferences-system"))
                self.btn_settings.clicked.connect(self._open_settings)
                controls_layout.addWidget(self.btn_settings)
                controls_layout.addSpacing(10)

                self.btn_copy_all = QPushButton("Copy Full Conversation")
                self.btn_copy_all.clicked.connect(self._copy_full_chat)
                controls_layout.addWidget(self.btn_copy_all)
                controls_layout.addStretch()

                self.token_label = QLabel("Context: 0 tokens")
                self.token_label.setStyleSheet("color: #888; font-size: 12px;")
                self.token_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                controls_layout.addWidget(self.token_label)
                
                self.controls_dock.setWidget(controls_widget)
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.controls_dock)

            def _setup_central_widget(self):
                central_widget = QWidget()
                layout = QVBoxLayout(central_widget)
                splitter = QSplitter(Qt.Orientation.Vertical)
                
                self.chat_view = QWebEngineView()
                self._setup_web_channel()
                self.chat_view.loadFinished.connect(self._on_page_load_finished)
                splitter.addWidget(self.chat_view)
                
                input_container = QWidget()
                input_layout = QVBoxLayout(input_container)
                input_layout.setContentsMargins(0, 5, 0, 0)
                
                self.staging_container = QWidget()
                self.staging_layout = FlowLayout(self.staging_container) 
                self.staging_container.setVisible(False)
                input_layout.addWidget(self.staging_container)

                input_row = QHBoxLayout()
                self.input_box = QTextEdit()
                self.input_box.setPlaceholderText("Enter your message here...")
                self.input_box.setStyleSheet("background-color: #ffffff; color: #000000; border: 1px solid #ccc;")
                self.input_box.setMinimumHeight(60) 
                input_row.addWidget(self.input_box)
                
                self.attach_btn = QPushButton("Attach")
                self.attach_btn.clicked.connect(self._attach_file)
                self.attach_btn.setFixedWidth(60)
                self.attach_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                input_row.addWidget(self.attach_btn)
                input_layout.addLayout(input_row, 1)

                self.send_button = QPushButton("Send Message")
                self.send_button.clicked.connect(self.send_message)
                input_layout.addWidget(self.send_button)
                
                splitter.addWidget(input_container)
                splitter.setStretchFactor(0, 4)
                splitter.setStretchFactor(1, 1)
                layout.addWidget(splitter)
                self.setCentralWidget(central_widget)

            @pyqtSlot()
            def _on_page_load_finished(self):
                self.is_web_ready = True
                self._apply_ui_settings()

            def _setup_web_channel(self):
                self.chat_backend = ChatBackend(self)
                self.channel = QWebChannel()
                self.channel.registerObject("backend", self.chat_backend)
                self.chat_view.page().setWebChannel(self.channel)
                
                # Use resource_path to find the HTML file even if bundled
                html_path = resource_path("chat_template.html")
                self.chat_view.setUrl(QUrl.fromLocalFile(html_path))

            def _populate_models(self):
                self.model_combo.clear()
                models = self.model_manager.get_all()
                for model in models:
                    self.model_combo.addItem(model.get("name"), model.get("id"))

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
                if index >= 0: self.sys_prompt_combo.setCurrentIndex(index)

            # --- Settings & Data Logic ---
            @pyqtSlot()
            def _open_settings(self):
                dialog = SettingsDialog(self.settings_manager, self.model_manager, self.db_manager, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # Reload everything that might have changed
                    self._init_api_manager()
                    self._apply_ui_settings()
                    self._populate_models()
                    self._populate_history_list() # In case of import
                    gui_print_success("Settings applied.")

            def _show_history_context_menu(self, position):
                item = self.history_list.itemAt(position)
                
                menu = QMenu()
                
                # Action available always (Import)
                import_action = QAction("Import Chat (JSON)", self)
                import_action.triggered.connect(self._import_chat)
                
                if item:
                    # Actions specific to an existing chat
                    rename_action = QAction("Rename", self)
                    delete_action = QAction("Delete", self)
                    export_action = QAction("Export JSON", self)
                    
                    rename_action.triggered.connect(lambda: self._rename_chat(item))
                    delete_action.triggered.connect(lambda: self._delete_chat_item(item))
                    export_action.triggered.connect(lambda: self._export_chat(item))
                    
                    menu.addAction(rename_action)
                    menu.addAction(delete_action)
                    menu.addSeparator()
                    menu.addAction(export_action)
                    menu.addSeparator()
                
                # Add Import at the bottom or top, depending on preference. 
                # Adding at bottom for now.
                menu.addAction(import_action)
                
                menu.exec(self.history_list.viewport().mapToGlobal(position))

            def _import_chat(self):
                fpath, _ = QFileDialog.getOpenFileName(self, "Import Chat", "", "JSON Files (*.json)")
                if not fpath: return
                
                try:
                    with open(fpath, "r") as f:
                        data = json.load(f)
                    
                    if data.get("type") != "or-client-chat":
                        raise ValueError("Invalid file format (missing type identifier).")
                    
                    title = data.get("title", "Imported Chat")
                    messages = data.get("messages", [])
                    
                    new_id = self.db_manager.add_conversation(f"{title} (Imported)")
                    for msg in messages:
                        self.db_manager.add_message(
                            new_id, msg['role'], msg['content'], msg.get('model'), 0.7
                        )
                    
                    self._populate_history_list()
                    gui_print_success("Chat imported successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Import Error", str(e))

            def _export_chat(self, item):
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                title = item.text()
                msgs = self.db_manager.get_messages_for_conversation(convo_id)
                
                data = {
                    "type": "or-client-chat",
                    "version": "1.0",
                    "title": title,
                    "messages": msgs
                }
                
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
                fpath, _ = QFileDialog.getSaveFileName(self, "Export Chat", f"{safe_title}.json", "JSON Files (*.json)")
                if fpath:
                    try:
                        with open(fpath, "w") as f: json.dump(data, f, indent=2)
                        gui_print_success(f"Exported: {fpath}")
                    except Exception as e:
                        gui_print_error(f"Export failed: {e}")

            def _rename_chat(self, item):
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                old_title = item.text()
                new_title, ok = QInputDialog.getText(self, "Rename Chat", "New Title:", text=old_title)
                if ok and new_title.strip():
                    if self.db_manager.update_conversation_title(convo_id, new_title.strip()):
                        item.setText(new_title.strip())

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
                self._populate_system_prompts()
                self.sys_prompt_combo.setEnabled(True)
                self._update_token_count()
                gui_print_info("New chat context initialized.")

            @pyqtSlot(QListWidgetItem)
            def _load_conversation(self, item):
                convo_id = item.data(Qt.ItemDataRole.UserRole)
                if convo_id == self.current_conversation_id: return
                self.current_conversation_id = convo_id
                
                messages_from_db = self.db_manager.get_messages_for_conversation(convo_id)
                self.current_messages = []
                self.staged_files = [] 
                self._update_staging_area()

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
                    self.current_messages.append({"role": role, "content": content, "model_name": model_name})

                self._populate_system_prompts()
                if self.current_messages and self.current_messages[0]['role'] == 'system':
                    sys_content = self.current_messages[0]['content']
                    index = self.sys_prompt_combo.findData(sys_content)
                    if index >= 0: self.sys_prompt_combo.setCurrentIndex(index)
                    else:
                        self.sys_prompt_combo.addItem("[Current Saved Prompt]", sys_content)
                        self.sys_prompt_combo.setCurrentIndex(self.sys_prompt_combo.count() - 1)
                else:
                    self.sys_prompt_combo.setCurrentIndex(0)
                self.sys_prompt_combo.setEnabled(True)
                self._refresh_chat_view()
                self._update_token_count()

            def _refresh_chat_view(self):
                self.chat_view.page().runJavaScript("clearChat();")
                render_markdown = self.chk_markdown.isChecked()
                for index, msg in enumerate(self.current_messages):
                    role = msg["role"]
                    content = msg["content"]
                    model_name = msg.get("model_name", "")
                    if role == "system": continue
                    clean_text, attachments = FileExtractor.strip_attachments_for_ui(content)
                    if render_markdown: html_text = markdown.markdown(clean_text, extensions=['fenced_code', 'tables'])
                    else: html_text = html.escape(clean_text)
                    indicators = ""
                    for filename, _ in attachments:
                        indicators += f'<span class="attachment-indicator">📎 [Attached: {filename}]</span>'
                    self.chat_backend.message_added.emit(index, role, html_text + indicators, model_name)

            def _update_token_count(self):
                count = self.token_counter.count_tokens(self.current_messages)
                self.token_label.setText(f"Context: ~{count:,} tokens")

            def copy_message_to_clipboard(self, index):
                if 0 <= index < len(self.current_messages):
                    msg = self.current_messages[index]
                    clean_content = FileExtractor.strip_attachments_for_copy(msg["content"])
                    QApplication.clipboard().setText(clean_content)

            def _copy_full_chat(self):
                full_text = ""
                for msg in self.current_messages:
                    role = msg["role"]
                    if role == "system": continue
                    clean_content = FileExtractor.strip_attachments_for_copy(msg["content"])
                    header = "You" if role == "user" else f"Assistant ({msg.get('model_name', 'AI')})"
                    full_text += f"--- {header} ---\n{clean_content}\n\n"
                if full_text: QApplication.clipboard().setText(full_text)

            @pyqtSlot()
            def _attach_file(self):
                filter_str = FileExtractor.get_supported_extensions()
                files, _ = QFileDialog.getOpenFileNames(self, "Attach File(s)", "", filter_str)
                if files:
                    for file_path in files:
                        if file_path not in self.staged_files: self.staged_files.append(file_path)
                    self._update_staging_area()

            def _remove_staged_file(self, path_to_remove):
                if path_to_remove in self.staged_files:
                    self.staged_files.remove(path_to_remove)
                    self._update_staging_area()

            def _update_staging_area(self):
                while self.staging_layout.count():
                    child = self.staging_layout.takeAt(0)
                    if child.widget(): child.widget().deleteLater()
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

            @pyqtSlot()
            def send_message(self):
                user_text = self.input_box.toPlainText().strip()
                if not user_text and not self.staged_files: return
                
                # Check API Key
                if not self.api_manager.is_configured():
                    QMessageBox.warning(self, "Configuration Error", "API Key is missing or invalid.\nPlease go to Settings > API & Network to configure it.")
                    return

                model_id = self.model_combo.currentData()
                temperature = self.temp_slider.value() / 100.0
                selected_prompt = self.sys_prompt_combo.currentData()
                
                if self.current_messages and self.current_messages[0]['role'] == 'system':
                    if selected_prompt: self.current_messages[0]['content'] = selected_prompt
                    else: self.current_messages.pop(0)
                elif selected_prompt:
                    self.current_messages.insert(0, {"role": "system", "content": selected_prompt, "model_name": "System"})

                full_message_content = user_text
                if self.staged_files:
                    for fpath in self.staged_files:
                        try:
                            raw_content = FileExtractor.extract_content(fpath)
                            fname = Path(fpath).name
                            full_message_content += FileExtractor.create_attachment_payload(fname, raw_content)
                        except Exception as e:
                            QMessageBox.warning(self, "Attachment Error", f"Could not read {fname}:\n{e}")
                            return 
                    self.staged_files = []
                    self._update_staging_area()

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

                self.db_manager.add_message(self.current_conversation_id, "user", full_message_content, None, None)
                self.current_messages.append({"role": "user", "content": full_message_content, "model_name": "You"})
                
                new_msg_index = len(self.current_messages) - 1
                clean_text, attachments = FileExtractor.strip_attachments_for_ui(full_message_content)
                if self.chk_markdown.isChecked(): html_text = markdown.markdown(clean_text, extensions=['fenced_code', 'tables'])
                else: html_text = html.escape(clean_text)
                indicators = ""
                for filename, _ in attachments: indicators += f'<span class="attachment-indicator">📎 [Attached: {filename}]</span>'
                self.chat_backend.message_added.emit(new_msg_index, "user", html_text + indicators, "You")
                
                self.input_box.clear()
                self.set_ui_enabled(False)
                self._update_token_count()
                self.chat_view.page().runJavaScript("showThinking();")

                worker = ApiWorker(self.api_manager, model_id, self.current_messages, temperature)
                worker.signals.finished.connect(self.handle_api_response)
                worker.signals.error.connect(self.handle_api_error)
                worker.signals.first_token.connect(self.handle_first_token)
                self.threadpool.start(worker)

            @pyqtSlot()
            def handle_first_token(self):
                self.chat_view.page().runJavaScript("updateThinking('Generating Response...');")

            @pyqtSlot(dict)
            def handle_api_response(self, response):
                try:
                    self.chat_view.page().runJavaScript("removeThinking();")
                    content = response['choices'][0]['message']['content']
                    model_name = self.model_combo.currentText()
                    self.current_messages.append({"role": "assistant", "content": content, "model_name": model_name})
                    if self.current_conversation_id:
                        self.db_manager.add_message(self.current_conversation_id, "assistant", content, self.model_combo.currentData(), self.temp_slider.value() / 100.0)
                    new_msg_index = len(self.current_messages) - 1
                    if self.chk_markdown.isChecked(): html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
                    else: html_content = html.escape(content)
                    self.chat_backend.message_added.emit(new_msg_index, "assistant", html_content, model_name)
                    self._update_token_count()
                except Exception as e: self.handle_api_error(f"Parse error: {e}")
                finally: self.set_ui_enabled(True)

            @pyqtSlot(str)
            def handle_api_error(self, msg):
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
