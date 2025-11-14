import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()


LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openrouter"),
    "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o"),
    "ollama_base_url": "http://localhost:11434/v1"
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

RAG_CONFIG = {
    "url": os.getenv("RAG_URL", "http://localhost:8000"),
    "search_endpoint": "/api/v1/search",
    "timeout": 30,
    "top_k": 4,
    "distance_threshold": 1.2
}
