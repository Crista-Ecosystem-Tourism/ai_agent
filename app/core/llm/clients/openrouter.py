import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from openai import OpenAI

from app.core.llm.base import BaseLLMClient
from app.core.llm.exceptions import ConfigurationError


class OpenRouterClient(BaseLLMClient):
    def __init__(self, model: str = "deepseek/deepseek-chat-v3-0324"):
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            raise ConfigurationError("OPENROUTER_API_KEY не найден")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model
        self.extra_headers = {
            "HTTP-Referer": "<YOUR_SITE_URL>",
            "X-Title": "<YOUR_SITE_NAME>",
        }
    
    def generate_response(
            self, 
            messages: List[Dict[str, str]], 
            full_response: bool = False,
            **kwargs
        ) -> str|Any:
        response = self.client.chat.completions.create(
            extra_headers=self.extra_headers,
            model=self.model,
            messages=messages,
            **kwargs
        )
        if full_response:
            return response
        return response.choices[0].message.content
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "OpenRouter",
            "model": self.model,
            "base_url": "https://openrouter.ai/api/v1"
        }
    