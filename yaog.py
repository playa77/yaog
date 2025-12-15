# YaOG -- Yet another Openrouter GUI
# Version: 3.5.0 (Strict Refactor)
# Description: Main Application Logic.
#
# Change Log (v3.5.0):
# - [Refactor] Split UI construction into ui_main_window.py.
# - [Refactor] Split ChatBackend into chat_backend.py.
# - [Compliance] File size strictly < 500 lines.

import sys
import json
import signal
import html
from pathlib import Path

# --- Local Imports ---
from api_manager import ApiManager
from database_manager import DatabaseManager
from settings_manager import SettingsManager, ModelManager
from utils import crash_handler, setup_project_files, LogStream, FileExtractor, TokenCounter
from worker_manager import ApiWorker
from ui_dialogs import SettingsDialog, SystemPromptDialog
from ui_main_window import MainWindowUI
from chat_backend import ChatBackend

sys.excepthook = crash_handler

def main_application():
    # Linux WebEngine Fixes
    if sys.platform == "linux":
        if '--no-sandbox' not in sys.argv: sys.argv.append('--no-sandbox')
        if '--disable-gpu' not in sys.argv: sys.argv.append('--disable-gpu')

    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QMessageBox, QListWidgetItem, QDialog, 
            QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QMenu, QInputDialog
        )
        from PyQt6.QtCore import Qt, QThreadPool, pyqtSlot, QTimer
        from PyQt6.QtGui import QAction, QFont
        from PyQt6.QtWebChannel import QWebChannel
        from PyQt6.QtWebEngineCore import QWebEngineProfile
        from dotenv import load_dotenv
        import markdown

        app = QApplication(sys.argv)

        # Ctrl+C Handling
        signal.signal(signal.SIGINT, lambda sig, frame: (QApplication.quit(), sys.exit(0)))
        QTimer().start(100) # Keep interpreter active

        # WebEngine Profile
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

        log_stream = LogStream()
        sys.stdout = log_stream 
        load_dotenv()

        class MainWindow(QMainWindow, MainWindowUI):
            def __init__(self, log_signal):
                super().__init__()
                self.setup_ui(self) # From MainWindowUI mixin
                
                self.current_messages = []
                self.current_conversation_id = None
                self.staged_files = [] 
                self.is_web_ready = False
                
                self.settings_manager = SettingsManager()
                self.model_manager = ModelManager()
                self.db_manager = DatabaseManager()
                self.api_manager = ApiManager(timeout=self.settings_manager.get("api_timeout"))
                
                self.threadpool = QThreadPool()
                self.token_counter = TokenCounter()

                log_signal.connect(self._append_log)
                self._connect_signals()
                self._setup_web_channel()
                
                self._populate_history_list()
                self._populate_system_prompts()
                self._populate_models()
                self._apply_ui_settings()

            def _connect_signals(self):
                self.new_chat_button.clicked.connect(self._new_chat)
                self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
                self.history_list.itemClicked.connect(self._load_conversation)
                self.manage_prompts_btn.clicked.connect(self._open_prompt_manager)
                self.temp_slider.valueChanged.connect(lambda val: self.temp_label.setText(f"{val/100.0:.2f}"))
                self.chk_markdown.toggled.connect(self._refresh_chat_view)
                self.btn_settings.clicked.connect(self._open_settings)
                self.btn_copy_all.clicked.connect(self._copy_full_chat)
                self.attach_btn.clicked.connect(self._attach_file)
                self.send_button.clicked.connect(self.send_message)
                self.chat_view.loadFinished.connect(self._on_page_load_finished)

            def _setup_web_channel(self):
                self.chat_backend = ChatBackend(self)
                self.channel = QWebChannel()
                self.channel.registerObject("backend", self.chat_backend)
                self.chat_view.page().setWebChannel(self.channel)

            @pyqtSlot(str)
            def _append_log(self, text):
                self.log_output.append(text.strip())
                self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

            @pyqtSlot()
            def _on_page_load_finished(self):
                self.is_web_ready = True
                self._apply_ui_settings()

            def _apply_ui_settings(self):
                font_size = self.settings_manager.get("font_size")
                font = QFont(); font.setPixelSize(font_size)
                self.input_box.setFont(font)
                self.history_list.setFont(font)
                if self.is_web_ready: self.chat_view.page().runJavaScript(f"setFontSize('{font_size}px');")

            # --- Data Population ---
            def _populate_models(self):
                self.model_combo.clear()
                for m in self.model_manager.get_all(): self.model_combo.addItem(m.get("name"), m.get("id"))

            def _populate_history_list(self):
                self.history_list.clear()
                for c in self.db_manager.get_all_conversations():
                    item = QListWidgetItem(c['title'])
                    item.setData(Qt.ItemDataRole.UserRole, c['id'])
                    self.history_list.addItem(item)

            def _populate_system_prompts(self):
                cur = self.sys_prompt_combo.currentData()
                self.sys_prompt_combo.clear()
                self.sys_prompt_combo.addItem("None (Default)", None)
                for p in self.db_manager.get_all_system_prompts():
                    self.sys_prompt_combo.addItem(p['name'], p['prompt_text'])
                idx = self.sys_prompt_combo.findData(cur)
                if idx >= 0: self.sys_prompt_combo.setCurrentIndex(idx)

            # --- Actions ---
            @pyqtSlot()
            def _open_settings(self):
                if SettingsDialog(self.settings_manager, self.model_manager, self.db_manager, self).exec():
                    self.api_manager = ApiManager(timeout=self.settings_manager.get("api_timeout"))
                    self._apply_ui_settings()
                    self._populate_models()
                    self._populate_history_list()

            @pyqtSlot()
            def _open_prompt_manager(self):
                SystemPromptDialog(self.db_manager, self).exec()
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
                self.sys_prompt_combo.setEnabled(True)
                self._update_token_count()

            # --- Chat Logic ---
            @pyqtSlot()
            def send_message(self):
                user_text = self.input_box.toPlainText().strip()
                if not user_text and not self.staged_files: return
                if not self.api_manager.is_configured():
                    return QMessageBox.warning(self, "Error", "API Key missing.")

                model_id = self.model_combo.currentData()
                model_name = self.model_combo.currentText()
                temp = self.temp_slider.value() / 100.0
                sys_prompt = self.sys_prompt_combo.currentData()

                # System Prompt Logic
                if self.current_messages and self.current_messages[0]['role'] == 'system':
                    if sys_prompt: self.current_messages[0]['content'] = sys_prompt
                    else: self.current_messages.pop(0)
                elif sys_prompt:
                    self.current_messages.insert(0, {"role": "system", "content": sys_prompt})

                # Attachments
                full_content = user_text
                for fpath in self.staged_files:
                    try:
                        full_content += FileExtractor.create_attachment_payload(Path(fpath).name, FileExtractor.extract_content(fpath))
                    except Exception as e: return QMessageBox.warning(self, "Error", str(e))
                self.staged_files = []; self._update_staging_area()

                # New Conversation
                if self.current_conversation_id is None:
                    title = (user_text[:40] + "...") if len(user_text) > 40 else (user_text or "Attachment")
                    self.current_conversation_id = self.db_manager.add_conversation(title)
                    item = QListWidgetItem(title); item.setData(Qt.ItemDataRole.UserRole, self.current_conversation_id)
                    self.history_list.insertItem(0, item); self.history_list.setCurrentItem(item)
                    if sys_prompt: self.db_manager.add_message(self.current_conversation_id, "system", sys_prompt, None, None)

                self.db_manager.add_message(self.current_conversation_id, "user", full_content, None, None)
                self.current_messages.append({"role": "user", "content": full_content})
                
                # Render User Msg
                clean, atts = FileExtractor.strip_attachments_for_ui(full_content)
                html_txt = markdown.markdown(clean, extensions=['fenced_code', 'tables']) if self.chk_markdown.isChecked() else html.escape(clean)
                for f, _ in atts: html_txt += f'<span class="attachment-indicator">📎 {f}</span>'
                self.chat_backend.message_added.emit(len(self.current_messages)-1, "user", html_txt, "You")
                
                self.input_box.clear(); self.set_ui_enabled(False); self._update_token_count()
                self.chat_view.page().runJavaScript("showThinking();")

                worker = ApiWorker(self.api_manager, model_id, self.current_messages, temp)
                worker.signals.first_token.connect(lambda: self.chat_view.page().runJavaScript(f"start_message({len(self.current_messages)}, 'assistant', '{model_name}');"))
                worker.signals.new_token.connect(self.chat_backend.stream_token)
                worker.signals.finished.connect(self.finalize_message)
                worker.signals.error.connect(self.handle_api_error)
                self.threadpool.start(worker)

            @pyqtSlot(dict)
            def finalize_message(self, response):
                try:
                    content = response['choices'][0]['message']['content']
                    self.current_messages.append({"role": "assistant", "content": content})
                    if self.current_conversation_id:
                        self.db_manager.add_message(self.current_conversation_id, "assistant", content, self.model_combo.currentData(), self.temp_slider.value()/100.0)
                    
                    html_c = markdown.markdown(content, extensions=['fenced_code', 'tables']) if self.chk_markdown.isChecked() else html.escape(content)
                    safe_html = html_c.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
                    self.chat_view.page().runJavaScript(f"finalize_message('{safe_html}');")
                    self._update_token_count()
                except Exception as e: self.handle_api_error(str(e))
                finally: self.set_ui_enabled(True)

            @pyqtSlot(str)
            def handle_api_error(self, msg):
                self.chat_view.page().runJavaScript("removeThinking();")
                self.set_ui_enabled(True)
                QMessageBox.critical(self, "API Error", msg)

            # --- Helpers ---
            def set_ui_enabled(self, enabled):
                self.send_button.setEnabled(enabled); self.input_box.setEnabled(enabled)
                self.attach_btn.setEnabled(enabled); self.controls_dock.setEnabled(enabled)
                self.send_button.setText("Send Message" if enabled else "Generating...")

            def _update_token_count(self):
                self.token_label.setText(f"Context: ~{self.token_counter.count_tokens(self.current_messages):,} tokens")

            def copy_message_to_clipboard(self, index):
                if 0 <= index < len(self.current_messages):
                    QApplication.clipboard().setText(FileExtractor.strip_attachments_for_copy(self.current_messages[index]["content"]))

            def _copy_full_chat(self):
                txt = ""
                for m in self.current_messages:
                    if m['role'] == 'system': continue
                    txt += f"--- {m['role'].upper()} ---\n{FileExtractor.strip_attachments_for_copy(m['content'])}\n\n"
                QApplication.clipboard().setText(txt)

            @pyqtSlot(QListWidgetItem)
            def _load_conversation(self, item):
                cid = item.data(Qt.ItemDataRole.UserRole)
                if cid == self.current_conversation_id: return
                self.current_conversation_id = cid
                self.current_messages = []
                self.staged_files = []; self._update_staging_area()
                
                for msg in self.db_manager.get_messages_for_conversation(cid):
                    self.current_messages.append({"role": msg["role"], "content": msg["content"]})
                
                self._populate_system_prompts()
                if self.current_messages and self.current_messages[0]['role'] == 'system':
                    idx = self.sys_prompt_combo.findData(self.current_messages[0]['content'])
                    self.sys_prompt_combo.setCurrentIndex(idx if idx >= 0 else 0)
                
                self._refresh_chat_view(); self._update_token_count()

            def _refresh_chat_view(self):
                self.chat_view.page().runJavaScript("clearChat();")
                for i, m in enumerate(self.current_messages):
                    if m['role'] == 'system': continue
                    clean, atts = FileExtractor.strip_attachments_for_ui(m['content'])
                    h = markdown.markdown(clean, extensions=['fenced_code', 'tables']) if self.chk_markdown.isChecked() else html.escape(clean)
                    for f, _ in atts: h += f'<span class="attachment-indicator">📎 {f}</span>'
                    self.chat_backend.message_added.emit(i, m['role'], h, "AI")

            def _show_history_context_menu(self, pos):
                menu = QMenu()
                menu.addAction("Import Chat (JSON)", self._import_chat)
                item = self.history_list.itemAt(pos)
                if item:
                    menu.addAction("Rename", lambda: self._rename_chat(item))
                    menu.addAction("Delete", lambda: self._delete_chat_item(item))
                    menu.addAction("Export JSON", lambda: self._export_chat(item))
                menu.exec(self.history_list.viewport().mapToGlobal(pos))

            def _import_chat(self):
                fpath, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
                if not fpath: return
                try:
                    with open(fpath) as f: data = json.load(f)
                    if data.get("type") != "or-client-chat": raise ValueError("Invalid type")
                    nid = self.db_manager.add_conversation(data.get("title", "Imported") + " (Imported)")
                    for m in data.get("messages", []): self.db_manager.add_message(nid, m['role'], m['content'], None, 0.7)
                    self._populate_history_list()
                except Exception as e: QMessageBox.critical(self, "Error", str(e))

            def _export_chat(self, item):
                cid = item.data(Qt.ItemDataRole.UserRole)
                data = {"type": "or-client-chat", "title": item.text(), "messages": self.db_manager.get_messages_for_conversation(cid)}
                fpath, _ = QFileDialog.getSaveFileName(self, "Export", f"{item.text()}.json", "JSON (*.json)")
                if fpath: 
                    with open(fpath, "w") as f: json.dump(data, f, indent=2)

            def _rename_chat(self, item):
                new, ok = QInputDialog.getText(self, "Rename", "Title:", text=item.text())
                if ok and new.strip():
                    self.db_manager.update_conversation_title(item.data(Qt.ItemDataRole.UserRole), new.strip())
                    item.setText(new.strip())

            def _delete_chat_item(self, item):
                if QMessageBox.question(self, "Confirm", "Delete?") == QMessageBox.StandardButton.Yes:
                    self.db_manager.delete_conversation(item.data(Qt.ItemDataRole.UserRole))
                    self.history_list.takeItem(self.history_list.row(item))
                    if self.current_conversation_id == item.data(Qt.ItemDataRole.UserRole): self._new_chat()

            def _attach_file(self):
                files, _ = QFileDialog.getOpenFileNames(self, "Attach", "", FileExtractor.get_supported_extensions())
                for f in files: 
                    if f not in self.staged_files: self.staged_files.append(f)
                self._update_staging_area()

            def _update_staging_area(self):
                while self.staging_layout.count(): 
                    w = self.staging_layout.takeAt(0).widget()
                    if w: w.deleteLater()
                self.staging_container.setVisible(bool(self.staged_files))
                for f in self.staged_files:
                    chip = QFrame(); chip.setStyleSheet("background-color: #3c3c3c; border-radius: 5px;")
                    l = QHBoxLayout(chip); l.setContentsMargins(5,2,5,2)
                    l.addWidget(QLabel(Path(f).name, styleSheet="color: white;"))
                    btn = QPushButton("x", styleSheet="background-color: #d32f2f; color: white; border-radius: 10px;"); btn.setFixedSize(20,20)
                    btn.clicked.connect(lambda _, p=f: (self.staged_files.remove(p), self._update_staging_area()))
                    l.addWidget(btn); self.staging_layout.addWidget(chip)

        window = MainWindow(log_stream.log_signal)
        window.showMaximized()
        sys.exit(app.exec())

    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup_project_files()
    main_application()
