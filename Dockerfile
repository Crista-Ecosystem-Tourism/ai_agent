FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    itsdangerous \
    pydantic-ai==1.63.0 \
    sqlalchemy==2.0.47 \
    asyncpg==0.31.0 \
    alembic==1.18.4 \
    httpx==0.28.1 \
    PyJWT==2.11.0 \
    bcrypt==5.0.0 \
    pydantic-settings==2.13.1

COPY . .

EXPOSE 8002

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8002"]
