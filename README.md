# Crista Agent

AI чат-бот для планирования путешествий. Извлекает предпочтения пользователя, ищет места через RAG (vectorization backend), строит маршруты.

## Зависимости

- Python 3.13+
- PostgreSQL на порту 5544 (Docker-контейнер `user-service-postgres`)
- Vectorization Backend на порту 8001
- PlacesWeb Backend на порту 8003
- Ключ OpenRouter API

## Запуск

```bash
source venv/Scripts/activate          # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head                  # миграции БД (первый запуск)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

## Конфигурация (.env)

```
CORS_ORIGINS=http://localhost:5173,http://localhost:3333
RAG_URL=http://localhost:8001
ROUTE_URL=http://localhost:8003
OPENROUTER_API_KEY=sk-or-v1-...
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5544/crs_agent
NO_PROXY=localhost,127.0.0.1
HTTP_PROXY=
HTTPS_PROXY=
```

## API

- `GET /health` — health check
- `POST /chat/sessions` — создание сессии чата
- `POST /chat/sessions/{id}/messages` — отправка сообщения
- `GET /chat/sessions/{id}/history` — история диалога
- `DELETE /chat/sessions/{id}` — удаление сессии
