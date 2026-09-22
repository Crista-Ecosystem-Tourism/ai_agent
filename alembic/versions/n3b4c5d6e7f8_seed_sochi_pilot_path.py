"""seed Sochi nature pilot path

Revision ID: n3b4c5d6e7f8
Revises: m2a3b4c5d6e7
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "n3b4c5d6e7f8"
down_revision = "m2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    region = sa.table("game_region", sa.column("id", sa.String()), sa.column("country_id", sa.String()), sa.column("name", sa.String()), sa.column("position", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    city = sa.table("game_city", sa.column("id", sa.String()), sa.column("region_id", sa.String()), sa.column("name", sa.String()), sa.column("tier", sa.Integer()), sa.column("required_quest_count", sa.Integer()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    district = sa.table("game_district", sa.column("id", sa.String()), sa.column("city_id", sa.String()), sa.column("name", sa.String()), sa.column("position", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    content = sa.table("game_content_revision", sa.column("id", sa.String()), sa.column("kind", sa.String()), sa.column("payload", postgresql.JSONB()), sa.column("is_published", sa.Boolean()), sa.column("published_at", sa.DateTime(timezone=True)), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("city_id", sa.String()), sa.column("content_revision_id", sa.String()), sa.column("district_id", sa.String()), sa.column("kind", sa.String()), sa.column("position", sa.Integer()), sa.column("prerequisite_quest_id", sa.String()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    op.bulk_insert(region, [{"id": "ru-sochi", "country_id": "ru", "name": "Сочи", "position": 3, "created_at": now, "updated_at": now}])
    op.bulk_insert(city, [{"id": "sochi", "region_id": "ru-sochi", "name": "Сочи", "tier": 3, "required_quest_count": 2, "is_published": True, "created_at": now, "updated_at": now}])
    op.bulk_insert(district, [{"id": "sochi-national-park", "city_id": "sochi", "name": "Сочинский национальный парк", "position": 1, "created_at": now, "updated_at": now}, {"id": "sochi-dendrarium", "city_id": "sochi", "name": "Дендрарий", "position": 2, "created_at": now, "updated_at": now}])
    entries = [("sochi-national-park-v1", "sochi-national-park", "sochi-national-park", 1, None, "Сочинский национальный парк", "Сочинский национальный парк основан 5 мая 1983 года и стал первым национальным парком России.", "Сочинский национальный парк", "https://npsochi.ru/about/", "В каком году был основан Сочинский национальный парк?", "1983", ["1973", "1983", "1993"]), ("sochi-dendrarium-v1", "sochi-dendrarium", "sochi-dendrarium", 2, "sochi-national-park", "Дендрарий", "Основные посадки в сочинском Дендрарии были завершены в 1892 году.", "Сочинский национальный парк", "https://npsochi.ru/working/dendrariy/", "В каком году завершили основные посадки в сочинском Дендрарии?", "1892", ["1882", "1892", "1902"])]
    op.bulk_insert(content, [{"id": cid, "kind": "fact-quiz", "payload": {"id": cid, "country": {"id": "ru", "name": "Россия", "city": "Сочи"}, "chris": {"name": "Крис", "intro": "Этот маршрут соединяет природу, субтропики и историю курорта."}, "scene": {"title": title, "mode": qid}, "fact": {"text": fact, "source_label": label, "source_url": url}, "question": {"id": f"{qid}-year", "text": question, "options": [{"id": value, "label": value} for value in options], "correct_option_id": correct}, "reward": {"xp": 25, "stamp_key": qid, "stamp_title": f"Штамп «{title}»"}}, "is_published": True, "published_at": now, "created_at": now, "updated_at": now} for cid, qid, _, _, _, title, fact, label, url, question, correct, options in entries])
    op.bulk_insert(quest, [{"id": qid, "city_id": "sochi", "content_revision_id": cid, "district_id": district_id, "kind": "fact-quiz", "position": position, "prerequisite_quest_id": prerequisite, "is_published": True, "created_at": now, "updated_at": now} for cid, qid, district_id, position, prerequisite, *_ in entries])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_quest_completion WHERE quest_id IN ('sochi-national-park', 'sochi-dendrarium')"))
    op.execute(sa.text("DELETE FROM game_quest WHERE id IN ('sochi-national-park', 'sochi-dendrarium')"))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id IN ('sochi-national-park-v1', 'sochi-dendrarium-v1')"))
    op.execute(sa.text("DELETE FROM game_district WHERE city_id = 'sochi'"))
    op.execute(sa.text("DELETE FROM game_city WHERE id = 'sochi'"))
    op.execute(sa.text("DELETE FROM game_region WHERE id = 'ru-sochi'"))
