"""Интеграционные тесты: смена города в пайплайне MessageProcessor.

Сценарий бага: пользователь начинает с Сочи, потом просит Питер,
но агент продолжает возвращать сочинские места.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.core.services.processor import MessageProcessor, ProcessorResult
from app.core.models import TravelDeps, UserPreferences
from app.api.schemas import Place


# ---------------------------------------------------------------------------
# Вспомогательные конструкторы
# ---------------------------------------------------------------------------

def _make_deps(city: str = "Сочи", **kwargs) -> TravelDeps:
    prefs = UserPreferences(
        city=city,
        travel_companions="пара",
        budget="эконом",
        duration_days=3,
        **kwargs,
    )
    return TravelDeps(
        rag_service_url="http://localhost:8001/api/v1",
        http_client=AsyncMock(),
        user_preferences=prefs,
    )


def _make_spb_places() -> list[Place]:
    return [
        Place(
            id="spb-1",
            name="Эрмитаж",
            city="Санкт-Петербург",
            country="Россия",
            description="Крупнейший художественный музей",
            latitude=59.9398,
            longitude=30.3146,
            rating=4.9,
            review_count=50000,
            subtype="музей",
        ),
        Place(
            id="spb-2",
            name="Петропавловская крепость",
            city="Санкт-Петербург",
            country="Россия",
            description="Историческая крепость на Заячьем острове",
            latitude=59.9500,
            longitude=30.3167,
            rating=4.8,
            review_count=30000,
            subtype="достопримечательность",
        ),
    ]


def _make_processor_with_city_extraction(extracted_city: str) -> MessageProcessor:
    """Создаёт MessageProcessor, чей preferences_agent вернёт указанный город."""
    mock_agent = MagicMock()
    mock_run_result = AsyncMock()
    mock_run_result.output = UserPreferences(city=extracted_city)
    mock_agent.agent.run = AsyncMock(return_value=mock_run_result)
    return MessageProcessor(preferences_agent=mock_agent, model=MagicMock())


# ---------------------------------------------------------------------------
# 1. Город переключается при явном упоминании
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route", return_value=None)
@patch("app.core.services.processor.PlacesSearchService.search_places_in_rag")
async def test_city_switches_from_sochi_to_spb(mock_search, _mock_route):
    """Когда LLM извлекает 'Санкт-Петербург', поиск идёт по новому городу."""
    spb_places = _make_spb_places()
    mock_search.return_value = spb_places

    # Состояние: уже есть Сочи в предпочтениях
    deps = _make_deps(city="Сочи")
    assert deps.user_preferences.city == "Сочи"

    # LLM извлекает "Санкт-Петербург" из "хочу в Питер"
    processor = _make_processor_with_city_extraction("Санкт-Петербург")
    result = await processor.process_message(
        "Я хочу в Санкт-Петербург также!", deps
    )

    # Проверяем что предпочтения обновились
    assert deps.user_preferences.city == "Санкт-Петербург"

    # Проверяем что RAG вызывался с "Санкт-Петербург"
    for c in mock_search.call_args_list:
        assert c.kwargs.get("city") == "Санкт-Петербург" or c[1].get("city") == "Санкт-Петербург", \
            f"search_places_in_rag вызван с городом: {c}"


# ---------------------------------------------------------------------------
# 2. Нормализация "Питер" → "Санкт-Петербург" через validator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route", return_value=None)
@patch("app.core.services.processor.PlacesSearchService.search_places_in_rag")
async def test_city_alias_normalized_in_pipeline(mock_search, _mock_route):
    """Даже если LLM вернёт 'Питер', validator нормализует в 'Санкт-Петербург'."""
    mock_search.return_value = _make_spb_places()

    deps = _make_deps(city="Сочи")

    # LLM возвращает "Питер" (неформальное название)
    processor = _make_processor_with_city_extraction("Питер")
    await processor.process_message("хочу потом в Питер", deps)

    # Проверяем нормализацию
    assert deps.user_preferences.city == "Санкт-Петербург"

    # Проверяем что RAG получил нормализованное название
    for c in mock_search.call_args_list:
        city_arg = c.kwargs.get("city", c[1].get("city") if len(c[1]) > 1 else None)
        assert city_arg == "Санкт-Петербург"


# ---------------------------------------------------------------------------
# 3. Город НЕ меняется, если LLM не извлёк новый
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route", return_value=None)
@patch("app.core.services.processor.PlacesSearchService.search_places_in_rag")
async def test_city_stays_when_not_mentioned(mock_search, _mock_route):
    """Если пользователь не упоминает город, старый сохраняется."""
    mock_search.return_value = [
        Place(
            id="s1", name="Пляж", city="Сочи", latitude=43.5, longitude=39.7,
            rating=4.5, subtype="пляж",
        ),
    ]

    deps = _make_deps(city="Сочи")

    # LLM НЕ извлекает город (city=None)
    processor = _make_processor_with_city_extraction(None)
    await processor.process_message("покажи ещё рестораны", deps)

    # Город остался Сочи
    assert deps.user_preferences.city == "Сочи"


# ---------------------------------------------------------------------------
# 4. Остальные предпочтения сохраняются при смене города
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route", return_value=None)
@patch("app.core.services.processor.PlacesSearchService.search_places_in_rag")
async def test_other_prefs_preserved_on_city_switch(mock_search, _mock_route):
    """При смене города бюджет, компания, длительность не теряются."""
    mock_search.return_value = _make_spb_places()

    deps = _make_deps(
        city="Сочи",
        destination_type="море",
        activities=["пляж"],
    )

    processor = _make_processor_with_city_extraction("Санкт-Петербург")
    await processor.process_message("теперь Питер", deps)

    assert deps.user_preferences.city == "Санкт-Петербург"
    assert deps.user_preferences.budget == "эконом"
    assert deps.user_preferences.travel_companions == "пара"
    assert deps.user_preferences.duration_days == 3
    assert deps.user_preferences.destination_type == "море"


# ---------------------------------------------------------------------------
# 5. Пустой результат RAG при смене города не откатывает город
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.core.services.processor.Agent")
@patch("app.core.services.processor.PlacesSearchService.search_places_in_rag")
async def test_empty_rag_does_not_revert_city(mock_search, MockAgent):
    """Даже если RAG не нашёл мест в новом городе, город остаётся новым."""
    mock_search.return_value = []  # RAG пустой

    # Мок для follow_up Agent (вызывается при пустых результатах)
    mock_follow_up_result = AsyncMock()
    mock_follow_up_result.output = "К сожалению, не нашёл мест."
    MockAgent.return_value.run = AsyncMock(return_value=mock_follow_up_result)

    deps = _make_deps(city="Сочи")

    processor = _make_processor_with_city_extraction("Санкт-Петербург")
    result = await processor.process_message("хочу в Питер", deps)

    # Город переключился, даже если мест не нашлось
    assert deps.user_preferences.city == "Санкт-Петербург"
    assert result.has_results is False
