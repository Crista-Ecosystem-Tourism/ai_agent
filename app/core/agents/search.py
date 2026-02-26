from pydantic_ai import Agent, RunContext

from app.core.models import TravelDeps
from app.core.prompts.search import SYSTEM_PROMPT


class SearchAgent:
    
    def __init__(self, model, deps_type=TravelDeps):
        self.agent = Agent(
            model=model,
            deps_type=deps_type,
            system_prompt=self._get_base_system_prompt()
        )
        self._register_tools()
        self._register_prompts()
    
    def _get_base_system_prompt(self) -> str:
        if SYSTEM_PROMPT:
            return SYSTEM_PROMPT
        return """
        Ты эксперт по подбору мест для отдыха.
        
        Твоя задача:
        1. Проанализировать результаты поиска из RAG
        2. Выбрать наиболее подходящие места на основе предпочтений
        3. Представить их пользователю в удобном формате с описанием
        4. Дать персонализированные рекомендации
        
        Формат ответа:
        - Краткое вступление
        - Список из 3-5 лучших мест с описанием
        - Каждое место: название, краткое описание, почему подходит
        
        Будь конкретным и полезным.
        """
    
    def _register_tools(self):        
        @self.agent.tool
        async def search_places(
            ctx: RunContext[TravelDeps],
            query: str,
        ) -> list[str]:
            try:
                response = await ctx.deps.http_client.post(
                    f"{ctx.deps.rag_service_url}/api/v1/search",
                    json={
                        "query": query,
                        "top_k": 10
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                places = response.json().get("results", [])
                
                results = []
                for result in places:
                    content = result.get("data", {}).get("page_content", "")
                    if content:
                        results.append(content)
                
                print(f"Найдено результатов: {len(results)}")
                return results
                
            except Exception as e:
                print(f"Ошибка поиска в RAG: {e}")
                return []
    
    def _register_prompts(self):
        @self.agent.system_prompt
        def add_user_context(ctx: RunContext[TravelDeps]) -> str:
            p = ctx.deps.user_preferences
            
            context = "Предпочтения пользователя:\n"
            if p.city:
                context += f"- Город: {p.city}\n"
            if p.destination_type:
                context += f"- Тип отдыха: {p.destination_type}\n"
            if p.travel_companions:
                context += f"- Компания: {p.travel_companions}\n"
            if p.budget:
                context += f"- Бюджет: {p.budget}\n"
            if p.activities:
                context += f"- Активности: {', '.join(p.activities)}\n"
            if p.duration_days:
                context += f"- Длительность: {p.duration_days} дней\n"
            
            return context
    
    def __call__(self, *args, **kwargs):
        return self.agent(*args, **kwargs)
    
    @property
    def tools(self):
        return self.agent.tools
    
    @property
    def system_prompts(self):
        return self.agent.system_prompts
