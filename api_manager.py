# api_manager.py for YaOG (yaog.py)
# Version: 1.9
# Description: A dedicated module to handle all interactions with the OpenRouter API.
#
# Change Log (v1.9):
# - [Config] Updated default timeout to 360.0s.
#
# Change Log (v1.8):
# - [Settings] Added set_timeout() to dynamically update request timeout.
# - [Settings] __init__ now accepts an optional timeout parameter.

import os
import httpx

# The base URL for the OpenRouter API.
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class ApiManager:
    """
    Handles all communication with the OpenRouter API.
    This class is designed to be self-contained and does not depend on the GUI.
    """
    
    def __init__(self, timeout=360.0):
        """
        Initializes the ApiManager.

        Args:
            timeout (float): The request timeout in seconds. Defaults to 360.0.
        """
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Recommended headers for OpenRouter API calls.
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/or-client", 
            "X-Title": "OR-Client"
        }
        
        # The httpx client is used for making asynchronous-friendly API calls.
        self.client = httpx.Client(
            headers=self.headers,
            timeout=timeout
        )
        
        if self.is_configured():
            print(f"[INFO] ApiManager initialized. Key: {self.api_key[:8]}... Timeout: {timeout}s")
        else:
            print(f"[WARNING] API Key not found or not configured in .env file.")

    def is_configured(self):
        """
        Checks if the API key is present and is not the default placeholder value.
        """
        return self.api_key and self.api_key != "YOUR_API_KEY_HERE"

    def set_timeout(self, timeout_seconds: float):
        """
        Updates the timeout for the HTTP client.
        
        Args:
            timeout_seconds (float): The new timeout in seconds.
        """
        print(f"[INFO] Updating API timeout to {timeout_seconds} seconds.")
        # httpx.Client.timeout can be updated directly in newer versions,
        # or we can recreate the client if needed. Updating the property is preferred.
        self.client.timeout = httpx.Timeout(timeout_seconds)

    def get_completion_stream(self, model_id, messages, temperature):
        """
        Initiates a streaming request to the OpenRouter API.
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
        
        try:
            # `with client.stream(...)` ensures the connection is properly handled.
            with self.client.stream("POST", OPENROUTER_API_URL, json=payload) as response:
                print(f" <- Stream opened. Status: {response.status_code}")
                response.raise_for_status()
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
