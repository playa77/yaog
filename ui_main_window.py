# ui_main_window.py for YaOG
# Version: 4.1.3 (Final Polish)
# Description: Handles the visual construction of the Main Window.

from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QTextEdit, QListWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QComboBox, QSlider, QCheckBox, 
    QSplitter, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from ui_layouts import FlowLayout
from utils import resource_path

class MainWindowUI:
    """
    Mixin class that handles the UI setup for the MainWindow.
    """
    def setup_ui(self, main_window):
        # UPDATED: Version number to match main script
        main_window.setWindowTitle("YaOG (v4.1.3)")
        main_window.setGeometry(100, 100, 1400, 900)
        
        self._create_docks(main_window)
        self._setup_central_widget(main_window)

    def _create_docks(self, mw):
        # --- Left Dock (History & Logs) ---
        mw.left_dock = QDockWidget("History & Logs", mw)
        mw.left_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        mw.left_dock.setTitleBarWidget(QWidget())
        mw.left_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        hist_btns = QHBoxLayout()
        mw.new_chat_button = QPushButton("New Chat")
        hist_btns.addWidget(mw.new_chat_button)
        left_layout.addLayout(hist_btns)

        left_layout.addWidget(QLabel("<b>Saved Conversations:</b>"))
        mw.history_list = QListWidget()
        mw.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        left_layout.addWidget(mw.history_list, 2)
        
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("<b>Application Logs:</b>"))
        mw.log_output = QTextEdit()
        mw.log_output.setReadOnly(True)
        mw.log_output.setStyleSheet("background-color: #ffffff; color: #000000; font-family: monospace; border: 1px solid #ccc;")
        left_layout.addWidget(mw.log_output, 1)
        
        mw.left_dock.setWidget(left_widget)
        mw.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, mw.left_dock)

        # --- Right Dock (Controls) ---
        mw.controls_dock = QDockWidget("Controls", mw)
        mw.controls_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        mw.controls_dock.setTitleBarWidget(QWidget())
        mw.controls_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        controls_layout.addWidget(QLabel("<b>Model Selection:</b>"))
        mw.model_combo = QComboBox()
        controls_layout.addWidget(mw.model_combo)
        controls_layout.addSpacing(10)

        controls_layout.addWidget(QLabel("<b>System Prompt:</b>"))
        mw.sys_prompt_combo = QComboBox()
        mw.sys_prompt_combo.addItem("None (Default)", None)
        controls_layout.addWidget(mw.sys_prompt_combo)
        
        mw.manage_prompts_btn = QPushButton("Manage Prompts")
        controls_layout.addWidget(mw.manage_prompts_btn)
        controls_layout.addSpacing(10)
        
        controls_layout.addWidget(QLabel("<b>Temperature:</b>"))
        temp_layout = QHBoxLayout()
        mw.temp_slider = QSlider(Qt.Orientation.Horizontal)
        mw.temp_slider.setRange(0, 200)
        mw.temp_slider.setValue(100)
        mw.temp_label = QLabel("1.00")
        temp_layout.addWidget(mw.temp_slider)
        temp_layout.addWidget(mw.temp_label)
        controls_layout.addLayout(temp_layout)
        controls_layout.addSpacing(10)

        mw.chk_markdown = QCheckBox("Render Markdown")
        mw.chk_markdown.setChecked(True)
        controls_layout.addWidget(mw.chk_markdown)
        
        # Phase 3: Capabilities Checkboxes
        mw.chk_web_search = QCheckBox("Web Search (:online)")
        mw.chk_web_search.setToolTip("Appends ':online' to model ID to force web search.")
        controls_layout.addWidget(mw.chk_web_search)

        mw.chk_reasoning = QCheckBox("Reasoning")
        mw.chk_reasoning.setToolTip("Requests 'include_reasoning' parameter for supported models.")
        controls_layout.addWidget(mw.chk_reasoning)
        
        controls_layout.addSpacing(20)

        mw.btn_settings = QPushButton("Settings")
        mw.btn_settings.setIcon(QIcon.fromTheme("preferences-system"))
        controls_layout.addWidget(mw.btn_settings)
        controls_layout.addSpacing(10)

        mw.btn_copy_all = QPushButton("Copy Full Conversation")
        controls_layout.addWidget(mw.btn_copy_all)
        controls_layout.addStretch()

        mw.token_label = QLabel("Context: 0 tokens")
        mw.token_label.setStyleSheet("color: #888; font-size: 12px;")
        mw.token_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(mw.token_label)
        
        mw.controls_dock.setWidget(controls_widget)
        mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, mw.controls_dock)

    def _setup_central_widget(self, mw):
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        mw.chat_view = QWebEngineView()
        html_path = resource_path("chat_template.html")
        mw.chat_view.setUrl(QUrl.fromLocalFile(html_path))
        splitter.addWidget(mw.chat_view)
        
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 5, 0, 0)
        
        mw.staging_container = QWidget()
        mw.staging_layout = FlowLayout(mw.staging_container) 
        mw.staging_container.setVisible(False)
        input_layout.addWidget(mw.staging_container)

        input_row = QHBoxLayout()
        mw.input_box = QTextEdit()
        mw.input_box.setPlaceholderText("Enter your message here...")
        mw.input_box.setStyleSheet("background-color: #ffffff; color: #000000; border: 1px solid #ccc;")
        mw.input_box.setMinimumHeight(60) 
        input_row.addWidget(mw.input_box)
        
        mw.attach_btn = QPushButton("Attach")
        mw.attach_btn.setFixedWidth(60)
        mw.attach_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        input_row.addWidget(mw.attach_btn)
        input_layout.addLayout(input_row, 1)

        mw.send_button = QPushButton("Send Message")
        input_layout.addWidget(mw.send_button)
        
        splitter.addWidget(input_container)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        mw.setCentralWidget(central_widget)
