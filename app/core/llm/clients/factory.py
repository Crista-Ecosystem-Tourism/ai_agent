from typing import List, Dict

from app.core.llm.base import BaseLLMClient
from app.core.llm.clients import (
    OpenRouterClient,
    DirectOpenAIClient, 
    OllamaClient,
    LangChainOpenAIClient
)


class LLMClientFactory:
    @staticmethod
    def create_client(provider: str, **kwargs) -> BaseLLMClient:
        providers = {
            "openrouter": OpenRouterClient,
            "openai": DirectOpenAIClient,
            "ollama": OllamaClient,
            "langchain": LangChainOpenAIClient
        }
        
        if provider not in providers:
            raise ValueError(
                f"Провайдер {provider} не поддерживается. "
                f"Доступные: {list(providers.keys())}"
            )
        
        return providers[provider](**kwargs)
    
    @staticmethod
    def get_available_providers() -> List[Dict[str, str]]:
        return [
            {"name": "openrouter", "description": "OpenRouter (множество моделей)"},
            {"name": "openai", "description": "OpenAI Direct (прямой доступ)"},
            {"name": "ollama", "description": "Ollama (локальные модели)"},
            {"name": "langchain", "description": "OpenAI через LangChain"}
        ]