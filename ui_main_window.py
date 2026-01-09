# ui_main_window.py for YaOG
# Version: 5.2.3 (Tooltip Positioning Fix)
# Description: Implements "Above and Left" positioning for custom tooltips.

from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QTextEdit, QListWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QComboBox, QSlider, QCheckBox, 
    QSplitter, QSizePolicy, QFrame, QScrollArea, QGroupBox, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, QUrl, QSize, QObject, QTimer, QEvent, QPoint
from PyQt6.QtGui import QCursor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from ui_layouts import FlowLayout
from utils import resource_path
import os

class TooltipManager(QObject):
    """
    Manages a custom, snappy tooltip that mimics Google AI Studio's style.
    Bypasses the native OS tooltip system for consistent styling and behavior.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.view = QLabel(parent)
        self.view.setObjectName("custom_tooltip")
        # ToolTip flag makes it a top-level window that sits above others
        self.view.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) 
        self.view.hide()
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(100) # Fast 100ms delay
        self.timer.timeout.connect(self.show_now)
        
        self._target = None
        self._text = ""

    def attach(self, widget, text):
        """Attaches the custom tooltip to a widget."""
        widget.installEventFilter(self)
        widget.setProperty("tooltip_text", text)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            self._target = obj
            self._text = obj.property("tooltip_text")
            self.timer.start()
            return False
        elif event.type() == QEvent.Type.Leave:
            self.timer.stop()
            self.view.hide()
            self._target = None
            return False
        elif event.type() == QEvent.Type.MouseButtonPress:
            self.view.hide()
            return False
        return False

    def show_now(self):
        if not self._target or not self._target.underMouse(): 
            return
            
        self.view.setText(self._text)
        self.view.adjustSize()
        
        # Get global mouse position
        cursor_pos = QCursor.pos()
        
        # Calculate position: Above and Left of cursor
        # The bottom-right corner of the tooltip anchors near the cursor
        tooltip_w = self.view.width()
        tooltip_h = self.view.height()
        
        # Offset: 10px up, 0px left (align right edge to cursor)
        x = cursor_pos.x() - tooltip_w
        y = cursor_pos.y() - tooltip_h - 10
        
        # Screen Boundary Check
        screen = self.view.screen()
        if not screen:
            screen = QApplication.primaryScreen()
            
        if screen:
            geo = screen.geometry()
            # Prevent going off left edge
            if x < geo.left() + 5:
                x = geo.left() + 5
            # Prevent going off top edge
            if y < geo.top() + 5:
                # If too close to top, flip to below the cursor
                y = cursor_pos.y() + 20

        self.view.move(x, y)
        self.view.raise_()
        self.view.show()


class MainWindowUI:
    def setup_ui(self, main_window):
        main_window.setWindowTitle("YaOG v5.2.3")
        main_window.setGeometry(100, 100, 1400, 900)
        
        # Initialize Custom Tooltip Manager
        main_window.tooltip_manager = TooltipManager(main_window)
        
        self._create_docks(main_window)
        self._setup_central_widget(main_window)

    def _create_docks(self, mw):
        # --- Left Dock ---
        mw.left_dock = QDockWidget("History", mw)
        mw.left_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        mw.left_dock.setTitleBarWidget(QWidget())
        mw.left_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        
        left_widget = QWidget()
        left_widget.setObjectName("sidebar_container") # Dark Theme Root
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Header Area
        header_frame = QFrame()
        header_frame.setObjectName("sidebar_header") 
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        mw.new_chat_button = QPushButton("+ New Chat")
        mw.new_chat_button.setObjectName("new_chat_btn") # Special Blue Style
        mw.new_chat_button.setCursor(Qt.CursorShape.PointingHandCursor)
        mw.new_chat_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        mw.tooltip_manager.attach(mw.new_chat_button, "Start a new conversation (Ctrl+N)")
        
        header_layout.addWidget(mw.new_chat_button)
        left_layout.addWidget(header_frame)

        # History List
        mw.history_list = QListWidget()
        mw.history_list.setObjectName("history_list")
        mw.history_list.setFrameShape(QFrame.Shape.NoFrame)
        mw.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        mw.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_layout.addWidget(mw.history_list, 2)
        
        # Logs
        mw.log_label = QLabel("  SYSTEM LOGS")
        mw.log_label.setObjectName("log_label_header") 
        left_layout.addWidget(mw.log_label)
        
        mw.log_output = QTextEdit()
        mw.log_output.setObjectName("log_output")
        mw.log_output.setReadOnly(True)
        mw.log_output.setFrameShape(QFrame.Shape.NoFrame)
        left_layout.addWidget(mw.log_output, 1)
        
        mw.left_dock.setWidget(left_widget)
        mw.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, mw.left_dock)

        # --- Right Dock ---
        mw.controls_dock = QDockWidget("Controls", mw)
        mw.controls_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        mw.controls_dock.setTitleBarWidget(QWidget())
        mw.controls_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: #111827;") 
        
        controls_widget = QWidget()
        controls_widget.setObjectName("sidebar_container") # Dark Theme Root
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        controls_layout.setContentsMargins(15, 20, 15, 20)
        controls_layout.setSpacing(25)
        
        # -- Group 1: Configuration --
        grp_config = QGroupBox("CONFIGURATION")
        grp_config_layout = QVBoxLayout(grp_config)
        grp_config_layout.setSpacing(10)
        
        grp_config_layout.addWidget(QLabel("Model Selection"))
        mw.model_combo = QComboBox()
        grp_config_layout.addWidget(mw.model_combo)
        
        grp_config_layout.addWidget(QLabel("System Persona"))
        mw.sys_prompt_combo = QComboBox()
        mw.sys_prompt_combo.addItem("None (Default)", None)
        grp_config_layout.addWidget(mw.sys_prompt_combo)
        
        controls_layout.addWidget(grp_config)

        # -- Group 2: Parameters --
        grp_params = QGroupBox("PARAMETERS")
        grp_params_layout = QGridLayout(grp_params)
        grp_params_layout.setVerticalSpacing(12)
        
        grp_params_layout.addWidget(QLabel("Temperature"), 0, 0)
        mw.temp_label = QLabel("1.00")
        mw.temp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grp_params_layout.addWidget(mw.temp_label, 0, 1)
        
        mw.temp_slider = QSlider(Qt.Orientation.Horizontal)
        mw.temp_slider.setRange(0, 40)
        mw.temp_slider.setValue(20)
        grp_params_layout.addWidget(mw.temp_slider, 1, 0, 1, 2)
        
        mw.chk_markdown = QCheckBox("Render Markdown")
        mw.chk_markdown.setChecked(True)
        grp_params_layout.addWidget(mw.chk_markdown, 2, 0, 1, 2)
        
        mw.chk_web_search = QCheckBox("Web Search (:online)")
        grp_params_layout.addWidget(mw.chk_web_search, 3, 0, 1, 2)

        mw.chk_reasoning = QCheckBox("Reasoning (CoT)")
        grp_params_layout.addWidget(mw.chk_reasoning, 4, 0, 1, 2)
        
        controls_layout.addWidget(grp_params)

        # -- Group 3: Actions --
        grp_actions = QGroupBox("ACTIONS")
        grp_actions_layout = QGridLayout(grp_actions)
        grp_actions_layout.setSpacing(10)
        
        mw.btn_settings = QPushButton("Settings")
        mw.btn_settings.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        mw.tooltip_manager.attach(mw.btn_settings, "Configure application settings")
        grp_actions_layout.addWidget(mw.btn_settings, 0, 0)
        
        mw.manage_prompts_btn = QPushButton("Prompts")
        mw.manage_prompts_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        mw.tooltip_manager.attach(mw.manage_prompts_btn, "Manage system personas")
        grp_actions_layout.addWidget(mw.manage_prompts_btn, 0, 1)
        
        mw.btn_copy_chat = QPushButton("Copy Chat")
        mw.btn_copy_chat.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        mw.tooltip_manager.attach(mw.btn_copy_chat, "Copy readable transcript")
        grp_actions_layout.addWidget(mw.btn_copy_chat, 1, 0)

        mw.btn_copy_context = QPushButton("Copy All")
        mw.btn_copy_context.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        mw.tooltip_manager.attach(mw.btn_copy_context, "Copy raw context with files")
        grp_actions_layout.addWidget(mw.btn_copy_context, 1, 1)
        
        controls_layout.addWidget(grp_actions)
        
        controls_layout.addStretch()
        mw.token_label = QLabel("Context: 0 tokens")
        mw.token_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        mw.token_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(mw.token_label)
        
        scroll.setWidget(controls_widget)
        mw.controls_dock.setWidget(scroll)
        mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, mw.controls_dock)

    def _setup_central_widget(self, mw):
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #D1D5DB; }") 
        
        mw.chat_view = QWebEngineView()
        html_path = resource_path(os.path.join("assets", "chat_template.html"))
        mw.chat_view.setUrl(QUrl.fromLocalFile(html_path))
        splitter.addWidget(mw.chat_view)
        
        input_container = QWidget()
        input_container.setStyleSheet("background-color: #E5E7EB;") 
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(20, 10, 20, 20)
        
        mw.staging_container = QWidget()
        mw.staging_layout = FlowLayout(mw.staging_container) 
        mw.staging_container.setVisible(False)
        input_layout.addWidget(mw.staging_container)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        
        mw.input_box = QTextEdit()
        mw.input_box.setPlaceholderText("Type a message... (Ctrl+Enter to send)")
        mw.input_box.setMinimumHeight(80)
        mw.input_box.setMaximumHeight(160)
        input_row.addWidget(mw.input_box)
        
        mw.attach_btn = QPushButton("Attach")
        mw.attach_btn.setObjectName("attach_button")
        mw.tooltip_manager.attach(mw.attach_btn, "Attach files")
        input_row.addWidget(mw.attach_btn)
        
        input_layout.addLayout(input_row)

        send_row = QHBoxLayout()
        send_row.addStretch()
        
        mw.send_button = QPushButton("Send Message")
        mw.send_button.setObjectName("send_button")
        mw.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        mw.tooltip_manager.attach(mw.send_button, "Send message (Ctrl+Enter)")
        send_row.addWidget(mw.send_button)
        
        input_layout.addLayout(send_row)
        
        splitter.addWidget(input_container)
        splitter.setStretchFactor(0, 10)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        mw.setCentralWidget(central_widget)
