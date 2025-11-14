from typing import List, Dict, Any
from openai import OpenAI

from app.core.llm.base import BaseLLMClient
from app.core.llm.exceptions import ConnectionError


class OllamaClient(BaseLLMClient):
    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434/v1"):
        self.client = OpenAI(
            base_url=base_url,
            api_key="ollama",
        )
        self.model = model
        self.base_url = base_url
    
    def generate_response(
            self, 
            messages: List[Dict[str, str]], 
            full_response: bool = False,
            **kwargs
        ) -> str|Any:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            if full_response:
                return response
            return response.choices[0].message.content
        except Exception as e:
            raise ConnectionError(f"Не удалось подключиться к Ollama по {self.base_url}. Убедитесь, что Ollama запущен.")
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "Ollama",
            "model": self.model,
            "base_url": self.base_url
        }