# api_manager.py for OR-Client (yaog.py)
# Version: 1.7
# Description: A dedicated module to handle all interactions with the OpenRouter API.

import os
import httpx

# The base URL for the OpenRouter API.
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class ApiManager:
    """
    Handles all communication with the OpenRouter API.
    This class is designed to be self-contained and does not depend on the GUI.
    """
    # Timeout for API requests in seconds. Can be adjusted.
    REQUEST_TIMEOUT = 120.0

    def __init__(self):
        """
        Initializes the ApiManager, loads the API key, and sets up the
        httpx client with necessary headers.
        """
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Recommended headers for OpenRouter API calls.
        # See: https://openrouter.ai/docs#headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/or-client", # TODO: Replace with your actual repo URL
            "X-Title": "OR-Client"
        }
        
        # The httpx client is used for making asynchronous-friendly API calls.
        self.client = httpx.Client(
            headers=self.headers,
            timeout=self.REQUEST_TIMEOUT
        )
        if self.is_configured():
            # Using standard print, which will be redirected by the main app's LogStream
            print(f"[INFO] ApiManager initialized. Key: {self.api_key[:8]}...")
        else:
            print(f"[WARNING] API Key not found or not configured in .env file.")

    def is_configured(self):
        """
        Checks if the API key is present and is not the default placeholder value.
        
        Returns:
            bool: True if the API key is configured, False otherwise.
        """
        return self.api_key and self.api_key != "YOUR_API_KEY_HERE"

    def get_completion_stream(self, model_id, messages, temperature):
        """
        Initiates a streaming request to the OpenRouter API. This method is a
        generator, yielding lines of the response as they arrive, which is
        suitable for processing Server-Sent Events (SSE).

        Args:
            model_id (str): The identifier of the model to use (e.g., "mistralai/mistral-7b-instruct:free").
            messages (list): A list of message dictionaries, e.g., [{"role": "user", "content": "Hello"}].
            temperature (float): The temperature setting for the model.

        Yields:
            str: A line from the HTTP response body.

        Raises:
            ValueError: If the API key is not configured.
            httpx.RequestError: If a network-level error occurs.
            Exception: For other unexpected errors during the API call.
        """
        if not self.is_configured():
            raise ValueError("API key is not configured.")
        
        # Ensure message format is clean before sending.
        clean_messages = [{"role": str(m["role"]), "content": str(m["content"])} for m in messages]
        
        # The payload for the API request. "stream": True is crucial.
        payload = {
            "model": model_id,
            "messages": clean_messages,
            "temperature": temperature,
            "stream": True
        }

        print(f"[INFO] Preparing to send request to model: {model_id}")
        print(f" -> Target URL: {OPENROUTER_API_URL}")
        print(f" -> Timeout set to: {self.client.timeout.read} seconds")
        print(f" -> History contains: {len(clean_messages)} messages")
        
        try:
            # `with client.stream(...)` ensures the connection is properly handled.
            with self.client.stream("POST", OPENROUTER_API_URL, json=payload) as response:
                print(f" <- Stream opened. Status: {response.status_code}")
                # Raise an exception for bad status codes (4xx or 5xx).
                response.raise_for_status()
                # `iter_lines` is the correct way to process SSE streams.
                for line in response.iter_lines():
                    yield line
        except httpx.RequestError as exc:
            print(f"[ERROR] Network request to OpenRouter failed.")
            print(f" -> Error Type: {type(exc).__name__}")
            print(f" -> Request URL: {exc.request.url}")
            raise exc
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred during the API call: {e}")
            raise e
