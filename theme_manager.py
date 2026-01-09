# theme_manager.py for YaOG v5.0
# Version: 5.0.0
# Description: Handles loading and applying the Global UI Contract (QSS).

import os
import sys
from PyQt6.QtWidgets import QApplication
from utils import resource_path

class ThemeManager:
    """
    Responsible for locating, loading, and applying the global stylesheet.
    """
    
    @staticmethod
    def load_theme(app: QApplication):
        """
        Loads 'assets/style.qss' and applies it to the QApplication instance.
        """
        # Resolve path using utils.resource_path to support PyInstaller
        qss_path = resource_path(os.path.join("assets", "style.qss"))
        
        if not os.path.exists(qss_path):
            print(f"[WARNING] Theme file not found at: {qss_path}", file=sys.stderr)
            return

        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                qss_content = f.read()
                
                # Optional: Pre-process QSS here if we need dynamic variable replacement
                # e.g., replacing placeholders for Dark Mode in the future.
                
                app.setStyleSheet(qss_content)
                print(f"[INFO] Theme loaded successfully from {qss_path}")
                
        except Exception as e:
            print(f"[ERROR] Failed to load theme: {e}", file=sys.stderr)

# --- Test Block ---
if __name__ == "__main__":
    # Simple test to verify syntax and loading
    from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    ThemeManager.load_theme(app)
    
    window = QWidget()
    window.setWindowTitle("Theme Test")
    layout = QVBoxLayout(window)
    
    btn = QPushButton("Standard Button")
    btn_send = QPushButton("Send Button")
    btn_send.setObjectName("send_button")
    
    layout.addWidget(btn)
    layout.addWidget(btn_send)
    
    window.show()
    sys.exit(app.exec())
