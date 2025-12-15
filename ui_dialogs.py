# ui_dialogs.py for YaOG (yaog.py)
# Version: 3.4.1 (Refactor)
# Description: Secondary dialog windows (Settings, System Prompts).

import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QSpinBox, QLabel, QLineEdit, QPushButton, QMessageBox, QTableWidget,
    QHeaderView, QAbstractItemView, QTableWidgetItem, QInputDialog,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QFileDialog
)
from PyQt6.QtCore import Qt
from utils import EnvManager

# --- Settings Dialog ---
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


# --- System Prompt Dialog ---
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
