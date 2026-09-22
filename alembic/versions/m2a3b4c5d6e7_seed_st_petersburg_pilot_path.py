"""seed St Petersburg editorial pilot path

Revision ID: m2a3b4c5d6e7
Revises: l1a2b3c4d5e6
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "m2a3b4c5d6e7"
down_revision = "l1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    region = sa.table("game_region", sa.column("id", sa.String()), sa.column("country_id", sa.String()), sa.column("name", sa.String()), sa.column("position", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    city = sa.table("game_city", sa.column("id", sa.String()), sa.column("region_id", sa.String()), sa.column("name", sa.String()), sa.column("tier", sa.Integer()), sa.column("required_quest_count", sa.Integer()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    district = sa.table("game_district", sa.column("id", sa.String()), sa.column("city_id", sa.String()), sa.column("name", sa.String()), sa.column("position", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    content = sa.table("game_content_revision", sa.column("id", sa.String()), sa.column("kind", sa.String()), sa.column("payload", postgresql.JSONB()), sa.column("is_published", sa.Boolean()), sa.column("published_at", sa.DateTime(timezone=True)), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("city_id", sa.String()), sa.column("content_revision_id", sa.String()), sa.column("district_id", sa.String()), sa.column("kind", sa.String()), sa.column("position", sa.Integer()), sa.column("prerequisite_quest_id", sa.String()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    op.bulk_insert(region, [{"id": "ru-st-petersburg", "country_id": "ru", "name": "Санкт-Петербург", "position": 2, "created_at": now, "updated_at": now}])
    op.bulk_insert(city, [{"id": "st-petersburg", "region_id": "ru-st-petersburg", "name": "Санкт-Петербург", "tier": 2, "required_quest_count": 2, "is_published": True, "created_at": now, "updated_at": now}])
    op.bulk_insert(district, [{"id": "spb-palace-embankment", "city_id": "st-petersburg", "name": "Дворцовая набережная", "position": 1, "created_at": now, "updated_at": now}, {"id": "spb-peterhof", "city_id": "st-petersburg", "name": "Петергоф", "position": 2, "created_at": now, "updated_at": now}])
    entries = [
        ("spb-hermitage-v1", "spb-hermitage", "spb-palace-embankment", 1, None, "Эрмитаж", "Эрмитаж считает 1764 годом основания музея: тогда Екатерина II приобрела коллекцию Иоганна Эрнста Гоцковского.", "Эрмитаж", "https://hermitagemuseum.org/about/facts_and_figures", "В каком году был основан Эрмитаж?", "1764", ["1703", "1764", "1917"]),
        ("spb-peterhof-v1", "spb-peterhof", "spb-peterhof", 2, "spb-hermitage", "Петергоф", "Торжественное открытие Петергофа состоялось 15 августа 1723 года.", "ГМЗ «Петергоф»", "https://en.peterhofmuseum.ru/objects/peterhof", "В каком году состоялось торжественное открытие Петергофа?", "1723", ["1714", "1723", "1762"]),
    ]
    op.bulk_insert(content, [{"id": cid, "kind": "fact-quiz", "payload": {"id": cid, "country": {"id": "ru", "name": "Россия", "city": "Санкт-Петербург"}, "chris": {"name": "Крис", "intro": "Следующая точка раскрывает культурный маршрут Петербурга."}, "scene": {"title": title, "mode": qid}, "fact": {"text": fact, "source_label": label, "source_url": url}, "question": {"id": f"{qid}-year", "text": question, "options": [{"id": value, "label": value} for value in options], "correct_option_id": correct}, "reward": {"xp": 25, "stamp_key": qid, "stamp_title": f"Штамп «{title}»"}}, "is_published": True, "published_at": now, "created_at": now, "updated_at": now} for cid, qid, _, _, _, title, fact, label, url, question, correct, options in entries])
    op.bulk_insert(quest, [{"id": qid, "city_id": "st-petersburg", "content_revision_id": cid, "district_id": district_id, "kind": "fact-quiz", "position": position, "prerequisite_quest_id": prerequisite, "is_published": True, "created_at": now, "updated_at": now} for cid, qid, district_id, position, prerequisite, *_ in entries])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_quest_completion WHERE quest_id IN ('spb-hermitage', 'spb-peterhof')"))
    op.execute(sa.text("DELETE FROM game_quest WHERE id IN ('spb-hermitage', 'spb-peterhof')"))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id IN ('spb-hermitage-v1', 'spb-peterhof-v1')"))
    op.execute(sa.text("DELETE FROM game_district WHERE city_id = 'st-petersburg'"))
    op.execute(sa.text("DELETE FROM game_city WHERE id = 'st-petersburg'"))
    op.execute(sa.text("DELETE FROM game_region WHERE id = 'ru-st-petersburg'"))
