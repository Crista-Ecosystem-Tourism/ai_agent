import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Union, Optional, Any

from pydantic_ai import Agent
from app.core.services.places import PlacesSearchService

from app.core.models import TravelDeps, SearchQueries, RerankResult, Itinerary, UserPreferences
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
    itinerary: Optional[Any] = None
    suggested_replies: Optional[list] = None
    follow_up_questions: Optional[List[str]] = None


class MessageProcessor:
    def __init__(self, preferences_agent, model):
        self.preferences_agent = preferences_agent
        self.model = model

    def _build_suggested_replies(self, prefs: UserPreferences) -> list[dict] | None:
        groups = []

        if not prefs.budget:
            groups.append({
                "category": "budget",
                "label": "Бюджет",
                "icon": "wallet",
                "options": [
                    {"value": "эконом", "label": "Эконом", "description": "~3 000 ₽/день"},
                    {"value": "средний", "label": "Средний", "description": "~7 000 ₽/день"},
                    {"value": "премиум", "label": "Премиум", "description": "~15 000 ₽/день"},
                    {"value": "люкс", "label": "Люкс", "description": "30 000+ ₽/день"},
                ],
                "allow_custom": True,
            })

        if not prefs.travel_companions:
            groups.append({
                "category": "companions",
                "label": "Компания",
                "icon": "users",
                "options": [
                    {"value": "один", "label": "Один", "description": "Соло-путешествие"},
                    {"value": "пара", "label": "Пара", "description": "Романтический отдых"},
                    {"value": "семья", "label": "Семья", "description": "С детьми"},
                    {"value": "друзья", "label": "Друзья", "description": "Компанией"},
                ],
                "allow_custom": True,
            })

        if not prefs.destination_type and not prefs.city:
            groups.append({
                "category": "destination",
                "label": "Тип отдыха",
                "icon": "compass",
                "options": [
                    {"value": "море", "label": "Море", "description": "Пляж и солнце"},
                    {"value": "горы", "label": "Горы", "description": "Треккинг и природа"},
                    {"value": "город", "label": "Город", "description": "Культура и шопинг"},
                    {"value": "природа", "label": "Природа", "description": "Парки и озёра"},
                ],
                "allow_custom": True,
            })

        if not prefs.duration_days:
            groups.append({
                "category": "duration",
                "label": "Длительность",
                "icon": "clock",
                "options": [
                    {"value": "2", "label": "2 дня", "description": "Выходные"},
                    {"value": "3", "label": "3 дня", "description": "Короткий отпуск"},
                    {"value": "5", "label": "5 дней", "description": "Рабочая неделя"},
                    {"value": "7", "label": "7 дней", "description": "Полноценный отпуск"},
                ],
                "allow_custom": True,
            })

        if not prefs.origin_city and prefs.city:
            groups.append({
                "category": "origin_city",
                "label": "Город вылета",
                "icon": "plane",
                "options": [
                    {"value": "Москва", "label": "Москва", "description": "SVO / DME / VKO"},
                    {"value": "Санкт-Петербург", "label": "Санкт-Петербург", "description": "LED"},
                    {"value": "Краснодар", "label": "Краснодар", "description": "KRR"},
                    {"value": "Екатеринбург", "label": "Екатеринбург", "description": "SVX"},
                    {"value": "Новосибирск", "label": "Новосибирск", "description": "OVB"},
                ],
                "allow_custom": True,
            })

        return groups if groups else None

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
        print(f"   Откуда: {deps.user_preferences.origin_city}")
        print(f"   Город: {deps.user_preferences.city}")
        print(f"   Тип: {deps.user_preferences.destination_type}")
        print(f"   Компания: {deps.user_preferences.travel_companions}")
        print(f"   Бюджет: {deps.user_preferences.budget}")
        print(f"   Активности: {deps.user_preferences.activities}")
        print(f"   Хочет маршрут: {deps.user_preferences.wants_itinerary}")
        print(f"   Можно искать: {deps.user_preferences.has_searchable_info()}")

    async def _handle_searchable_message(
            self,
            deps: TravelDeps,
            generate_search_response: bool = False
        ) -> ProcessorResult:
        print("\nЕсть информация для поиска. Начинаю поиск.")

        search_results = await self._execute_search_queries(deps)

        if search_results:
            try:
                search_results = await self._rerank_places(search_results, deps)
            except Exception as e:
                logger.warning("Reranking failed, using unranked: %s", e)

        if search_results:
            conversation_complete = deps.user_preferences.is_complete()
            wants_itinerary = deps.user_preferences.wants_itinerary
            suggested_replies = self._build_suggested_replies(deps.user_preferences)

            # When wants_itinerary=True and all prefs are filled — generate itinerary immediately
            if wants_itinerary and conversation_complete:
                structured_results = [
                    SearchResult(
                        query=result['query'],
                        places=result['places'],
                        count=len(result['places'])
                    )
                    for result in search_results
                ]
                itinerary = None
                try:
                    itinerary = await self._generate_itinerary(deps, search_results)
                except Exception as e:
                    logger.warning("Itinerary generation failed: %s", e)

                summary = itinerary.summary if itinerary else "Ваш план путешествия готов!"
                return ProcessorResult(
                    response=summary,
                    has_results=True,
                    is_complete=True,
                    route_geojson=None,
                    route_metadata=None,
                    search_results=structured_results,
                    itinerary=itinerary,
                    suggested_replies=None,
                )

            if generate_search_response:
                result = await self._generate_search_response(
                    deps, search_results
                )
                result.suggested_replies = suggested_replies
                return result
            else:
                structured_results = [
                    SearchResult(
                        query=result['query'],
                        places=result['places'],
                        count=len(result['places'])
                    )
                    for result in search_results
                ]

                # Generate structured itinerary when conversation is complete
                itinerary = None
                if conversation_complete:
                    try:
                        itinerary = await self._generate_itinerary(deps, search_results)
                    except Exception as e:
                        logger.warning("Itinerary generation failed: %s", e)

                return ProcessorResult(
                    response=structured_results,
                    has_results=True,
                    is_complete=conversation_complete,
                    route_geojson=None,
                    route_metadata=None,
                    itinerary=itinerary,
                    suggested_replies=suggested_replies,
                )
        else:
            return await self._handle_empty_search_results(deps)

    async def _generate_smart_queries(self, deps: TravelDeps) -> list[str]:
        prefs = deps.user_preferences
        prompt = (
            "Сгенерируй 3-5 РАЗНООБРАЗНЫХ поисковых запросов для поиска мест отдыха.\n\n"
            f"Предпочтения:\n"
            f"- Город: {prefs.city or 'не указан'}\n"
            f"- Тип отдыха: {prefs.destination_type or 'не указан'}\n"
            f"- Компания: {prefs.travel_companions or 'не указана'}\n"
            f"- Бюджет: {prefs.budget or 'не указан'}\n"
            f"- Активности: {', '.join(prefs.activities) if prefs.activities else 'не указаны'}\n"
            f"- Дней: {prefs.duration_days or 'не указано'}\n\n"
            "ПРАВИЛА:\n"
            "1. НЕ включай название города — город фильтруется отдельно\n"
            "2. Каждый запрос на русском языке\n"
            "3. Покрывай РАЗНЫЕ аспекты:\n"
            "   - Если есть активности → запрос для каждой\n"
            "   - Добавь запросы по типу отдыха и компании\n"
            "   - Учитывай бюджет\n"
            "4. Примеры хороших запросов:\n"
            "   - 'романтические рестораны с видом на море'\n"
            "   - 'бесплатные достопримечательности и музеи'\n"
            "   - 'активный отдых водные виды спорта'\n"
        )
        query_agent = Agent(model=self.model, output_type=SearchQueries)
        result = await query_agent.run(prompt)
        return result.output.queries

    async def _execute_search_queries(self, deps: TravelDeps) -> list:
        try:
            search_queries = await self._generate_smart_queries(deps)
        except Exception as e:
            logger.warning("Smart query generation failed, fallback: %s", e)
            search_queries = deps.user_preferences.get_search_queries()

        print(f"\nСгенерированные запросы:")
        for i, q in enumerate(search_queries, 1):
            print(f"   {i}. {q}")

        all_results = []
        seen_ids = set()

        for query in search_queries:
            places = await PlacesSearchService.search_places_in_rag(
                deps=deps, query=query, city=deps.user_preferences.city,
            )
            if places:
                unique = [p for p in places if not p.id or p.id not in seen_ids]
                seen_ids.update(p.id for p in unique if p.id)
                if unique:
                    all_results.append({"query": query, "places": unique})

        return all_results

    async def _rerank_places(self, all_results: list, deps: TravelDeps, max_places: int = 15) -> list:
        # Собираем все места
        place_map = {}
        for r in all_results:
            for p in r["places"]:
                pid = p.id or p.name
                if pid and pid not in place_map:
                    place_map[pid] = p

        if len(place_map) <= max_places:
            return all_results

        prefs = deps.user_preferences
        summaries = []
        for pid, p in place_map.items():
            s = f"[{pid}] {p.name or 'Без названия'}"
            if p.subtype: s += f" ({p.subtype})"
            if p.rating: s += f" рейтинг:{p.rating}"
            if p.description: s += f" — {p.description[:100]}"
            summaries.append(s)

        prompt = (
            "Отранжируй места по релевантности для пользователя.\n\n"
            f"Предпочтения:\n"
            f"- Тип: {prefs.destination_type or '?'}, Компания: {prefs.travel_companions or '?'}\n"
            f"- Бюджет: {prefs.budget or '?'}, Активности: {', '.join(prefs.activities) or '?'}\n\n"
            f"Места:\n" + "\n".join(summaries) + "\n\n"
            f"Выбери {max_places} лучших. Учитывай: релевантность, разнообразие, рейтинг, соответствие бюджету/компании."
        )
        rerank_agent = Agent(model=self.model, output_type=RerankResult)
        result = await rerank_agent.run(prompt)
        selected = set(result.output.selected_ids)

        reranked = []
        for r in all_results:
            filtered = [p for p in r["places"] if (p.id or p.name) in selected]
            if filtered:
                reranked.append({"query": r["query"], "places": filtered})
        return reranked

    async def _generate_search_response(
        self,
        deps: TravelDeps,
        search_results: list,
    ) -> ProcessorResult:
        conversation_complete = deps.user_preferences.is_complete()

        structured = [
            SearchResult(
                query=r['query'],
                places=r['places'],
                count=len(r['places']),
            )
            for r in search_results
        ]

        if conversation_complete:
            # Try structured itinerary generation
            itinerary = None
            try:
                itinerary = await self._generate_itinerary(deps, search_results)
            except Exception as e:
                logger.warning("Itinerary generation failed, fallback to text: %s", e)

            if itinerary:
                summary_text = itinerary.summary or "Ваш план путешествия готов!"
                print(f"\nСтруктурированный итинерарий готов! Дней: {len(itinerary.days)}")
                return ProcessorResult(
                    response=summary_text,
                    has_results=True,
                    is_complete=True,
                    route_geojson=None,
                    route_metadata=None,
                    search_results=structured,
                    itinerary=itinerary,
                )
            else:
                # Fallback to text itinerary
                prompt = self._build_itinerary_prompt(deps, search_results)
        else:
            prompt = self._build_places_prompt(deps, search_results)

        response_agent = Agent(model=self.model)
        result = await response_agent.run(prompt)
        raw_response = result.output
        response, follow_up_questions = self._extract_questions(raw_response)
        print(f"\nОтвет готов! Разговор завершен: {conversation_complete}, вопросов: {len(follow_up_questions)}")

        return ProcessorResult(
            response=response,
            has_results=True,
            is_complete=conversation_complete,
            route_geojson=None,
            route_metadata=None,
            search_results=structured,
            follow_up_questions=follow_up_questions or None,
        )

    @staticmethod
    def _extract_questions(text: str) -> tuple[str, list[str]]:
        """Extract [Q] tagged questions from AI response text.
        Returns (clean_text, questions_list)."""
        questions = []
        clean_lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("[Q]"):
                q = stripped[3:].strip().rstrip("?").strip() + "?"
                if q != "?":
                    questions.append(q)
            else:
                clean_lines.append(line)
        clean_text = "\n".join(clean_lines).strip()
        # Remove trailing empty lines left after extraction
        while clean_text.endswith("\n\n"):
            clean_text = clean_text[:-1]
        return clean_text, questions

    def _build_places_prompt(self, deps: TravelDeps, search_results: list) -> str:
        search_context = self._build_search_context(search_results)
        missing = deps.user_preferences.missing_info()
        questions_instruction = ""
        if missing:
            questions_instruction = (
                f"5. ВАЖНО — УТОЧНЯЮЩИЕ ВОПРОСЫ: задай 1-2 коротких вопроса про: {', '.join(missing)}\n"
                f"   Каждый вопрос пиши на ОТДЕЛЬНОЙ строке с префиксом [Q].\n"
                f"   Пример:\n"
                f"   [Q] Какой у вас примерный бюджет на день?\n"
                f"   [Q] С кем вы планируете поездку?\n"
                f"   НЕ включай вопросы в основной текст — только через [Q].\n"
            )
        return (
            f"На основе результатов поиска составь полезный ответ пользователю.\n"
            f"{search_context}\n"
            f"Предпочтения пользователя:\n"
            f"{deps.user_preferences.model_dump_json(exclude_none=True, indent=2)}\n"
            f"ТВОИ ЗАДАЧИ:\n"
            f"1. Представь найденные места в понятном формате\n"
            f"2. Выбери 5-10 лучших вариантов и опиши каждый\n"
            f"3. Объясни почему эти места подходят пользователю\n"
            f"4. Будь дружелюбным, конкретным и полезным\n"
            f"{questions_instruction}"
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

    async def _generate_itinerary(self, deps: TravelDeps, search_results: list) -> Itinerary:
        prefs = deps.user_preferences
        days = prefs.duration_days or 3

        # Собираем доступные места с ID
        available_places = []
        for r in search_results:
            for p in r["places"]:
                pid = p.id or p.name
                name = p.name or "Без названия"
                subtype = p.subtype or ""
                rating = p.rating or ""
                desc = (p.description or p.page_content or "")[:150]
                available_places.append(f"[{pid}] {name} ({subtype}) рейтинг:{rating} — {desc}")

        prompt = (
            f"Составь план путешествия на {days} дней.\n\n"
            f"Предпочтения:\n"
            f"- Город: {prefs.city or '?'}\n"
            f"- Тип: {prefs.destination_type or '?'}\n"
            f"- Компания: {prefs.travel_companions or '?'}\n"
            f"- Бюджет: {prefs.budget or '?'}\n"
            f"- Активности: {', '.join(prefs.activities) if prefs.activities else '?'}\n\n"
            f"Доступные места (используй place_id из скобок []):\n"
            + "\n".join(available_places) + "\n\n"
            "ПРАВИЛА:\n"
            f"1. Создай ровно {days} дней\n"
            "2. В каждом дне — столько слотов, сколько нужно (обычно 3-5)\n"
            "3. time_label — свободный текст: 'Утро', 'Обед', 'После обеда', 'Вечер', 'Закат' и т.д.\n"
            "4. place_id — ТОЧНО из списка выше (из квадратных скобок)\n"
            "5. place_name — название места\n"
            "6. note — короткая полезная рекомендация (1-2 предложения): что попробовать, когда лучше идти, лайфхак\n"
            "7. title каждого дня — краткое и вдохновляющее название\n"
            "8. summary — общий совет по путешествию (бюджет, транспорт)\n"
            "9. Одно место может повторяться максимум один раз\n"
            "10. Учитывай бюджет, компанию и тип отдыха при выборе мест и порядке\n"
        )

        itinerary_agent = Agent(model=self.model, output_type=Itinerary)
        result = await itinerary_agent.run(prompt)
        return result.output

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
        suggested_replies = self._build_suggested_replies(deps.user_preferences)

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

        return ProcessorResult(
            response=response,
            suggested_replies=suggested_replies,
        )

    async def _handle_insufficient_info(self, deps: TravelDeps) -> ProcessorResult:
        print("\nНедостаточно информации для поиска - задаем вопросы")

        suggested_replies = self._build_suggested_replies(deps.user_preferences)
        missing = deps.user_preferences.missing_info()

        follow_up = Agent(model=self.model)
        question = await follow_up.run(
            f"""Пользователь начал разговор о планировании отдыха.

            Текущая информация: {deps.user_preferences}
            Нужно узнать минимум: {', '.join(missing)}

            Напиши короткий дружелюбный ответ (1-2 предложения).
            Затем задай 1-2 уточняющих вопроса, каждый на отдельной строке с префиксом [Q].
            Пример:
            Отлично, помогу спланировать отдых!
            [Q] Куда вы хотите поехать?
            [Q] Какой тип отдыха вас интересует — море, горы, город?

            Будь естественным.
            """
        )
        response_text, follow_up_questions = self._extract_questions(question.output)
        return ProcessorResult(
            response=response_text,
            suggested_replies=suggested_replies,
            follow_up_questions=follow_up_questions or None,
        )
