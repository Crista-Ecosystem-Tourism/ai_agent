from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import Optional, Literal, List
import httpx


class UserPreferences(BaseModel):
    destination_type: Optional[Literal["море", "горы", "город", "природа"]] = None
    city: Optional[str] = None
    travel_companions: Optional[Literal["один", "пара", "семья", "друзья"]] = None
    budget: Optional[Literal["эконом", "средний", "премиум", "люкс"]] = None
    activities: list[str] = Field(default_factory=list)
    duration_days: Optional[int] = None
    
    def merge_with(self, new: "UserPreferences") -> "UserPreferences":
        """Merge new preferences (from current message) with existing ones.
        New non-empty values overwrite old; activities are combined."""
        return UserPreferences(
            destination_type=new.destination_type or self.destination_type,
            city=new.city or self.city,
            travel_companions=new.travel_companions or self.travel_companions,
            budget=new.budget or self.budget,
            activities=list(dict.fromkeys(self.activities + new.activities)),
            duration_days=new.duration_days if new.duration_days is not None else self.duration_days,
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

