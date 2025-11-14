import os
from dotenv import load_dotenv
from typing import List, Dict, Any

from app.core.llm.base import BaseLLMClient
from app.core.llm.exceptions import ConfigurationError


class LangChainOpenAIClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4o-mini"):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Для использования LangChain установите: pip install langchain-openai")
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY не найден")
        
        self.llm = ChatOpenAI(model=model, api_key=api_key)
        self.model = model
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            from langchain.messages import HumanMessage, SystemMessage
        except ImportError:
            raise ImportError("Для использования LangChain установите: pip install langchain")
        
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            else:
                langchain_messages.append(HumanMessage(content=msg["content"]))
        
        response = self.llm.invoke(langchain_messages, **kwargs)
        return response.content
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "OpenAI via LangChain",
            "model": self.model,
            "base_url": "https://api.openai.com/v1"
        }
    