# worker_manager.py for YaOG (yaog.py)
# Version: 3.5.3 (Phase 3: Model Management)
# Description: Manages the asynchronous API worker.

import json
import sys
import time
import traceback
import httpx

try:
    from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot
except ImportError:
    print("[FATAL] PyQt6 is not installed.", file=sys.stderr)
    sys.exit(1)

# --- Local Imports ---
from api_manager import ApiManager

class WorkerSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    first_token = pyqtSignal()
    new_token = pyqtSignal(str)

class ApiWorker(QRunnable):
    def __init__(self, api_manager: ApiManager, model_id: str, messages: list, temperature: float, extra_params: dict = None):
        super().__init__()
        self.api_manager = api_manager
        self.model_id = model_id
        self.messages = messages
        self.temperature = temperature
        self.extra_params = extra_params or {}
        self.signals = WorkerSignals()
        self._is_running = True

    def stop(self):
        print("[WORKER] Stop requested.")
        self._is_running = False

    @pyqtSlot()
    def run(self):
        try:
            content_parts = []
            first_token_emitted = False
            
            print(f"[WORKER] Starting stream for model: {self.model_id}")

            # Pass extra_params to the API manager
            stream = self.api_manager.get_completion_stream(
                self.model_id, self.messages, self.temperature, self.extra_params
            )

            for line in stream:
                if not self._is_running:
                    print("[WORKER] Stream stopped by user.")
                    break

                if not line: continue
                if line.startswith("data: "):
                    data_str = line[len("data: "):].strip()
                    if data_str == "[DONE]": break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get('choices', [{}])[0].get('delta', {})
                        content_part = delta.get('content')

                        if content_part:
                            if not first_token_emitted:
                                self.signals.first_token.emit()
                                first_token_emitted = True

                            # Micro-Chunking
                            chunk_size = 3
                            for i in range(0, len(content_part), chunk_size):
                                if not self._is_running: break
                                sub_chunk = content_part[i:i+chunk_size]
                                self.signals.new_token.emit(sub_chunk)
                                time.sleep(0.01)
                            
                            content_parts.append(content_part)

                    except json.JSONDecodeError: continue

            full_response_content = "".join(content_parts)
            final_result = {"choices": [{"message": {"content": full_response_content}}]}
            self.signals.finished.emit(final_result)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self.signals.error.emit("<b>Rate Limit Exceeded (429)</b><br>Model busy or limit reached.")
            else:
                self.signals.error.emit(f"<b>API HTTP Error</b><br>Status: {e.response.status_code}")

        except Exception as e:
            if not self._is_running: return
            print("\n\033[91m--- [API WORKER EXCEPTION] ---\033[0m", file=sys.__stderr__)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.__stderr__)
            self.signals.error.emit(f"<b>API Call Failed</b><br>{str(e)}")
