import os
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import httpx

from app.core.memory.sqlalchemy_store.store import SqlAlchemyHistoryStore
from app.core.memory.services import ConversationHistoryService, HistoryPolicy
from app.core.memory.config import HistoryConfig
from app.services.chat_session import ChatSessionService
from app.services.user import UserService
from app.services.saved_route import SavedRouteService
from app.services.game_progress import GameProgressService

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from app.core.agents.preferences import PreferencesAgent
from app.core.agents.search import SearchAgent
from app.core.services.processor import MessageProcessor
from app.db.dsn import get_database_url


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_http_client: httpx.AsyncClient | None = None

_history_service: ConversationHistoryService | None = None
_chat_session_service: ChatSessionService | None = None
_user_service: UserService | None = None
_saved_route_service: SavedRouteService | None = None
_game_progress_service: GameProgressService | None = None

_llm_model: OpenAIChatModel | None = None
_preferences_agent: PreferencesAgent | None = None
_search_agent: SearchAgent | None = None
_message_processor: MessageProcessor | None = None
_ai_available = False
_ai_unavailable_reason = "not started"

_PLACEHOLDER_API_KEYS = {
    "local-placeholder",
    "placeholder",
    "your-api-key",
    "changeme",
}


def _configured_openrouter_key() -> str | None:
    value = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not value or value.lower() in _PLACEHOLDER_API_KEYS:
        return None
    return value


def get_runtime_status() -> dict[str, object]:
    """Expose process readiness without leaking provider credentials."""
    core_ready = all((
        _engine is not None,
        _session_factory is not None,
        _http_client is not None,
        _history_service is not None,
        _chat_session_service is not None,
        _user_service is not None,
        _saved_route_service is not None,
        _game_progress_service is not None,
    ))
    return {
        "core_ready": core_ready,
        "ai": {
            "available": _ai_available,
            "reason": None if _ai_available else _ai_unavailable_reason,
        },
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _session_factory, _http_client
    global _history_service, _chat_session_service, _user_service, _saved_route_service, _game_progress_service
    global _llm_model, _preferences_agent, _search_agent, _message_processor
    global _ai_available, _ai_unavailable_reason

    dsn = get_database_url()
    _engine = create_async_engine(dsn, pool_pre_ping=True, future=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    _http_client = httpx.AsyncClient(timeout=30.0)

    store = SqlAlchemyHistoryStore(_session_factory, cfg=HistoryConfig())

    _history_service = ConversationHistoryService(store, HistoryPolicy(
        max_messages=int(os.getenv("HISTORY_MAX_MESSAGES", "12")),
        ttl=timedelta(hours=int(os.getenv("HISTORY_TTL_HOURS", "24")))
    ))

    _chat_session_service = ChatSessionService(_session_factory)
    _user_service = UserService(_session_factory)
    _saved_route_service = SavedRouteService(_session_factory)
    _game_progress_service = GameProgressService(_session_factory)

    api_key = _configured_openrouter_key()
    if api_key is None:
        _ai_available = False
        _ai_unavailable_reason = "OpenRouter API key is not configured"
    else:
        try:
            _llm_model = OpenAIChatModel(
                # Дефолт: DeepSeek V3 (не OpenAI) — для регионов вроде HK OpenRouter часто блокирует openai/* по ToS/geo.
                os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324"),
                provider=OpenRouterProvider(api_key=api_key),
            )
            _preferences_agent = PreferencesAgent(_llm_model)
            _search_agent = SearchAgent(model=_llm_model)
            _message_processor = MessageProcessor(
                preferences_agent=_preferences_agent,
                model=_llm_model,
            )
            _ai_available = True
            _ai_unavailable_reason = ""
        except Exception:  # noqa: BLE001
            # Auth, saved routes and suitcase must stay usable when the optional
            # AI integration cannot initialize. Detailed diagnostics stay in logs.
            _ai_available = False
            _ai_unavailable_reason = "AI provider initialization failed"

    try:
        yield
    finally:
        if _http_client:
            await _http_client.aclose()
        if _engine:
            await _engine.dispose()
        _engine = None
        _session_factory = None
        _http_client = None
        _history_service = None
        _chat_session_service = None
        _user_service = None
        _saved_route_service = None
        _game_progress_service = None
        _llm_model = None
        _preferences_agent = None
        _search_agent = None
        _message_processor = None
        _ai_available = False
        _ai_unavailable_reason = "not started"


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return _session_factory

async def get_db():
    factory = get_session_factory()
    async with factory() as s:
        yield s

def get_http_client() -> httpx.AsyncClient:
    return _http_client

def get_history_service() -> ConversationHistoryService:
    return _history_service

def get_chat_session_service() -> ChatSessionService:
    return _chat_session_service

def get_user_service() -> UserService:
    return _user_service

def get_saved_route_service() -> SavedRouteService:
    return _saved_route_service

def get_game_progress_service() -> GameProgressService:
    return _game_progress_service

def get_message_processor() -> MessageProcessor:
    if _message_processor is None:
        raise HTTPException(
            status_code=503,
            detail="AI-маршруты временно недоступны. Остальные функции продолжают работать.",
        )
    return _message_processor
