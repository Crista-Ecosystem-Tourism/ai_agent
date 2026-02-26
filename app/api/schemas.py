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

class HistoryOut(BaseModel):
    session_id: str
    messages: list
