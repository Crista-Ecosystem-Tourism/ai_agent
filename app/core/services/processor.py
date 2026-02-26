import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Union, Optional, Any

from pydantic_ai import Agent
from app.core.services.places import PlacesSearchService
from app.core.services.route import RouteService, RouteResult
from app.core.models import TravelDeps
from app.api.schemas import SearchResult, Place

logger = logging.getLogger(__name__)


@dataclass
class ProcessorResult:
    """Единый результат обработки сообщения."""
    response: Union[str, List[SearchResult]]
    has_results: bool = False
    is_complete: bool = False
    route_geojson: Optional[dict] = None
    route_metadata: Optional[dict] = None
    search_results: Optional[List[SearchResult]] = None


class MessageProcessor:
    def __init__(self, preferences_agent, model):
        self.preferences_agent = preferences_agent
        self.model = model

    async def process_message(
        self,
        user_msg: str,
        deps: TravelDeps,
        message_history: Optional[list] = None,
        generate_search_response: bool = False
    ) -> ProcessorResult:
        try:
            return await self._process_message_core(
                user_msg, deps, message_history, generate_search_response
            )
        except Exception as e:
            mapped = self._map_provider_error(e)
            if mapped is not None:
                detail = mapped
                user_text = detail.get("message") or "Запрос отклонен политикой модерации. Переформулируйте запрос."
                return ProcessorResult(response=user_text)
            import traceback
            traceback.print_exc()
            return ProcessorResult(response="Произошла ошибка при обработке запроса. Попробуйте позже.")

    async def _process_message_core(
        self,
        user_msg: str,
        deps: TravelDeps,
        message_history: Optional[list],
        generate_search_response: bool
    ) -> ProcessorResult:
        print("Анализ сообщения пользователя...")

        await self._update_preferences(user_msg, deps, message_history)

        if deps.user_preferences.has_searchable_info():
            return await self._handle_searchable_message(deps, generate_search_response)
        else:
            return await self._handle_insufficient_info(deps)

    def _map_provider_error(self, e: Exception) -> Optional[dict]:
        ""
        msg = str(e)
        if ("status_code: 400" in msg) and ("content_filter" in msg or "ResponsibleAIPolicyViolation" in msg):
            provider_payload = None
            try:
                m = re.search(r"'raw': '(.+?)'", msg)
                if m:
                    raw_json = m.group(1)
                    provider_payload = json.loads(raw_json)
            except Exception:
                provider_payload = {"error": {"code": "content_filter"}}

            return {
                "type": "content_filter",
                "title": "Запрос отклонен политикой модерации провайдера",
                "message": "Формулировка запроса нарушает правила контент‑безопасности. Переформулируйте запрос и попробуйте снова.",
                "provider": provider_payload
            }
        return None

    async def _update_preferences(
        self,
        user_msg: str,
        deps: TravelDeps,
        message_history=None
    ) -> None:
        history = list(message_history or [])
        history = history[-8:]
        result = await self.preferences_agent.agent.run(
            user_msg,
            deps=deps,
            message_history=history
        )
        extracted = result.output
        deps.user_preferences = deps.user_preferences.merge_with(extracted)

        print(f"\nОбновленные предпочтения:")
        print(f"   Город: {deps.user_preferences.city}")
        print(f"   Тип: {deps.user_preferences.destination_type}")
        print(f"   Компания: {deps.user_preferences.travel_companions}")
        print(f"   Бюджет: {deps.user_preferences.budget}")
        print(f"   Активности: {deps.user_preferences.activities}")
        print(f"   Можно искать: {deps.user_preferences.has_searchable_info()}")

    async def _handle_searchable_message(
            self,
            deps: TravelDeps,
            generate_search_response: bool = False
        ) -> ProcessorResult:
        print("\nЕсть информация для поиска. Начинаю поиск.")

        search_results = await self._execute_search_queries(deps)

        if search_results:
            conversation_complete = deps.user_preferences.is_complete()

            # Собираем все Place из результатов поиска для маршрутизации
            all_places: List[Place] = []
            for result in search_results:
                all_places.extend(result['places'])

            # Строим маршрут (graceful degradation — при ошибке route_result=None)
            route_result = await RouteService.build_route(
                all_places, deps.http_client
            )

            route_geojson = None
            route_metadata = None
            if route_result is not None:
                route_geojson = route_result.geojson
                route_metadata = {
                    "graph_id": route_result.graph_id,
                    "build_time_seconds": route_result.build_time_seconds,
                    "nodes_count": route_result.nodes_count,
                    "edges_count": route_result.edges_count,
                    "alternatives_count": route_result.alternatives_count,
                    "metrics": route_result.metrics,
                }
                logger.info(
                    "Маршрут построен: %d узлов, %d рёбер, %.2f сек",
                    route_result.nodes_count,
                    route_result.edges_count,
                    route_result.build_time_seconds,
                )

            if generate_search_response:
                return await self._generate_search_response(
                    deps, search_results, route_geojson, route_metadata
                )
            else:
                structured_results = [
                    SearchResult(
                        query=result['query'],
                        places=result['places'],
                        count=len(result['places'])
                    )
                    for result in search_results
                ]
                return ProcessorResult(
                    response=structured_results,
                    has_results=True,
                    is_complete=conversation_complete,
                    route_geojson=route_geojson,
                    route_metadata=route_metadata,
                )
        else:
            return await self._handle_empty_search_results(deps)

    async def _execute_search_queries(self, deps: TravelDeps) -> list:
        search_queries = deps.user_preferences.get_search_queries()
        print(f"\nСгенерированные запросы:")
        for i, q in enumerate(search_queries, 1):
            print(f"   {i}. {q}")

        all_results = []
        for query in search_queries:
            places = await PlacesSearchService.search_places_in_rag(
                deps=deps,
                query=query,
                city=deps.user_preferences.city,
            )
            if places:
                all_results.append({
                    "query": query,
                    "places": places
                })

        return all_results

    async def _generate_search_response(
        self,
        deps: TravelDeps,
        search_results: list,
        route_geojson: Optional[dict] = None,
        route_metadata: Optional[dict] = None,
    ) -> ProcessorResult:
        conversation_complete = deps.user_preferences.is_complete()

        if conversation_complete:
            prompt = self._build_itinerary_prompt(deps, search_results)
        else:
            prompt = self._build_places_prompt(deps, search_results)

        response_agent = Agent(model=self.model)
        result = await response_agent.run(prompt)
        response = result.output
        print(f"\nОтвет готов! Разговор завершен: {conversation_complete}")

        structured = [
            SearchResult(
                query=r['query'],
                places=r['places'],
                count=len(r['places']),
            )
            for r in search_results
        ]

        return ProcessorResult(
            response=response,
            has_results=True,
            is_complete=conversation_complete,
            route_geojson=route_geojson,
            route_metadata=route_metadata,
            search_results=structured,
        )

    def _build_places_prompt(self, deps: TravelDeps, search_results: list) -> str:
        search_context = self._build_search_context(search_results)
        missing = deps.user_preferences.missing_info()
        return (
            f"На основе результатов поиска составь полезный ответ пользователю.\n"
            f"{search_context}\n"
            f"Предпочтения пользователя:\n"
            f"{deps.user_preferences.model_dump_json(exclude_none=True, indent=2)}\n"
            f"ТВОИ ЗАДАЧИ:\n"
            f"1. Представь найденные места в понятном формате\n"
            f"2. Выбери 5-10 лучших вариантов и опиши каждый\n"
            f"3. Объясни почему эти места подходят пользователю\n"
            f"4. ВАЖНО: После представления мест задай 1-2 коротких уточняющих вопроса: {', '.join(missing)}\n"
            f"Будь дружелюбным, конкретным и полезным."
        )

    def _build_itinerary_prompt(self, deps: TravelDeps, search_results: list) -> str:
        search_context = self._build_search_context(search_results)
        prefs = deps.user_preferences
        days = prefs.duration_days or 3
        return (
            f"Составь ПЛАН ПУТЕШЕСТВИЯ по дням на основе результатов поиска.\n\n"
            f"{search_context}\n\n"
            f"Предпочтения пользователя:\n"
            f"{prefs.model_dump_json(exclude_none=True, indent=2)}\n\n"
            f"ТВОИ ЗАДАЧИ:\n"
            f"1. Составь план на {days} дней\n"
            f"2. Для каждого дня распиши по времени суток: утро, обед, день, вечер\n"
            f"3. Для каждого слота укажи конкретное место из результатов поиска\n"
            f"4. Учитывай бюджет ({prefs.budget}), компанию ({prefs.travel_companions}) "
            f"и интересы ({', '.join(prefs.activities) if prefs.activities else 'общие'})\n"
            f"5. Добавь практические советы: как добраться, что взять с собой\n"
            f"6. В конце дай краткую сводку по бюджету\n\n"
            f"Формат ответа:\n"
            f"# План путешествия: {prefs.city or prefs.destination_type}\n"
            f"## День 1\n"
            f"**Утро:** ...\n"
            f"**Обед:** ...\n"
            f"**День:** ...\n"
            f"**Вечер:** ...\n"
            f"...\n\n"
            f"Будь конкретным, используй реальные места из поиска."
        )

    def _build_search_context(self, search_results: list) -> str:
        search_context = "Результаты поиска из RAG:\n\n"
        for idx, result in enumerate(search_results, 1):
            search_context += f"Запрос {idx}: {result['query']}\n"
            search_context += f"Найдено: {len(result['places'])} мест\n\n"
            search_context += "Места:\n"

            for i, place in enumerate(result['places'], 1):
                text = place.page_content or place.name or str(place)
                place_short = text[:300] + "..." if len(text) > 300 else text
                search_context += f"{i}. {place_short}\n"

        return search_context

    async def _handle_empty_search_results(self, deps: TravelDeps) -> ProcessorResult:
        print("\nRAG не вернул результатов")

        response = "К сожалению, не нашел подходящих мест в базе данных. "

        missing = deps.user_preferences.missing_info()
        if missing:
            follow_up = Agent(model=self.model)
            question = await follow_up.run(
                f"""Результаты поиска пустые. Задай пользователю уточняющий вопрос.
                Текущая информация: {deps.user_preferences.model_dump_json(exclude_none=True)}
                Нужно узнать: {', '.join(missing)}
                Создай ОДИН короткий вопрос чтобы уточнить детали."""
            )
            response += question.output
        else:
            response += "Попробуйте изменить критерии поиска."

        return ProcessorResult(response=response)

    async def _handle_insufficient_info(self, deps: TravelDeps) -> ProcessorResult:
        print("\nНедостаточно информации для поиска - задаем вопросы")

        follow_up = Agent(model=self.model)
        question = await follow_up.run(
            f"""Пользователь начал разговор о планировании отдыха.

            Текущая информация: {deps.user_preferences}
            Нужно узнать минимум: {', '.join(deps.user_preferences.missing_info())}

            Создай ОДИН короткий, дружелюбный вопрос чтобы узнать базовую информацию.
            Например: "Куда вы хотите поехать?" или "Какой тип отдыха вас интересует?"

            Будь естественным и не задавай несколько вопросов сразу.
            """
        )
        return ProcessorResult(response=question.output)
