from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass
from typing import Optional, Literal, List
import httpx


# Нормализация неформальных / сокращённых названий городов
# к каноническому виду, который хранится в RAG-базе.
CITY_ALIASES: dict[str, str] = {
    "питер": "Санкт-Петербург",
    "спб": "Санкт-Петербург",
    "с-пб": "Санкт-Петербург",
    "с.петербург": "Санкт-Петербург",
    "с.-петербург": "Санкт-Петербург",
    "санкт петербург": "Санкт-Петербург",
    "петербург": "Санкт-Петербург",
    "мск": "Москва",
    "нск": "Новосибирск",
    "новосиб": "Новосибирск",
    "екб": "Екатеринбург",
    "ебург": "Екатеринбург",
    "нижний": "Нижний Новгород",
    "владик": "Владивосток",
    "ростов": "Ростов-на-Дону",
    "краснодар": "Краснодар",
    "сочи": "Сочи",
}


class UserPreferences(BaseModel):
    destination_type: Optional[Literal["море", "горы", "город", "природа"]] = None
    city: Optional[str] = None
    origin_city: Optional[str] = None
    travel_companions: Optional[Literal["один", "пара", "семья", "друзья"]] = None
    budget: Optional[Literal["эконом", "средний", "премиум", "люкс"]] = None
    activities: list[str] = Field(default_factory=list)
    duration_days: Optional[int] = None
    wants_itinerary: Optional[bool] = None

    @field_validator("city", "origin_city", mode="before")
    @classmethod
    def normalize_city(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            return None
        canonical = CITY_ALIASES.get(stripped.lower())
        return canonical if canonical else stripped

    def merge_with(self, new: "UserPreferences") -> "UserPreferences":
        """Merge new preferences (from current message) with existing ones.
        New non-empty values overwrite old; activities are combined."""
        return UserPreferences(
            destination_type=new.destination_type or self.destination_type,
            city=new.city or self.city,
            origin_city=new.origin_city or self.origin_city,
            travel_companions=new.travel_companions or self.travel_companions,
            budget=new.budget or self.budget,
            activities=list(dict.fromkeys(self.activities + new.activities)),
            duration_days=new.duration_days if new.duration_days is not None else self.duration_days,
            wants_itinerary=new.wants_itinerary if new.wants_itinerary is not None else self.wants_itinerary,
        )

    def has_searchable_info(self) -> bool:
        return self.destination_type is not None or self.city is not None
    
    def is_complete(self) -> bool:
        return all([
            self.destination_type or self.city,
            self.travel_companions,
            self.budget
        ])
    
    def missing_info(self) -> list[str]:
        missing = []
        if not self.destination_type and not self.city:
            missing.append("тип места или конкретный город")
        if not self.travel_companions:
            missing.append("с кем едете")
        if not self.budget:
            missing.append("бюджет")
        return missing
    
    def get_search_queries(self) -> list[str]:
        queries = []
        
        # Если указан конкретный город
        # if self.city:

        if self.activities:
            for activity in self.activities:
                queries.append(activity)
        
        return queries if queries else ["отдых"]


class SearchQueries(BaseModel):
    """Structured output: LLM-generated search queries."""
    queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="3-5 diverse search queries in Russian"
    )

class RerankResult(BaseModel):
    """Structured output: LLM-reranked place IDs."""
    selected_ids: list[str] = Field(
        ...,
        description="Place IDs in ranked order, best first"
    )


class ItinerarySlot(BaseModel):
    """Один слот в дне итинерария."""
    time_label: str = Field(..., description="Время дня, например 'Утро', 'Обед', 'День', 'Вечер'")
    place_id: str = Field(..., description="ID места из search_results")
    place_name: str = Field(..., description="Название места для отображения")
    note: str = Field("", description="Короткая заметка/рекомендация от ассистента")

class ItineraryDay(BaseModel):
    """Один день итинерария."""
    day: int = Field(..., description="Номер дня (1, 2, 3...)")
    title: str = Field(..., description="Краткое название дня, например 'Знакомство с городом'")
    slots: list[ItinerarySlot] = Field(..., description="Слоты дня")

class Itinerary(BaseModel):
    """Structured output: полный итинерарий путешествия."""
    days: list[ItineraryDay] = Field(..., description="Дни путешествия")
    summary: str = Field("", description="Краткая сводка/совет по всему путешествию")


class Place(BaseModel):
    name: str
    location: str
    description: str
    price_range: Optional[str] = None
    activities: List[str] = Field(default_factory=list)
    rating: Optional[float] = None


@dataclass
class TravelDeps:
    rag_service_url: str
    http_client: httpx.AsyncClient
    user_preferences: UserPreferences

