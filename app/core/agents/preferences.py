from typing import List
from pydantic_ai import Agent, RunContext

from app.core.models import TravelDeps, UserPreferences
from app.core.prompts.preferences import SYSTEM_PROMPT


class PreferencesAgent:
    def __init__(self, model):
        self.agent = Agent(
            model=model,
            deps_type=TravelDeps,
            output_type=UserPreferences,
            system_prompt=self._get_system_prompt(),
        )
        # self.agent.system_prompt = self._add_progress
        @self.agent.system_prompt
        def add_progress(ctx: RunContext[TravelDeps]) -> str:
            return self._add_progress(ctx)
    
    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT or (
            "Ты помощник по сбору предпочтений для путешествий.\n"
            "Собери информацию о том, куда пользователь хочет поехать и что его интересует.\n"
            "{progress_info}\n"
            "Задавай уточняющие вопросы, чтобы собрать недостающую информацию.\n"
            "Будь дружелюбным и помогающим."
        )

    def _add_progress(self, ctx: RunContext[TravelDeps]) -> str:
        prefs = ctx.deps.user_preferences
        status = self._build_status_list(prefs)
        progress_text = "\n".join(status) if status else "Ничего не собрано"
        can_search = "ДА" if prefs.has_searchable_info() else "НЕТ"
        return (
            "Текущее состояние предпочтений (из предыдущих сообщений):\n"
            f"{progress_text}\n\n"
            f"Можно начинать поиск: {can_search}\n\n"
            "ВАЖНО: Если пользователь в ТЕКУЩЕМ сообщении упоминает новый город — "
            "ОБЯЗАТЕЛЬНО верни его в поле city. Новый город автоматически заменит текущий. "
            "НЕ игнорируй упоминание города из-за того, что один уже установлен."
        )
    
    def _build_status_list(self, prefs: UserPreferences) -> List[str]:
        status = []
        fields = [
            ("origin_city", "Откуда"),
            ("city", "Место"),
            ("destination_type", "Тип"),
            ("travel_companions", "Компания"),
            ("budget", "Бюджет"),
            ("duration_days", "Дней"),
        ]
        
        for field, label in fields:
            value = getattr(prefs, field)
            if value:
                if field == 'activities':
                    status.append(f"✓ {label}: {', '.join(value)}")
                else:
                    status.append(f"✓ {label}: {value}")
        
        return status
    
    def __call__(self, *args, **kwargs):
        return self.agent(*args, **kwargs)
