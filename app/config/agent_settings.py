import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()


LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openrouter"),
    "model": os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324"),
    "ollama_base_url": "http://localhost:11434/v1"
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

RAG_CONFIG = {
    "url": os.getenv("RAG_URL", "http://localhost:8001"),
    "search_endpoint": "/api/v1/search",
    "timeout": 30,
    "top_k": 8,
    "distance_threshold": 1.2
}

# Конфигурация сервиса маршрутизации (placesweb_backend)
ROUTE_CONFIG = {
    "url": os.getenv("ROUTE_URL", "http://localhost:8000"),
    "build_endpoint": "/api/v1/graph/build",
    "timeout": 60,
    "use_osrm_scoring": True,
    "base_radius_m": 500,
    "k_alternatives": 3,
    "min_points": 2,
    "default_weight": 1.0,
}
