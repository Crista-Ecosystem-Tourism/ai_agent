import re
import json
from typing import List, Union, Tuple, Optional, Any

from pydantic_ai import Agent
from app.core.services.places import PlacesSearchService
from app.core.models import TravelDeps
from app.api.schemas import SearchResult


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
    ) -> Tuple[Union[str, List[SearchResult]], bool, bool]:
        try:
            return await self._process_message_core(
                user_msg, deps, message_history, generate_search_response
            )
        except Exception as e:
            mapped = self._map_provider_error(e)
            if mapped is not None:
                detail = mapped
                user_text = detail.get("message") or "Запрос отклонен политикой модерации. Переформулируйте запрос."
                return user_text, False, False
            return "Произошла ошибка при обработке запроса. Попробуйте позже.", False, False

    async def _process_message_core(
        self,
        user_msg: str,
        deps: TravelDeps,
        message_history: Optional[list],
        generate_search_response: bool
    ) -> Tuple[Union[str, List[SearchResult]], bool, bool]:
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
        deps.user_preferences = result.output
        
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
        ) -> tuple[str, bool, bool]:
        print("\nЕсть информация для поиска. Начинаю поиск.")
        
        search_results = await self._execute_search_queries(deps)
        
        if search_results:
            conversation_complete = deps.user_preferences.is_complete()

            if generate_search_response:
                return await self._generate_search_response(deps, search_results)
            else:
                structured_results = [
                    SearchResult(
                        query=result['query'],
                        places=result['places'],
                        count=len(result['places'])
                    )
                    for result in search_results
                ]
                return structured_results, True, conversation_complete
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
        search_results: list
    ) -> tuple[str, bool, bool]:
        search_context = self._build_search_context(search_results)
        missing = deps.user_preferences.missing_info()
        
        prompt = f"""На основе результатов поиска составь полезный ответ пользователю.
        {search_context}
        Предпочтения пользователя:
        {deps.user_preferences.model_dump_json(exclude_none=True, indent=2)}
        ТВОИ ЗАДАЧИ:
        1. Представь найденные места в понятном формате
        2. Выбери 5-10 лучших вариантов и опиши каждый
        3. Объясни почему эти места подходят пользователю
        {"4. ВАЖНО: После представления мест задай 1-2 коротких уточняющих вопроса: " + ', '.join(missing) if missing else "4. Вся информация собрана - финальные рекомендации готовы!"}
        Будь дружелюбным, конкретным и полезным.
        """
        
        # мб добавить генерацию ответа через агента
        # response_agent = Agent(model=self.model, deps_type=TravelDeps)
        # response_result = await response_agent.run(prompt, deps=deps)
        # conversation_complete = deps.user_preferences.is_complete()
        
        conversation_complete = deps.user_preferences.is_complete()
        print(f"\nОтвет готов! Разговор завершен: {conversation_complete}")
        
        response = "Найдены подходящие места! " + prompt[:100] + "..."
        return response, True, conversation_complete
    
    def _build_search_context(self, search_results: list) -> str:
        search_context = "Результаты поиска из RAG:\n\n"
        for idx, result in enumerate(search_results, 1):
            search_context += f"Запрос {idx}: {result['query']}\n"
            search_context += f"Найдено: {len(result['places'])} мест\n\n"
            search_context += "Места:\n"

            for i, place in enumerate(result['places'], 1):
                place_short = place[:300] + "..." if len(place) > 300 else place
                search_context += "\n"
        
        return search_context
    
    async def _handle_empty_search_results(self, deps: TravelDeps) -> tuple[str, bool, bool]:
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
        
        return response, False, False
    
    async def _handle_insufficient_info(self, deps: TravelDeps) -> tuple[str, bool, bool]:
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
        return question.output, False, False
