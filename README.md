# Crista — AI Agent

Backend чата: **FastAPI**, **pydantic-ai**, **OpenRouter**, RAG (vectorization), маршруты (placesweb), **PostgreSQL**, **Alembic**, JWT.

## Роль

Сессии чата, LLM, вызовы RAG/графа, регистрация/логин. Внутри Docker `RAG_URL` / `ROUTE_URL` — **имена** **сервисов** `vectorization`, `placesweb`.

## Локально

```bash
cd ai_agent
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Нужен **`.env`**: `OPENROUTER_API_KEY`, `DATABASE_URL`, `RAG_URL`, `ROUTE_URL`, `CORS_ORIGINS` — примеры в [главной документации](https://raw.githubusercontent.com/Crista-Ecosystem-Tourism/crs/main/README.md) (см. репо **crs**).

## CI/CD

Синк в [crs/ai_agent](https://github.com/Crista-Ecosystem-Tourism/crs): [инструкция](https://github.com/Crista-Ecosystem-Tourism/crs/blob/main/docs/CI-CD-SYNC.md), секрет `CRS_SYNC_PAT`.

## Полная документация

[README `crs`](https://github.com/Crista-Ecosystem-Tourism/crs#readme) · [орг](https://github.com/Crista-Ecosystem-Tourism)
