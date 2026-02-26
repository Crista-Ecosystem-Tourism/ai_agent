"""Тесты для UserPreferences: merge_with и нормализация городов."""

import pytest
from app.core.models import UserPreferences, CITY_ALIASES


# ---------------------------------------------------------------------------
# 1. City normalization via field_validator
# ---------------------------------------------------------------------------

class TestCityNormalization:
    """Проверяем, что неформальные названия приводятся к каноническому виду."""

    @pytest.mark.parametrize("raw,expected", [
        ("Питер", "Санкт-Петербург"),
        ("питер", "Санкт-Петербург"),
        ("ПИТЕР", "Санкт-Петербург"),
        ("Спб", "Санкт-Петербург"),
        ("спб", "Санкт-Петербург"),
        ("СПб", "Санкт-Петербург"),
        ("Петербург", "Санкт-Петербург"),
        ("санкт петербург", "Санкт-Петербург"),
        ("Мск", "Москва"),
        ("мск", "Москва"),
    ])
    def test_alias_normalized(self, raw: str, expected: str):
        prefs = UserPreferences(city=raw)
        assert prefs.city == expected

    @pytest.mark.parametrize("city", [
        "Санкт-Петербург",
        "Москва",
        "Сочи",
        "Казань",
        "Калининград",
    ])
    def test_canonical_passthrough(self, city: str):
        """Канонические названия не меняются."""
        prefs = UserPreferences(city=city)
        assert prefs.city == city

    def test_none_stays_none(self):
        prefs = UserPreferences(city=None)
        assert prefs.city is None

    def test_empty_string_becomes_none(self):
        prefs = UserPreferences(city="")
        assert prefs.city is None

    def test_whitespace_trimmed(self):
        prefs = UserPreferences(city="  Сочи  ")
        assert prefs.city == "Сочи"

    def test_whitespace_alias_trimmed(self):
        prefs = UserPreferences(city="  питер  ")
        assert prefs.city == "Санкт-Петербург"


# ---------------------------------------------------------------------------
# 2. merge_with — city switching
# ---------------------------------------------------------------------------

class TestMergeWith:
    """Проверяем правильность слияния предпочтений, особенно смену города."""

    def test_new_city_replaces_old(self):
        """Если LLM извлёк новый город, он заменяет старый."""
        old = UserPreferences(city="Сочи", budget="эконом")
        new = UserPreferences(city="Санкт-Петербург")
        merged = old.merge_with(new)
        assert merged.city == "Санкт-Петербург"
        assert merged.budget == "эконом"  # остальное сохраняется

    def test_none_city_keeps_old(self):
        """Если LLM не извлёк город (None), старый сохраняется."""
        old = UserPreferences(city="Сочи", budget="эконом")
        new = UserPreferences(city=None)
        merged = old.merge_with(new)
        assert merged.city == "Сочи"

    def test_alias_city_replaces_old(self):
        """Если LLM вернул 'Питер', нормализация превращает в 'Санкт-Петербург'."""
        old = UserPreferences(city="Сочи")
        new = UserPreferences(city="Питер")  # validator нормализует
        merged = old.merge_with(new)
        assert merged.city == "Санкт-Петербург"

    def test_same_city_keeps(self):
        """Повторное указание того же города не ломает ничего."""
        old = UserPreferences(city="Сочи")
        new = UserPreferences(city="Сочи")
        merged = old.merge_with(new)
        assert merged.city == "Сочи"

    def test_activities_combined(self):
        """Активности объединяются без дубликатов."""
        old = UserPreferences(activities=["пляж", "экскурсии"])
        new = UserPreferences(activities=["экскурсии", "рестораны"])
        merged = old.merge_with(new)
        assert merged.activities == ["пляж", "экскурсии", "рестораны"]

    def test_new_budget_replaces_old(self):
        old = UserPreferences(budget="эконом")
        new = UserPreferences(budget="премиум")
        merged = old.merge_with(new)
        assert merged.budget == "премиум"

    def test_none_budget_keeps_old(self):
        old = UserPreferences(budget="эконом")
        new = UserPreferences(budget=None)
        merged = old.merge_with(new)
        assert merged.budget == "эконом"

    def test_duration_days_overwrite(self):
        old = UserPreferences(duration_days=3)
        new = UserPreferences(duration_days=7)
        merged = old.merge_with(new)
        assert merged.duration_days == 7

    def test_duration_days_none_keeps_old(self):
        old = UserPreferences(duration_days=3)
        new = UserPreferences(duration_days=None)
        merged = old.merge_with(new)
        assert merged.duration_days == 3

    def test_full_city_switch_scenario(self):
        """Сценарий из бага: Сочи → Питер при полных предпочтениях."""
        old = UserPreferences(
            city="Сочи",
            destination_type="море",
            travel_companions="пара",
            budget="эконом",
            duration_days=3,
            activities=["пляж", "рестораны"],
        )
        # LLM извлекает только город из "хочу в Питер также"
        new = UserPreferences(city="Питер")
        merged = old.merge_with(new)

        assert merged.city == "Санкт-Петербург"
        assert merged.destination_type == "море"
        assert merged.travel_companions == "пара"
        assert merged.budget == "эконом"
        assert merged.duration_days == 3


# ---------------------------------------------------------------------------
# 3. has_searchable_info / is_complete / missing_info
# ---------------------------------------------------------------------------

class TestPreferencesHelpers:
    def test_has_searchable_with_city(self):
        assert UserPreferences(city="Сочи").has_searchable_info() is True

    def test_has_searchable_with_type(self):
        assert UserPreferences(destination_type="море").has_searchable_info() is True

    def test_has_searchable_empty(self):
        assert UserPreferences().has_searchable_info() is False

    def test_is_complete(self):
        prefs = UserPreferences(
            city="Сочи",
            travel_companions="пара",
            budget="эконом",
        )
        assert prefs.is_complete() is True

    def test_is_not_complete_missing_budget(self):
        prefs = UserPreferences(city="Сочи", travel_companions="пара")
        assert prefs.is_complete() is False

    def test_missing_info(self):
        prefs = UserPreferences(city="Сочи")
        missing = prefs.missing_info()
        assert "с кем едете" in missing
        assert "бюджет" in missing
