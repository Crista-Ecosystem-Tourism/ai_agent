import os
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import httpx

from app.core.memory.sqlalchemy_store.store import SqlAlchemyHistoryStore
from app.core.memory.services import ConversationHistoryService, HistoryPolicy
from app.core.memory.config import HistoryConfig
from app.services.chat_session import ChatSessionService
from app.services.user import UserService
from app.services.saved_route import SavedRouteService
from app.services.suitcase import SuitcaseService

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
_suitcase_service: SuitcaseService | None = None

_llm_model: OpenAIChatModel | None = None
_preferences_agent: PreferencesAgent | None = None
_search_agent: SearchAgent | None = None
_message_processor: MessageProcessor | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _session_factory, _http_client
    global _history_service, _chat_session_service, _user_service, _saved_route_service, _suitcase_service
    global _llm_model, _preferences_agent, _search_agent, _message_processor

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
    _suitcase_service = SuitcaseService(_session_factory)

    _llm_model = OpenAIChatModel(
        # Дефолт: DeepSeek V3 (не OpenAI) — для регионов вроде HK OpenRouter часто блокирует openai/* по ToS/geo.
        os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324"),
        provider=OpenRouterProvider(api_key=os.getenv("OPENROUTER_API_KEY"))
    )
    _preferences_agent = PreferencesAgent(_llm_model)
    _search_agent = SearchAgent(model=_llm_model)
    _message_processor = MessageProcessor(
        preferences_agent=_preferences_agent,
        model=_llm_model
    )

    try:
        yield
    finally:
        if _http_client:
            await _http_client.aclose()
        if _engine:
            await _engine.dispose()


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

def get_suitcase_service() -> SuitcaseService:
    return _suitcase_service

def get_message_processor() -> MessageProcessor:
    return _message_processor
