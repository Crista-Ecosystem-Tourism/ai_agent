import os
import json
import httpx
import logging

from typing import Optional, Union
from fastapi import APIRouter, Query, Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND
from pydantic_ai.messages import ModelMessagesTypeAdapter

from app.core.memory.services import ConversationHistoryService
from app.core.models import TravelDeps, UserPreferences
from app.services.chat_session import ChatSessionService
from app.security.deps import get_current_user, get_optional_user

from app.api.schemas import (
    SessionCreate, SessionOut, SessionOutAnon, SessionListItem,
    MessageIn, MessageOut,
    HistoryIn, HistoryOut,
    AttachIn
)
from app.dependencies import (
    get_history_service,
    get_chat_session_service,
    get_message_processor,
    get_http_client,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(
    user=Depends(get_current_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    sessions = await chat_srv.list_for_user(user["sub"])
    return [SessionListItem(**s) for s in sessions]


@router.post("/sessions", response_model=Union[SessionOut, SessionOutAnon])
async def create_session(
    payload: SessionCreate,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    if payload.anonymous:
        session_id, secret = await chat_srv.create_anon(payload.title)
        return SessionOutAnon(id=session_id, title=payload.title, secret=secret)
    else:
        user_id = user["sub"] if user else None
        session_id = await chat_srv.create(user_id=user_id, title=payload.title)
        return SessionOut(id=session_id, title=payload.title)

@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    user=Depends(get_current_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    row = await chat_srv.get_owned(session_id, user["sub"])
    if not row:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionOut(id=row[0], title=row[1])

@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    payload: SessionCreate,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    if payload.title:
        await chat_srv.update_title(session_id, payload.title)
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user=Depends(get_current_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
    history: ConversationHistoryService = Depends(get_history_service),
):
    ok = await chat_srv.delete_owned(session_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    await history.reset(session_id)
    return {"ok": True}


@router.get("/sessions/{session_id}/history", response_model=HistoryOut)
async def get_history(
    session_id: str,
    view: str = "short",
    session_secret: Optional[str] = Query(None, description="Secret для анонимной сессии"),
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
    history: ConversationHistoryService = Depends(get_history_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        ok = await chat_srv.verify_anonymous_access(session_id, session_secret)
        if not ok:
            raise HTTPException(status_code=403, detail="Forbidden (anon secret invalid)")

    msgs = await (history.load_full(session_id) if view == "full" else history.load_for_context(session_id))
    raw = ModelMessagesTypeAdapter.dump_json(msgs).decode("utf-8")
    return HistoryOut(session_id=session_id, messages=json.loads(raw))

@router.post("/sessions/{session_id}/attach")
async def attach_session(
    session_id: str,
    session_secret: AttachIn,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    if not user:
        raise HTTPException(status_code=401, detail="Login required to attach")
    ok = await chat_srv.verify_anonymous_access(session_id, session_secret)
    if not ok:
        raise HTTPException(status_code=403, detail="Forbidden (anon secret invalid)")
    await chat_srv.attach_owner(session_id, user["sub"])
    return {"ok": True}


@router.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def send_message(
    session_id: str,
    data: MessageIn,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
    history_service: ConversationHistoryService = Depends(get_history_service),
    processor = Depends(get_message_processor),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        ok = await chat_srv.verify_anonymous_access(session_id, data.session_secret)
        if not ok:
            raise HTTPException(status_code=403, detail="Forbidden (anon secret invalid)")

    history = await history_service.load_for_context(session_id)

    saved_prefs = await chat_srv.load_preferences(session_id)
    deps = TravelDeps(
        rag_service_url=os.getenv("RAG_URL", "http://localhost:8001/api/v1"),
        http_client=http_client,
        user_preferences=saved_prefs,
    )

    try:
        result = await processor.process_message(
            data.message,
            deps,
            history,
            generate_search_response=data.generate_text_response
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")

    await chat_srv.save_preferences(session_id, deps.user_preferences)

    from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
    from datetime import datetime, timezone

    user_message = ModelRequest(
        parts=[UserPromptPart(content=data.message)],
        kind="request"
    )

    if isinstance(result.response, str):
        text = result.response
        sr = result.search_results
    else:
        sr = result.response  # List[SearchResult] from non-text path
        count = sum(r.count for r in sr)
        text = f"Найдено {count} мест по вашему запросу."

    assistant_message = ModelResponse(
        parts=[TextPart(content=text)],
        kind="response",
        timestamp=datetime.now(timezone.utc)
    )

    await history_service.append_messages(session_id, [user_message, assistant_message])

    await chat_srv.touch(session_id)

    return MessageOut(
        message=text,
        search_results=[r if hasattr(r, 'model_dump') else r for r in sr] if sr else None,
        conversation_complete=result.is_complete,
        has_search_results=result.has_results,
        preferences=deps.user_preferences.model_dump(exclude_none=True),
        route_geojson=result.route_geojson,
        route_metadata=result.route_metadata,
        itinerary=result.itinerary.model_dump() if result.itinerary else None,
        suggested_replies=result.suggested_replies,
        follow_up_questions=result.follow_up_questions,
    )
