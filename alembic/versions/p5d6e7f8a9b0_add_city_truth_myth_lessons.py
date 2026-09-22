"""add truth-or-myth lessons to the city pilots

Revision ID: p5d6e7f8a9b0
Revises: o4c5d6e7f8a9
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "p5d6e7f8a9b0"
down_revision = "o4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    content = sa.table("game_content_revision", sa.column("id", sa.String()), sa.column("kind", sa.String()), sa.column("payload", postgresql.JSONB()), sa.column("updated_at", sa.DateTime(timezone=True)))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("kind", sa.String()))
    entries = [
        ("spb-peterhof-history-v1", "spb-peterhof-history", "Санкт-Петербург", "Первое упоминание Петергофа", "Первое документальное упоминание Петергофа в походном журнале Петра I относится к 1705 году.", "ГМЗ «Петергоф»", "https://peterhofmuseum.ru/objects/peterhof", "Верно ли, что первое документальное упоминание Петергофа относится к 1705 году?", "fact", "Факт", "Миф"),
        ("sochi-park-area-v1", "sochi-park-area", "Сочи", "Площадь национального парка", "Площадь Сочинского национального парка составляет 214 098,6 гектара.", "Сочинский национальный парк", "https://npsochi.ru/about/", "Верно ли, что площадь Сочинского национального парка составляет 214 098,6 гектара?", "fact", "Факт", "Миф"),
    ]
    for content_id, quest_id, city, title, fact, label, url, question, correct, truth, myth in entries:
        payload = {
            "id": content_id,
            "country": {"id": "ru", "name": "Россия", "city": city},
            "chris": {"name": "Крис", "intro": "Проверь утверждение по первоисточнику."},
            "scene": {"title": title, "mode": "truth-myth"},
            "fact": {"text": fact, "source_label": label, "source_url": url},
            "mechanic": {"type": "truth-myth", "title": "Правда или миф"},
            "question": {"id": f"{quest_id}-truth", "text": question, "options": [{"id": "fact", "label": truth}, {"id": "myth", "label": myth}], "correct_option_id": correct},
            "reward": {"xp": 25, "stamp_key": quest_id, "stamp_title": f"Штамп «{title}»"},
        }
        op.execute(content.update().where(content.c.id == content_id).values(kind="truth-myth", payload=payload, updated_at=now))
        op.execute(quest.update().where(quest.c.id == quest_id).values(kind="truth-myth"))


def downgrade() -> None:
    content = sa.table("game_content_revision", sa.column("id", sa.String()), sa.column("kind", sa.String()), sa.column("payload", postgresql.JSONB()))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("kind", sa.String()))
    entries = [
        ("spb-peterhof-history-v1", "spb-peterhof-history", "Санкт-Петербург", "Первое упоминание Петергофа", "Первое документальное упоминание Петергофа в походном журнале Петра I относится к 1705 году.", "ГМЗ «Петергоф»", "https://peterhofmuseum.ru/objects/peterhof", "В каком году впервые документально упомянут Петергоф?", "1705", ["1695", "1705", "1715"]),
        ("sochi-park-area-v1", "sochi-park-area", "Сочи", "Площадь национального парка", "Площадь Сочинского национального парка составляет 214 098,6 гектара.", "Сочинский национальный парк", "https://npsochi.ru/about/", "Какова площадь Сочинского национального парка?", "214 098,6 га", ["21 409,86 га", "214 098,6 га", "2 140 986 га"]),
    ]
    for content_id, quest_id, city, title, fact, label, url, question, correct, options in entries:
        payload = {"id": content_id, "country": {"id": "ru", "name": "Россия", "city": city}, "chris": {"name": "Крис", "intro": "Продолжим маршрут и сверим факт с первоисточником."}, "scene": {"title": title, "mode": quest_id}, "fact": {"text": fact, "source_label": label, "source_url": url}, "question": {"id": f"{quest_id}-fact", "text": question, "options": [{"id": value, "label": value} for value in options], "correct_option_id": correct}, "reward": {"xp": 25, "stamp_key": quest_id, "stamp_title": f"Штамп «{title}»"}}
        op.execute(content.update().where(content.c.id == content_id).values(kind="fact-quiz", payload=payload))
        op.execute(quest.update().where(quest.c.id == quest_id).values(kind="fact-quiz"))
