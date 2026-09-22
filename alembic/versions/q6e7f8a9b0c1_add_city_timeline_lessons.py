"""add timeline lessons to the city pilots

Revision ID: q6e7f8a9b0c1
Revises: p5d6e7f8a9b0
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "q6e7f8a9b0c1"
down_revision = "p5d6e7f8a9b0"
branch_labels = None
depends_on = None


def _payload(content_id, quest_id, city, title, fact, label, url, question, correct, options, intro, mode, mechanic=None):
    payload = {"id": content_id, "country": {"id": "ru", "name": "Россия", "city": city}, "chris": {"name": "Крис", "intro": intro}, "scene": {"title": title, "mode": mode}, "fact": {"text": fact, "source_label": label, "source_url": url}, "question": {"id": f"{quest_id}-year", "text": question, "options": [{"id": value, "label": value} for value in options], "correct_option_id": correct}, "reward": {"xp": 25, "stamp_key": quest_id, "stamp_title": f"Штамп «{title}»"}}
    if mechanic:
        payload["mechanic"] = mechanic
    return payload


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    content = sa.table("game_content_revision", sa.column("id", sa.String()), sa.column("kind", sa.String()), sa.column("payload", postgresql.JSONB()), sa.column("updated_at", sa.DateTime(timezone=True)))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("kind", sa.String()))
    entries = [
        ("spb-peterhof-v1", "spb-peterhof", "Санкт-Петербург", "Петергоф", "Торжественное открытие Петергофа состоялось 15 августа 1723 года.", "ГМЗ «Петергоф»", "https://en.peterhofmuseum.ru/objects/peterhof", "Выберите год открытия на временной шкале.", "1723", ["1714", "1723", "1762"]),
        ("sochi-dendrarium-v1", "sochi-dendrarium", "Сочи", "Дендрарий", "Основные посадки в сочинском Дендрарии были завершены в 1892 году.", "Сочинский национальный парк", "https://npsochi.ru/working/dendrariy/", "Выберите год завершения основных посадок на временной шкале.", "1892", ["1882", "1892", "1902"]),
    ]
    for entry in entries:
        content_id, quest_id, *_ = entry
        payload = _payload(*entry, intro="Расположите факт на временной шкале.", mode="timeline", mechanic={"type": "timeline", "title": "Временная шкала"})
        op.execute(content.update().where(content.c.id == content_id).values(kind="timeline", payload=payload, updated_at=now))
        op.execute(quest.update().where(quest.c.id == quest_id).values(kind="timeline"))


def downgrade() -> None:
    content = sa.table("game_content_revision", sa.column("id", sa.String()), sa.column("kind", sa.String()), sa.column("payload", postgresql.JSONB()))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("kind", sa.String()))
    entries = [
        ("spb-peterhof-v1", "spb-peterhof", "Санкт-Петербург", "Петергоф", "Торжественное открытие Петергофа состоялось 15 августа 1723 года.", "ГМЗ «Петергоф»", "https://en.peterhofmuseum.ru/objects/peterhof", "В каком году состоялось торжественное открытие Петергофа?", "1723", ["1714", "1723", "1762"]),
        ("sochi-dendrarium-v1", "sochi-dendrarium", "Сочи", "Дендрарий", "Основные посадки в сочинском Дендрарии были завершены в 1892 году.", "Сочинский национальный парк", "https://npsochi.ru/working/dendrariy/", "В каком году завершили основные посадки в сочинском Дендрарии?", "1892", ["1882", "1892", "1902"]),
    ]
    for entry in entries:
        content_id, quest_id, *_ = entry
        payload = _payload(*entry, intro="Следующая точка раскрывает культурный маршрут Петербурга." if quest_id == "spb-peterhof" else "Этот маршрут соединяет природу, субтропики и историю курорта.", mode=quest_id)
        op.execute(content.update().where(content.c.id == content_id).values(kind="fact-quiz", payload=payload))
        op.execute(quest.update().where(quest.c.id == quest_id).values(kind="fact-quiz"))
