import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from app.services.chat_session import ChatSessionService
from app.services.saved_route import SavedRouteService
from app.security.deps import get_current_user, get_optional_user

from app.api.schemas import (
    PlaceRatingsIn, PlaceRatingsOut,
    PlacesSnapshotIn, PlacesSnapshotOut,
    GraphIn, GraphOut,
    SavedRouteCreate, SavedRouteOut, SavedRouteListItem,
)
from app.dependencies import (
    get_chat_session_service,
    get_saved_route_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["travel-data"])


# --- Place ratings ---

@router.put("/chat/sessions/{session_id}/place-ratings")
async def save_place_ratings(
    session_id: str,
    payload: PlaceRatingsIn,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    ratings_dict = {k: v.model_dump() for k, v in payload.ratings.items()}
    await chat_srv.save_place_ratings(session_id, ratings_dict)
    return {"ok": True}


@router.get("/chat/sessions/{session_id}/place-ratings", response_model=PlaceRatingsOut)
async def load_place_ratings(
    session_id: str,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    ratings = await chat_srv.load_place_ratings(session_id)
    return PlaceRatingsOut(session_id=session_id, ratings=ratings)


# --- Places snapshot ---

@router.put("/chat/sessions/{session_id}/places")
async def save_places_snapshot(
    session_id: str,
    payload: PlacesSnapshotIn,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    await chat_srv.save_places_snapshot(session_id, payload.places)
    return {"ok": True}


@router.get("/chat/sessions/{session_id}/places", response_model=PlacesSnapshotOut)
async def load_places_snapshot(
    session_id: str,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    places = await chat_srv.load_places_snapshot(session_id)
    return PlacesSnapshotOut(session_id=session_id, places=places)


# --- Graph GeoJSON ---

@router.put("/chat/sessions/{session_id}/graph")
async def save_graph(
    session_id: str,
    payload: GraphIn,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    await chat_srv.save_graph_geojson(session_id, payload.geojson)
    return {"ok": True}


@router.get("/chat/sessions/{session_id}/graph", response_model=GraphOut)
async def load_graph(
    session_id: str,
    user=Depends(get_optional_user),
    chat_srv: ChatSessionService = Depends(get_chat_session_service),
):
    owner = await chat_srv.get_owner(session_id)
    if owner:
        if not user or user["sub"] != owner:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    geojson = await chat_srv.load_graph_geojson(session_id)
    return GraphOut(session_id=session_id, geojson=geojson)


# --- Saved routes ---

@router.post("/routes", response_model=SavedRouteOut)
async def create_route(
    payload: SavedRouteCreate,
    user=Depends(get_current_user),
    route_srv: SavedRouteService = Depends(get_saved_route_service),
):
    route_id = await route_srv.create(user["sub"], payload.model_dump())
    route = await route_srv.get_owned(route_id, user["sub"])
    return SavedRouteOut(**route)


@router.get("/routes", response_model=list[SavedRouteListItem])
async def list_routes(
    user=Depends(get_current_user),
    route_srv: SavedRouteService = Depends(get_saved_route_service),
):
    routes = await route_srv.list_for_user(user["sub"])
    return [SavedRouteListItem(**r) for r in routes]


@router.get("/routes/{route_id}", response_model=SavedRouteOut)
async def get_route(
    route_id: str,
    user=Depends(get_current_user),
    route_srv: SavedRouteService = Depends(get_saved_route_service),
):
    route = await route_srv.get_owned(route_id, user["sub"])
    if not route:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Route not found")
    return SavedRouteOut(**route)


@router.delete("/routes/{route_id}")
async def delete_route(
    route_id: str,
    user=Depends(get_current_user),
    route_srv: SavedRouteService = Depends(get_saved_route_service),
):
    ok = await route_srv.delete_owned(route_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Route not found")
    return {"ok": True}
