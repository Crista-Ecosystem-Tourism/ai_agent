from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    title: Optional[str] = None
    anonymous: bool = Field(default=False, description="Создать анонимную сессию с секретом")

class SessionOut(BaseModel):
    id: str
    title: Optional[str] = None

class SessionOutAnon(SessionOut):
    secret: str

class SessionListItem(BaseModel):
    id: str
    title: Optional[str] = None
    updated_at: Optional[str] = None

class MessageIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    generate_text_response: bool = False
    session_secret: Optional[str] = Field(None)

class HistoryIn(BaseModel):
    session_secret: Optional[str] = Field(None)

class AttachIn(BaseModel):
    session_secret: str

class Place(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    subtype: Optional[str] = None
    activities: Optional[str] = None
    postalcode: Optional[str] = None
    page_content: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")

class SearchResult(BaseModel):
    query: str
    places: List[Place]
    count: int

class MessageOut(BaseModel):
    message: str = Field(...)
    search_results: Optional[List[SearchResult]] = Field(None)
    conversation_complete: bool = Field(default=False)
    has_search_results: bool = Field(default=False)
    preferences: Optional[dict] = Field(None)
    route_geojson: Optional[dict] = Field(
        None,
        description="GeoJSON маршрута от placesweb_backend (FeatureCollection)",
    )
    route_metadata: Optional[dict] = Field(
        None,
        description="Метаданные маршрута: graph_id, время сборки, кол-во узлов/рёбер",
    )
    itinerary: Optional[dict] = Field(
        None,
        description="Structured itinerary (days/slots/places)",
    )
    suggested_replies: Optional[List[dict]] = Field(
        None,
        description="Quick reply chips for missing preferences",
    )
    follow_up_questions: Optional[List[str]] = Field(
        None,
        description="Follow-up questions extracted from AI response, displayed as clickable cards",
    )

class HistoryOut(BaseModel):
    session_id: str
    messages: list


# --- Travel data persistence schemas ---

class PlaceRatingEntry(BaseModel):
    rating: Optional[float] = None
    score: Optional[float] = None
    selected: bool = False

class PlaceRatingsIn(BaseModel):
    ratings: dict[str, PlaceRatingEntry]
    session_secret: Optional[str] = Field(None, description="Секрет анонимной сессии (если user_id ещё не привязан)")

class PlaceRatingsOut(BaseModel):
    session_id: str
    ratings: Optional[dict[str, PlaceRatingEntry]] = None

class PlacesSnapshotIn(BaseModel):
    places: list[dict]
    session_secret: Optional[str] = Field(None, description="Секрет анонимной сессии")

class PlacesSnapshotOut(BaseModel):
    session_id: str
    places: Optional[list[dict]] = None

class GraphIn(BaseModel):
    geojson: dict
    session_secret: Optional[str] = Field(None, description="Секрет анонимной сессии")

class GraphOut(BaseModel):
    session_id: str
    geojson: Optional[dict] = None

class SavedRouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    destination: str = Field(..., min_length=1, max_length=200)
    session_id: Optional[str] = None
    places: list[dict] = Field(...)
    graph_geojson: Optional[dict] = None

class SavedRouteOut(BaseModel):
    id: str
    name: str
    destination: str
    session_id: Optional[str] = None
    places: list[dict]
    graph_geojson: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class SavedRouteListItem(BaseModel):
    id: str
    name: str
    destination: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# --- Suitcase (Мой чемодан) ---

class SuitcaseTripCreate(BaseModel):
    country: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=200)
    start_date: str = Field(..., min_length=8, max_length=32)
    end_date: str = Field(..., min_length=8, max_length=32)
    image: Optional[str] = Field(None, max_length=1024)
    mood: Optional[str] = Field(None, max_length=100)
    route_json: Optional[str] = None
    impressions: Optional[str] = None
    photos: Optional[list] = None
    is_archived: bool = False


class SuitcaseTripPatch(BaseModel):
    country: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=200)
    start_date: Optional[str] = Field(None, max_length=32)
    end_date: Optional[str] = Field(None, max_length=32)
    image: Optional[str] = Field(None, max_length=1024)
    mood: Optional[str] = Field(None, max_length=100)
    route_json: Optional[str] = None
    impressions: Optional[str] = None
    photos: Optional[list] = None
    is_archived: Optional[bool] = None


class SuitcaseTripOut(BaseModel):
    id: str
    country: str
    city: str
    start_date: str
    end_date: str
    image: Optional[str] = None
    mood: Optional[str] = None
    route_json: Optional[str] = None
    impressions: Optional[str] = None
    photos: Optional[list] = None
    is_archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SuitcaseExpenseCreate(BaseModel):
    amount: float = Field(..., ge=0)
    category: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=500)
    date: str = Field(..., min_length=8, max_length=32)
    currency: Optional[str] = Field(None, max_length=8)


class SuitcaseExpensePatch(BaseModel):
    amount: Optional[float] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=64)
    title: Optional[str] = Field(None, max_length=500)
    date: Optional[str] = Field(None, max_length=32)
    currency: Optional[str] = Field(None, max_length=8)


class SuitcaseExpenseOut(BaseModel):
    id: str
    trip_id: str
    amount: float
    category: str
    title: str
    date: str
    currency: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SuitcaseGoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    current: int = Field(0, ge=0)
    total: int = Field(..., ge=1)
    color: str = Field("#007AFF", max_length=32)


class SuitcaseGoalPatch(BaseModel):
    title: Optional[str] = Field(None, max_length=300)
    current: Optional[int] = Field(None, ge=0)
    total: Optional[int] = Field(None, ge=1)
    color: Optional[str] = Field(None, max_length=32)


class SuitcaseGoalOut(BaseModel):
    id: str
    title: str
    current: int
    total: int
    color: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SuitcaseWorkspaceOut(BaseModel):
    trips: list[SuitcaseTripOut]
    expenses: list[SuitcaseExpenseOut]
    goals: list[SuitcaseGoalOut]
