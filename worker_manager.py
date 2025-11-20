# worker_manager.py for OR-Client (yaog.py)
# Version: 1.2
# Description: A dedicated module for managing the asynchronous API worker.
#              Includes robust handling for HTTP 429 (Rate Limit) errors.
#
# Change Log (v1.2):
# - [UX] Added 'first_token' signal to support "Thinking..." -> "Generating..." UI feedback.

import json
import sys
import traceback
import httpx  # Required for exception handling

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
    Supported signals are:
    - finished: Emits a dict when the process is complete.
    - error: Emits a string if an error occurs.
    - first_token: Emits when the first valid data chunk is received.
    """
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    first_token = pyqtSignal()


class ApiWorker(QRunnable):
    """
    A worker thread for handling API requests asynchronously.
    It uses an instance of ApiManager to perform the actual request and
    emits signals to communicate the result back to the main thread.
    """
    def __init__(self, api_manager: ApiManager, model_id: str, messages: list, temperature: float):
        """
        Initializes the ApiWorker.

        Args:
            api_manager (ApiManager): An instance of the ApiManager.
            model_id (str): The ID of the model to use.
            messages (list): The list of message dictionaries for the conversation.
            temperature (float): The temperature for the generation.
        """
        super().__init__()
        self.api_manager = api_manager
        self.model_id = model_id
        self.messages = messages
        self.temperature = temperature
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """
        The main logic of the worker thread. It consumes the SSE stream from the
        API, aggregates the content, and emits the final result or an error.
        """
        try:
            content_parts = []
            first_token_emitted = False
            
            # Using standard print, which will be redirected by the main app's LogStream
            print("[WORKER] Worker started, consuming response stream line-by-line...")

            for line in self.api_manager.get_completion_stream(self.model_id, self.messages, self.temperature):
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
                            # Emit signal on the very first token received
                            if not first_token_emitted:
                                self.signals.first_token.emit()
                                first_token_emitted = True
                            
                            content_parts.append(content_part)

                    except json.JSONDecodeError:
                        print(f"[WORKER WARNING] Could not decode a JSON chunk from the stream: {data_str}")
                        continue

            full_response_content = "".join(content_parts)

            # Construct a final result dictionary that mimics the non-streaming API response structure.
            final_result = {
                "choices": [{"message": {"content": full_response_content}}]
            }
            # Emit the 'finished' signal with the complete result.
            self.signals.finished.emit(final_result)

        except httpx.HTTPStatusError as e:
            # Specific handling for HTTP errors (like 429 Rate Limit)
            if e.response.status_code == 429:
                print(f"\033[93m[API WARNING] Rate Limit Exceeded (429).\033[0m")
                friendly_error = (
                    "<b>Rate Limit Exceeded (429)</b><br>"
                    "The free model is currently busy or you have hit a request limit.<br>"
                    "Please wait a moment or try selecting a different model."
                )
                self.signals.error.emit(friendly_error)
            else:
                # Handle other HTTP errors
                error_message = (
                    f"<b>API HTTP Error</b><br>"
                    f"Status Code: {e.response.status_code}<br>"
                    f"Details: {e.response.text[:200]}"
                )
                self.signals.error.emit(error_message)

        except Exception as e:
            # Format a detailed error message for the GUI for unexpected crashes
            error_message = (
                f"<b>API Call Failed</b><br>"
                f"Model: {self.model_id}<br>"
                f"Error Type: {type(e).__name__}<br>"
                f"Details: {str(e)}<br><br>"
                "Please check your network, API key, and the console logs for details."
            )
            # Print the full traceback to the console (which is redirected to the log view).
            print("\n\033[91m--- [API WORKER EXCEPTION] ---\033[0m", file=sys.__stderr__)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.__stderr__)
            print("\033[91m------------------------------\033[0m\n", file=sys.__stderr__)
            # Emit the 'error' signal.
            self.signals.error.emit(error_message)
