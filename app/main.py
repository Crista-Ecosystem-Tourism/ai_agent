import logging
import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import lifespan
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.travel_data import router as travel_data_router


log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Agent API", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", os.getenv("JWT_SECRET", "dev-secret-key-min-32-chars")),
    max_age=3600,
    same_site="lax",
    https_only=False,  # В production поставьте True
)

origins = (os.getenv("CORS_ORIGINS") or "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(travel_data_router)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root():
    return {"message": "Agent API", "docs": "/docs"}
