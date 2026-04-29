from app.core.models import TravelDeps
from app.core.utils.rag import remove_duplicates
from app.config.agent_settings import RAG_CONFIG
from app.api.schemas import Place


class PlacesSearchService:

    @staticmethod
    async def search_places_in_rag(
        deps: TravelDeps,
        query: str,
        city: str,
        top_k: int = RAG_CONFIG["top_k"],
        page_content: bool = False,
        rm_duplicates: bool = True
    ) -> list[str]:
        try:
            search_url = RAG_CONFIG["url"] + RAG_CONFIG["search_endpoint"]
            if rm_duplicates:
                k=top_k
                top_k *= 2

            # Город в тексте запроса: генератор запросов намеренно не включает city в строку.
            # metadata_filter по city не используем — в Chroma у многих документов city пустой,
            # из‑за чего Chroma отдаёт 0 результатов при {"city": "Москва"}.
            query_text = f"{query} {city}".strip() if city else query
            data = {
                "query": query_text,
                "top_k": top_k,
                "distance_threshold": RAG_CONFIG["distance_threshold"],
            }
            
            response = await deps.http_client.post(
                search_url,
                json=data,
                timeout=20.0
            )

            response.raise_for_status()
            results = response.json().get("results", [])
            if rm_duplicates:
                results = remove_duplicates(results)
                results = results[:k]

            if page_content:
                contents: list[str] = []
                for result in results:
                    content = result.get("data", {}).get("page_content", "")
                    if content:
                        contents.append(content)
                return contents
            
            places = []
            for result in results:
                data = result.get("data", {})
                
                place = Place(
                    id=data.get("id"),
                    name=data.get("name"),
                    city=data.get("city"),
                    country=data.get("country"),
                    description=data.get("description"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    rating=data.get("rating"),
                    review_count=data.get("review_count"),
                    subtype=data.get("subtype"),
                    activities=data.get("activities"),
                    postalcode=data.get("postalcode"),
                    page_content=data.get("page_content"),
                )
                places.append(place)
            
            return places

            
        except Exception as e:
            print(f"Ошибка поиска в RAG: {e}")
            return []
    
