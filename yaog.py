# Script Version: 5.2.1 | Last Updated: 2025-12-18
# Description: Main Application Logic. Version bump for Refined Slate UI updates.

import sys
import json
import signal
import html
import re
from pathlib import Path

# --- Local Imports ---
from api_manager import ApiManager
from database_manager import DatabaseManager
from settings_manager import SettingsManager, ModelManager
from conversation_manager import ConversationManager
from utils import crash_handler, setup_project_files, LogStream, FileExtractor
from worker_manager import ApiWorker
from ui_dialogs import SettingsDialog, SystemPromptDialog
from ui_main_window import MainWindowUI
from chat_backend import ChatBackend
from theme_manager import ThemeManager

sys.excepthook = crash_handler

def main_application():
    if sys.platform == "linux":
        if '--no-sandbox' not in sys.argv: sys.argv.append('--no-sandbox')
        if '--disable-gpu' not in sys.argv: sys.argv.append('--disable-gpu')

    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QMessageBox, QListWidgetItem, QMenu, QInputDialog,
            QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton
        )
        from PyQt6.QtCore import Qt, QThreadPool, pyqtSlot, QTimer, QEvent
        from PyQt6.QtGui import QFont
        from PyQt6.QtWebChannel import QWebChannel
        from PyQt6.QtWebEngineCore import QWebEngineProfile
        from dotenv import load_dotenv
        import markdown

        if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        
        ThemeManager.load_theme(app)

        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

        log_stream = LogStream()
        sys.stdout = log_stream 
        load_dotenv()

        class MainWindow(QMainWindow, MainWindowUI):
            def __init__(self, log_signal):
                super().__init__()
                self.setup_ui(self)
                
                # Managers
                self.settings_manager = SettingsManager()
                self.model_manager = ModelManager()
                self.db_manager = DatabaseManager()
                self.api_manager = ApiManager(timeout=self.settings_manager.get("api_timeout"))
                self.conv_manager = ConversationManager(self.db_manager)
                
                # State
                self.worker = None
                self.is_generating = False
                self.force_close = False
                self.is_web_ready = False
                self.model_metadata = {} 
                self.threadpool = QThreadPool()

                log_signal.connect(self._append_log)
                self._connect_signals()
                self._setup_web_channel()
                
                self._populate_history_list()
                self._populate_system_prompts()
                self._populate_models()
                self._apply_ui_settings()
                
                self.input_box.installEventFilter(self)
                self.threadpool.start(self._fetch_and_cache_models)

            def _connect_signals(self):
                self.new_chat_button.clicked.connect(self._new_chat)
                self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
                self.history_list.itemClicked.connect(self._load_conversation)
                self.manage_prompts_btn.clicked.connect(self._open_prompt_manager)
                
                self.temp_slider.valueChanged.connect(lambda val: self.temp_label.setText(f"{val * 0.05:.2f}"))
                
                self.chk_markdown.toggled.connect(self._refresh_chat_view)
                self.btn_settings.clicked.connect(self._open_settings)
                
                # Dual Copy Buttons
                self.btn_copy_chat.clicked.connect(self._copy_full_chat)
                self.btn_copy_context.clicked.connect(self._copy_full_context)
                
                self.attach_btn.clicked.connect(self._attach_file)
                self.send_button.clicked.connect(self.send_message)
                self.chat_view.loadFinished.connect(self._on_page_load_finished)
                self.model_combo.currentIndexChanged.connect(self._on_model_changed)

            def _setup_web_channel(self):
                self.chat_backend = ChatBackend(self)
                self.chat_backend.edit_requested.connect(self._handle_edit_request)
                self.chat_backend.regenerate_requested.connect(self._handle_regenerate_request)
                self.chat_backend.delete_requested.connect(self._handle_delete_request)
                self.channel = QWebChannel()
                self.channel.registerObject("backend", self.chat_backend)
                self.chat_view.page().setWebChannel(self.channel)

            def eventFilter(self, source, event):
                if source == self.input_box and event.type() == QEvent.Type.KeyPress:
                    if event.key() == Qt.Key.Key_Return and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                        self.send_message()
                        return True
                return super().eventFilter(source, event)

            def closeEvent(self, event):
                if self.force_close: event.accept(); return
                
                if self.is_generating:
                    if QMessageBox.question(self, "Exit", "Stop generation?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                        self.stop_generation(); event.accept()
                    else: event.ignore()
                else:
                    if QMessageBox.question(self, "Exit", "Exit application?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                        event.accept()
                    else:
                        event.ignore()

            @pyqtSlot(str)
            def _append_log(self, text):
                self.log_output.append(text.strip())
                self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

            @pyqtSlot()
            def _on_page_load_finished(self):
                self.is_web_ready = True
                self._sync_web_font()
                self._apply_ui_settings()

            def _sync_web_font(self):
                font = QApplication.font()
                family = font.family()
                family_safe = family.replace("'", "\\'")
                js = f"""
                document.documentElement.style.setProperty('--main-font', "'{family_safe}', sans-serif");
                """
                self.chat_view.page().runJavaScript(js)

            def _apply_ui_settings(self):
                font_size = self.settings_manager.get("font_size")
                font = QFont(); font.setPixelSize(font_size)
                self.input_box.setFont(font)
                self.history_list.setFont(font)
                if self.is_web_ready:
                    self.chat_view.page().runJavaScript(f"setFontSize('{font_size}px');")

            def _populate_models(self):
                self.model_combo.clear()
                for m in self.model_manager.get_all(): self.model_combo.addItem(m.get("name"), m.get("id"))
                self._on_model_changed()

            def _fetch_and_cache_models(self):
                models = self.api_manager.fetch_models()
                for m in models: self.model_metadata[m['id']] = m

            def _on_model_changed(self):
                mid = self.model_combo.currentData()
                if not mid: return
                meta = self.model_metadata.get(mid, {})
                supported = meta.get("supported_parameters", [])
                self.chk_reasoning.setEnabled("include_reasoning" in supported)
                if not self.chk_reasoning.isEnabled(): self.chk_reasoning.setChecked(False)
                self.chk_web_search.setChecked(mid.endswith(":online"))

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
                if self.is_generating: return
                self.conv_manager.new_conversation()
                self._update_staging_area()
                self.input_box.clear()
                self.history_list.clearSelection()
                self.chat_view.page().runJavaScript("clearChat();")
                self.sys_prompt_combo.setEnabled(True)
                self._update_token_count()

            @pyqtSlot()
            def send_message(self):
                if self.is_generating: self.stop_generation(); return
                user_text = self.input_box.toPlainText().strip()
                if not user_text and not self.conv_manager.staged_files: return
                if not self.api_manager.is_configured(): return QMessageBox.warning(self, "Error", "API Key missing.")

                sys_prompt = self.sys_prompt_combo.currentData()
                msgs = self.conv_manager.messages
                
                if msgs and msgs[0]['role'] == 'system':
                    if sys_prompt: 
                        self.conv_manager.update_message(0, sys_prompt)
                    else: 
                        self.conv_manager.delete_message_at(0)
                elif sys_prompt:
                    self.conv_manager.insert_system_message(sys_prompt)
                
                full_content = user_text + self.conv_manager.get_staged_content()
                self.conv_manager.clear_staged_files(); self._update_staging_area()

                current_temp = self.temp_slider.value() * 0.05
                self.conv_manager.add_message("user", full_content, None, current_temp)
                self._refresh_chat_view() 
                
                self._trigger_generation()
                self.input_box.clear()

            def _trigger_generation(self):
                self._set_ui_state_generating()
                self.chat_view.page().runJavaScript("showThinking();")
                
                model_id = self.model_combo.currentData()
                model_name = self.model_combo.currentText()
                temp = self.temp_slider.value() * 0.05
                
                if self.chk_web_search.isChecked() and not model_id.endswith(":online"): model_id += ":online"
                elif not self.chk_web_search.isChecked() and model_id.endswith(":online"): model_id = model_id.replace(":online", "")

                extra = {}
                if self.chk_reasoning.isChecked() and self.chk_reasoning.isEnabled(): extra["include_reasoning"] = True

                self.worker = ApiWorker(self.api_manager, model_id, self.conv_manager.get_messages_for_api(), temp, extra)
                self.worker.signals.first_token.connect(lambda: self.chat_view.page().runJavaScript(f"start_message({len(self.conv_manager.messages)}, 'assistant', '{model_name}');"))
                self.worker.signals.new_token.connect(self.chat_backend.stream_token)
                self.worker.signals.finished.connect(self.finalize_message)
                self.worker.signals.error.connect(self.handle_api_error)
                self.threadpool.start(self.worker)

            @pyqtSlot(dict)
            def finalize_message(self, response):
                try:
                    content = response['choices'][0]['message']['content']
                    current_temp = self.temp_slider.value() * 0.05
                    self.conv_manager.add_message("assistant", content, self.model_combo.currentData(), current_temp)
                    
                    html_c = markdown.markdown(content, extensions=['fenced_code', 'tables']) if self.chk_markdown.isChecked() else html.escape(content)
                    safe_html = html_c.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
                    self.chat_view.page().runJavaScript(f"finalize_message('{safe_html}');")
                    self._update_token_count()
                    
                    if self.history_list.count() != len(self.db_manager.get_all_conversations()):
                        self._populate_history_list()
                except Exception as e: self.handle_api_error(str(e))
                finally: self._set_ui_state_idle()

            @pyqtSlot(int, str)
            def _handle_edit_request(self, index, new_content):
                if self.is_generating: return
                self.conv_manager.update_message(index, new_content)
                self.conv_manager.prune_after(index)
                self._refresh_chat_view()
                self._trigger_generation()

            @pyqtSlot(int)
            def _handle_regenerate_request(self, index):
                if self.is_generating: return
                msg = self.conv_manager.messages[index]
                if msg['role'] == 'assistant':
                    self.conv_manager.prune_from(index)
                else:
                    self.conv_manager.prune_after(index)
                self._refresh_chat_view()
                self._trigger_generation()

            @pyqtSlot(int)
            def _handle_delete_request(self, index):
                if self.is_generating: return
                self.conv_manager.prune_from(index)
                self._refresh_chat_view()
                self._update_token_count()

            @pyqtSlot(str)
            def handle_api_error(self, msg):
                self.chat_view.page().runJavaScript("removeThinking();")
                self._set_ui_state_idle()
                QMessageBox.critical(self, "API Error", msg)

            def stop_generation(self):
                if self.worker:
                    try:
                        self.worker.signals.new_token.disconnect()
                        self.worker.signals.finished.disconnect()
                        self.worker.signals.error.disconnect()
                        self.worker.signals.first_token.disconnect()
                    except Exception: pass 
                    self.worker.stop()
                    self.chat_view.page().runJavaScript("removeThinking();")
                    self._set_ui_state_idle()

            def _set_ui_state_generating(self):
                self.is_generating = True
                self.send_button.setText("Stop")
                self.send_button.setProperty("danger", True)
                self.send_button.style().unpolish(self.send_button)
                self.send_button.style().polish(self.send_button)
                self.input_box.setEnabled(False)
                self.attach_btn.setEnabled(False)
                self.controls_dock.setEnabled(False)

            def _set_ui_state_idle(self):
                self.is_generating = False
                self.send_button.setText("Send Message")
                self.send_button.setProperty("danger", False)
                self.send_button.style().unpolish(self.send_button)
                self.send_button.style().polish(self.send_button)
                self.send_button.setEnabled(True)
                self.input_box.setEnabled(True)
                self.attach_btn.setEnabled(True)
                self.controls_dock.setEnabled(True)
                self.worker = None

            def _update_token_count(self):
                self.token_label.setText(f"Context: ~{self.conv_manager.get_token_count():,} tokens")

            def copy_message_to_clipboard(self, index):
                if 0 <= index < len(self.conv_manager.messages):
                    QApplication.clipboard().setText(FileExtractor.strip_attachments_for_copy(self.conv_manager.messages[index]["content"]))

            def _copy_full_chat(self):
                """Phase 5.1: Copies readable transcript (no raw file data)."""
                buffer = []
                if self.conv_manager.current_conversation_id:
                    buffer.append(f"=== CHAT TRANSCRIPT ===\n")
                for msg in self.conv_manager.messages:
                    role = "User" if msg['role'] == 'user' else f"Assistant ({msg.get('model_used', 'AI')})"
                    content, _ = FileExtractor.strip_attachments_for_ui(msg['content'])
                    buffer.append(f"[{role}]:\n{content.strip()}\n")
                QApplication.clipboard().setText("\n".join(buffer))
                self._append_log("[INFO] Chat transcript copied to clipboard.")

            def _copy_full_context(self):
                """Phase 5.1: Copies raw context including file payloads."""
                buffer = []
                if self.conv_manager.current_conversation_id:
                    buffer.append(f"=== RAW CONTEXT EXPORT ===\n")
                for msg in self.conv_manager.messages:
                    role = msg['role'].upper()
                    content = msg['content']
                    clean_content = re.sub(r'<div class="yaog-file-content" data-filename="[^"]+">', '', content).replace('</div>', '')
                    buffer.append(f"--- {role} ---")
                    buffer.append(clean_content.strip())
                    buffer.append("\n")
                QApplication.clipboard().setText("\n".join(buffer))
                self._append_log("[INFO] Raw context copied to clipboard.")

            @pyqtSlot(QListWidgetItem)
            def _load_conversation(self, item):
                if self.is_generating: return
                cid = item.data(Qt.ItemDataRole.UserRole)
                if cid == self.conv_manager.current_conversation_id: return
                self.conv_manager.load_conversation(cid)
                self._populate_system_prompts()
                msgs = self.conv_manager.messages
                if msgs and msgs[0]['role'] == 'system':
                    idx = self.sys_prompt_combo.findData(msgs[0]['content'])
                    self.sys_prompt_combo.setCurrentIndex(idx if idx >= 0 else 0)
                self._refresh_chat_view()
                self._update_token_count()

            def _refresh_chat_view(self):
                self.chat_view.page().runJavaScript("clearChat();")
                for i, m in enumerate(self.conv_manager.messages):
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
                    if self.conv_manager.current_conversation_id == item.data(Qt.ItemDataRole.UserRole): self._new_chat()

            def _attach_file(self):
                files, _ = QFileDialog.getOpenFileNames(self, "Attach", "", FileExtractor.get_supported_extensions())
                for f in files: self.conv_manager.add_staged_file(f)
                self._update_staging_area()

            def _update_staging_area(self):
                while self.staging_layout.count(): 
                    w = self.staging_layout.takeAt(0).widget()
                    if w: w.deleteLater()
                self.staging_container.setVisible(bool(self.conv_manager.staged_files))
                for f in self.conv_manager.staged_files:
                    chip = QFrame(); chip.setStyleSheet("background-color: #3c3c3c; border-radius: 5px;")
                    l = QHBoxLayout(chip); l.setContentsMargins(5,2,5,2)
                    l.addWidget(QLabel(Path(f).name, styleSheet="color: white;"))
                    btn = QPushButton("x", styleSheet="background-color: #d32f2f; color: white; border-radius: 10px;"); btn.setFixedSize(20,20)
                    btn.clicked.connect(lambda _, p=f: (self.conv_manager.remove_staged_file(p), self._update_staging_area()))
                    l.addWidget(btn); self.staging_layout.addWidget(chip)

        window = MainWindow(log_stream.log_signal)
        
        def signal_handler(sig, frame):
            print("\n[INFO] Ctrl+C detected. Exiting cleanly...")
            window.force_close = True
            if window.worker: window.worker.stop()
            QApplication.quit()
            
        signal.signal(signal.SIGINT, signal_handler)
        QTimer().start(100)

        window.showMaximized()
        sys.exit(app.exec())

    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup_project_files()
    main_application()
