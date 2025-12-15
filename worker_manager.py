# worker_manager.py for YaOG (yaog.py)
# Version: 3.4.0 (Phase 1: Smooth Streaming)
# Description: Manages the asynchronous API worker.
#              Implements "Micro-Chunking" to smooth out network bursts.
#
# Change Log (v3.4.0):
# - [UX] Added Python-side smoothing (chunk splitting + micro-sleeps) to prevent "blocky" text rendering.
# - [UX] Optimized emission rate to target ~60Hz updates.

import json
import sys
import time
import traceback
import httpx

# --- Local Imports ---
from api_manager import ApiManager

# --- PyQt6 Imports ---
try:
    from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot
except ImportError:
    print("[FATAL] PyQt6 is not installed. Please run: pip install PyQt6", file=sys.stderr)
    sys.exit(1)


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = pyqtSignal(dict)      # Emitted when stream completes (contains full text)
    error = pyqtSignal(str)          # Emitted on failure
    first_token = pyqtSignal()       # Emitted when the first valid chunk arrives
    new_token = pyqtSignal(str)      # Emitted for every text chunk received


class ApiWorker(QRunnable):
    """
    A worker thread for handling API requests asynchronously.
    """
    def __init__(self, api_manager: ApiManager, model_id: str, messages: list, temperature: float):
        super().__init__()
        self.api_manager = api_manager
        self.model_id = model_id
        self.messages = messages
        self.temperature = temperature
        self.signals = WorkerSignals()
        self._is_running = True  # Flag to allow cancellation (Phase 2 prep)

    def stop(self):
        """Stops the worker gracefully."""
        self._is_running = False

    @pyqtSlot()
    def run(self):
        """
        Consumes the SSE stream, emits tokens in real-time, and aggregates the result.
        """
        try:
            content_parts = []
            first_token_emitted = False
            
            # Using standard print, which will be redirected by the main app's LogStream
            print(f"[WORKER] Starting stream for model: {self.model_id}")

            for line in self.api_manager.get_completion_stream(self.model_id, self.messages, self.temperature):
                if not self._is_running:
                    print("[WORKER] Stream stopped by user.")
                    break

                if not line:
                    continue

                if line.startswith("data: "):
                    data_str = line[len("data: "):].strip()

                    if data_str == "[DONE]":
                        print("[WORKER] Stream finished ([DONE] received).")
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get('choices', [{}])[0].get('delta', {})
                        content_part = delta.get('content')

                        if content_part:
                            # 1. Emit first_token signal if this is the start
                            if not first_token_emitted:
                                self.signals.first_token.emit()
                                first_token_emitted = True

                            # 2. Smooth Streaming Logic
                            # Instead of emitting the whole 'content_part' (which might be a large buffered chunk),
                            # we split it into tiny pieces and sleep briefly. This paces the UI updates.
                            
                            # Chunk size: 3 chars. 
                            # Sleep: 0.01s (10ms).
                            # Rate: ~100 emits/sec max. ~300 chars/sec.
                            # This is fast enough to feel snappy, but slow enough to look smooth.
                            
                            chunk_size = 3
                            for i in range(0, len(content_part), chunk_size):
                                if not self._is_running: break
                                
                                sub_chunk = content_part[i:i+chunk_size]
                                self.signals.new_token.emit(sub_chunk)
                                
                                # Force a tiny pause to let the Qt Event Loop process the signal
                                # and repaint the UI, preventing "batching".
                                time.sleep(0.01)
                            
                            # 3. Store it for the final aggregation
                            content_parts.append(content_part)

                    except json.JSONDecodeError:
                        print(f"[WORKER WARNING] Could not decode JSON chunk: {data_str}")
                        continue

            full_response_content = "".join(content_parts)

            # Construct final result for DB storage and Markdown rendering
            final_result = {
                "choices": [{"message": {"content": full_response_content}}]
            }
            
            if self._is_running:
                self.signals.finished.emit(final_result)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"\033[93m[API WARNING] Rate Limit Exceeded (429).\033[0m")
                friendly_error = (
                    "<b>Rate Limit Exceeded (429)</b><br>"
                    "The free model is currently busy or you have hit a request limit.<br>"
                    "Please wait a moment or try selecting a different model."
                )
                self.signals.error.emit(friendly_error)
            else:
                error_message = (
                    f"<b>API HTTP Error</b><br>"
                    f"Status Code: {e.response.status_code}<br>"
                    f"Details: {e.response.text[:200]}"
                )
                self.signals.error.emit(error_message)

        except Exception as e:
            error_message = (
                f"<b>API Call Failed</b><br>"
                f"Model: {self.model_id}<br>"
                f"Error Type: {type(e).__name__}<br>"
                f"Details: {str(e)}<br><br>"
                "Please check your network, API key, and the console logs for details."
            )
            print("\n\033[91m--- [API WORKER EXCEPTION] ---\033[0m", file=sys.__stderr__)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.__stderr__)
            self.signals.error.emit(error_message)
