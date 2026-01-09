# ui_dialogs.py for YaOG
# Version: 5.0.0 (Phase 3: Dialog Refactor)
# Description: Implements the "Sidebar Navigation" pattern for Settings and Prompts.

import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QStackedWidget, QWidget, QFormLayout,
    QSpinBox, QLabel, QLineEdit, QPushButton, QMessageBox, QTableWidget,
    QHeaderView, QAbstractItemView, QTableWidgetItem, QInputDialog,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from utils import EnvManager

# --- Settings Dialog (Sidebar Pattern) ---
class SettingsDialog(QDialog):
    def __init__(self, settings_manager, model_manager, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(750, 550)
        self.settings_manager = settings_manager
        self.model_manager = model_manager
        self.db_manager = db_manager
        self._init_ui()

    def _init_ui(self):
        # Root Layout: Horizontal (Sidebar | Content)
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Left Sidebar ---
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setFrameShape(QFrame.Shape.NoFrame)
        # Styling handled by Global QSS (assets/style.qss), but we enforce background here to be safe
        self.sidebar.setStyleSheet("background-color: #F8F9FA; border-right: 1px solid #EBEEF5; outline: none;")
        
        # Sidebar Items
        items = ["General", "API & Network", "Models", "Data & Backup"]
        for i in items:
            item = QListWidgetItem(i)
            item.setSizeHint(QSize(0, 40)) # Taller click targets
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.sidebar.addItem(item)
            
        root_layout.addWidget(self.sidebar)

        # --- Right Content Area ---
        content_container = QWidget()
        content_container.setStyleSheet("background-color: #FFFFFF;")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_general_page())
        self.pages.addWidget(self._create_api_page())
        self.pages.addWidget(self._create_models_page())
        self.pages.addWidget(self._create_data_page())
        
        content_layout.addWidget(self.pages)
        
        # Bottom Button Row (Inside Content Area)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_close = QPushButton("Close")
        self.btn_close.setFixedWidth(100)
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)
        
        content_layout.addSpacing(20)
        content_layout.addLayout(btn_row)
        
        root_layout.addWidget(content_container)

        # Logic: Connect Sidebar to Stack
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

    # -- Page 1: General --
    def _create_general_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel("General Configuration")
        title.setStyleSheet("font-size: 18px; font-weight: 600; margin-bottom: 15px;")
        layout.addWidget(title)
        
        form = QFormLayout()
        form.setSpacing(15)
        
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 32)
        self.font_spin.setSuffix(" px")
        self.font_spin.setValue(self.settings_manager.get("font_size"))
        self.font_spin.valueChanged.connect(self._save_general)
        
        form.addRow("Chat Font Size:", self.font_spin)
        layout.addLayout(form)
        layout.addStretch()
        return widget

    def _save_general(self):
        self.settings_manager.set("font_size", self.font_spin.value())

    # -- Page 2: API --
    def _create_api_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel("API & Network")
        title.setStyleSheet("font-size: 18px; font-weight: 600; margin-bottom: 15px;")
        layout.addWidget(title)
        
        form = QFormLayout()
        form.setSpacing(15)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)
        self.timeout_spin.setSuffix(" s")
        self.timeout_spin.setValue(self.settings_manager.get("api_timeout"))
        self.timeout_spin.valueChanged.connect(lambda: self.settings_manager.set("api_timeout", self.timeout_spin.value()))
        form.addRow("Request Timeout:", self.timeout_spin)
        layout.addLayout(form)
        
        layout.addSpacing(20)
        layout.addWidget(QLabel("<b>OpenRouter API Key</b>"))
        
        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setText(EnvManager.get_api_key())
        
        self.btn_reveal = QPushButton("Show")
        self.btn_reveal.setCheckable(True)
        self.btn_reveal.setFixedWidth(60)
        self.btn_reveal.toggled.connect(lambda c: self.key_input.setEchoMode(QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        self.btn_reveal.toggled.connect(lambda c: self.btn_reveal.setText("Hide" if c else "Show"))
        
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.btn_reveal)
        layout.addLayout(key_layout)
        
        self.btn_save_key = QPushButton("Update Key")
        self.btn_save_key.clicked.connect(self._save_api_key)
        layout.addWidget(self.btn_save_key)
        
        layout.addStretch()
        return widget

    def _save_api_key(self):
        if EnvManager.save_api_key(self.key_input.text().strip()):
            QMessageBox.information(self, "Success", "API Key updated.")
        else:
            QMessageBox.critical(self, "Error", "Failed to write to .env file.")

    # -- Page 3: Models --
    def _create_models_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("Model Management")
        title.setStyleSheet("font-size: 18px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(2)
        self.model_table.setHorizontalHeaderLabels(["Display Name", "Model ID"])
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.model_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.model_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.model_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.model_table.verticalHeader().setVisible(False)
        self.model_table.setShowGrid(False)
        self.model_table.setAlternatingRowColors(True)
        layout.addWidget(self.model_table)
        
        btn_row = QHBoxLayout()
        self.btn_add_model = QPushButton("Add")
        self.btn_edit_model = QPushButton("Edit")
        self.btn_del_model = QPushButton("Delete")
        self.btn_move_up = QPushButton("Up")
        self.btn_move_down = QPushButton("Down")
        
        # Set fixed widths for these small action buttons
        for btn in [self.btn_add_model, self.btn_edit_model, self.btn_del_model, self.btn_move_up, self.btn_move_down]:
            btn.setFixedWidth(80)

        self.btn_add_model.clicked.connect(self._add_model)
        self.btn_edit_model.clicked.connect(self._edit_model)
        self.btn_del_model.clicked.connect(self._del_model)
        self.btn_move_up.clicked.connect(self._move_up)
        self.btn_move_down.clicked.connect(self._move_down)
        
        btn_row.addWidget(self.btn_add_model)
        btn_row.addWidget(self.btn_edit_model)
        btn_row.addWidget(self.btn_del_model)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_move_up)
        btn_row.addWidget(self.btn_move_down)
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
        mid, ok2 = QInputDialog.getText(self, "Add Model", "Model ID:")
        if not ok2 or not mid: return
        if self.model_manager.add_model(name, mid): self._refresh_model_list()

    def _edit_model(self):
        row = self.model_table.currentRow()
        if row < 0: return
        old_name = self.model_table.item(row, 0).text()
        old_id = self.model_table.item(row, 1).text()
        name, ok1 = QInputDialog.getText(self, "Edit", "Name:", text=old_name)
        if not ok1: return
        mid, ok2 = QInputDialog.getText(self, "Edit", "ID:", text=old_id)
        if not ok2: return
        self.model_manager.update_model(row, name, mid)
        self._refresh_model_list()

    def _del_model(self):
        row = self.model_table.currentRow()
        if row >= 0 and QMessageBox.question(self, "Confirm", "Delete?") == QMessageBox.StandardButton.Yes:
            self.model_manager.delete_model(row)
            self._refresh_model_list()

    def _move_up(self):
        row = self.model_table.currentRow()
        if self.model_manager.move_up(row):
            self._refresh_model_list()
            self.model_table.selectRow(row - 1)

    def _move_down(self):
        row = self.model_table.currentRow()
        if self.model_manager.move_down(row):
            self._refresh_model_list()
            self.model_table.selectRow(row + 1)

    # -- Page 4: Data --
    def _create_data_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel("Data & Backup")
        title.setStyleSheet("font-size: 18px; font-weight: 600; margin-bottom: 15px;")
        layout.addWidget(title)
        
        info = QLabel(
            "Conversations are stored locally in <b>~/.or-client/or-client.db</b>.<br><br>"
            "To Import or Export individual chats, right-click on the 'Saved Conversations' list "
            "in the main window."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #606266; line-height: 1.4;")
        layout.addWidget(info)
        
        layout.addStretch()
        return widget


# --- System Prompt Dialog (Splitter Pattern) ---
class SystemPromptDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage System Personas")
        self.resize(900, 600)
        self.db_manager = db_manager
        self.current_prompt_id = None
        self._init_ui()
        self._load_prompts()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Splitter for resizable panes
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Pane: List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        left_layout.addWidget(QLabel("<b>Saved Personas</b>"))
        self.prompt_list = QListWidget()
        self.prompt_list.setFrameShape(QFrame.Shape.NoFrame)
        self.prompt_list.setStyleSheet("background-color: #F8F9FA; border: 1px solid #DCDFE6; border-radius: 4px;")
        self.prompt_list.itemClicked.connect(self._on_item_clicked)
        left_layout.addWidget(self.prompt_list)
        
        self.btn_new = QPushButton("New Persona")
        self.btn_new.clicked.connect(self._reset_form)
        left_layout.addWidget(self.btn_new)
        
        io_layout = QHBoxLayout()
        self.btn_import = QPushButton("Import")
        self.btn_export = QPushButton("Export")
        self.btn_import.setFixedWidth(80)
        self.btn_export.setFixedWidth(80)
        
        self.btn_import.clicked.connect(self._import_prompt)
        self.btn_export.clicked.connect(self._export_prompt)
        io_layout.addWidget(self.btn_import)
        io_layout.addWidget(self.btn_export)
        io_layout.addStretch()
        left_layout.addLayout(io_layout)
        
        # Right Pane: Editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        right_layout.addWidget(QLabel("<b>Name</b>"))
        self.name_input = QLineEdit()
        right_layout.addWidget(self.name_input)
        
        right_layout.addWidget(QLabel("<b>Instructions</b>"))
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("You are a helpful assistant...")
        right_layout.addWidget(self.content_input)
        
        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Changes")
        self.btn_save.clicked.connect(self._save_prompt)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("background-color: #FF3B30; color: white; border: none;")
        self.btn_delete.clicked.connect(self._delete_prompt)
        
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_delete)
        right_layout.addLayout(btn_row)

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
        data = {"type": "or-client-prompt", "name": name, "content": self.content_input.toPlainText()}
        fpath, _ = QFileDialog.getSaveFileName(self, "Export", f"{name}.json", "JSON (*.json)")
        if fpath:
            with open(fpath, "w") as f: json.dump(data, f, indent=2)

    def _import_prompt(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
        if fpath:
            try:
                with open(fpath, "r") as f: data = json.load(f)
                if data.get("type") != "or-client-prompt": raise ValueError("Invalid type")
                self.name_input.setText(data.get("name", "") + " (Imported)")
                self.content_input.setPlainText(data.get("content", ""))
                self.current_prompt_id = None
                self.btn_save.setFocus()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
