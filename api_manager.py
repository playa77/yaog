# Script Version: 3.5.5 | Last Updated: 2025-12-17
# Description: Handles OpenRouter API interactions.

import os
import httpx

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

class ApiManager:
    def __init__(self, timeout=360.0):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "YaOG"
        }
        self.client = httpx.Client(headers=self.headers, timeout=timeout)

    def is_configured(self):
        return self.api_key and self.api_key != "YOUR_API_KEY_HERE"

    def fetch_models(self):
        if not self.is_configured(): return []
        try:
            resp = self.client.get(OPENROUTER_MODELS_URL)
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            print(f"[ERROR] Failed to fetch models: {e}")
            return []

    def get_completion_stream(self, model_id, messages, temperature, extra_params=None):
        if not self.is_configured():
            raise ValueError("API key is not configured.")
        
        payload = {
            "model": model_id,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": temperature,
            "stream": True
        }
        if extra_params:
            payload.update(extra_params)

        try:
            with self.client.stream("POST", OPENROUTER_API_URL, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    yield line
        except Exception as e:
            raise e
