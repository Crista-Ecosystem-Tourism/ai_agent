import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from openai import OpenAI

from app.core.llm.base import BaseLLMClient
from app.core.llm.exceptions import ConfigurationError


class DirectOpenAIClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4o-mini"):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY не найден")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def generate_response(
            self, 
            messages: List[Dict[str, str]], 
            full_response: bool = False,
            **kwargs
        ) -> str|Any:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        if full_response:
            return response
        return response.choices[0].message.content
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "OpenAI Direct",
            "model": self.model,
            "base_url": "https://api.openai.com/v1"
        }