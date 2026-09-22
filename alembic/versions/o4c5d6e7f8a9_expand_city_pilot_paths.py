"""expand St Petersburg and Sochi pilot paths to five sourced lessons

Revision ID: o4c5d6e7f8a9
Revises: n3b4c5d6e7f8
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "o4c5d6e7f8a9"
down_revision = "n3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    district = sa.table("game_district", sa.column("id", sa.String()), sa.column("city_id", sa.String()), sa.column("name", sa.String()), sa.column("position", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    content = sa.table("game_content_revision", sa.column("id", sa.String()), sa.column("kind", sa.String()), sa.column("payload", postgresql.JSONB()), sa.column("is_published", sa.Boolean()), sa.column("published_at", sa.DateTime(timezone=True)), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("city_id", sa.String()), sa.column("content_revision_id", sa.String()), sa.column("district_id", sa.String()), sa.column("kind", sa.String()), sa.column("position", sa.Integer()), sa.column("prerequisite_quest_id", sa.String()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    op.bulk_insert(district, [
        {"id": "spb-winter-palace", "city_id": "st-petersburg", "name": "Зимний дворец", "position": 3, "created_at": now, "updated_at": now},
        {"id": "spb-fountains", "city_id": "st-petersburg", "name": "Фонтаны Петергофа", "position": 4, "created_at": now, "updated_at": now},
        {"id": "spb-peterhof-history", "city_id": "st-petersburg", "name": "История Петергофа", "position": 5, "created_at": now, "updated_at": now},
        {"id": "sochi-forest", "city_id": "sochi", "name": "Горные леса", "position": 3, "created_at": now, "updated_at": now},
        {"id": "sochi-mzymta", "city_id": "sochi", "name": "Долина Мзымты", "position": 4, "created_at": now, "updated_at": now},
        {"id": "sochi-park-area", "city_id": "sochi", "name": "Масштаб парка", "position": 5, "created_at": now, "updated_at": now},
    ])
    entries = [
        ("spb-collection-v1", "spb-collection", "st-petersburg", "spb-winter-palace", 3, "spb-peterhof", "Коллекция Эрмитажа", "Коллекция Государственного Эрмитажа насчитывает более трёх миллионов произведений искусства и артефактов мировой культуры.", "Государственный Эрмитаж", "https://hermitagemuseum.org/about/facts_and_figures", "Сколько произведений и артефактов включает коллекция Эрмитажа?", "Более 3 млн", ["Около 300 тыс.", "Более 3 млн", "Более 30 млн"]),
        ("spb-fountains-v1", "spb-fountains", "st-petersburg", "spb-fountains", 4, "spb-collection", "Фонтаны Петергофа", "В парках Петергофа расположены четыре каскада и свыше 150 фонтанов.", "ГМЗ «Петергоф»", "https://go.peterhofmuseum.ru/info/fountains/", "Сколько фонтанов находится в парках Петергофа?", "Свыше 150", ["Около 15", "Свыше 150", "Свыше 1 500"]),
        ("spb-peterhof-history-v1", "spb-peterhof-history", "st-petersburg", "spb-peterhof-history", 5, "spb-fountains", "Первое упоминание Петергофа", "Первое документальное упоминание Петергофа в походном журнале Петра I относится к 1705 году.", "ГМЗ «Петергоф»", "https://peterhofmuseum.ru/objects/peterhof", "В каком году впервые документально упомянут Петергоф?", "1705", ["1695", "1705", "1715"]),
        ("sochi-forest-v1", "sochi-forest", "sochi", "sochi-forest", 3, "sochi-dendrarium", "Горные леса", "Горные леса занимают 94,1% площади Сочинского национального парка.", "Сочинский национальный парк", "https://npsochi.ru/about/", "Какая доля площади парка занята горными лесами?", "94,1%", ["49,1%", "74,1%", "94,1%"]),
        ("sochi-mzymta-v1", "sochi-mzymta", "sochi", "sochi-mzymta", 4, "sochi-forest", "Река Мзымта", "Мзымта — самая крупная река на территории парка; её протяжённость составляет 89 км.", "Сочинский национальный парк", "https://npsochi.ru/about/", "Какова протяжённость Мзымты на территории парка?", "89 км", ["29 км", "89 км", "189 км"]),
        ("sochi-park-area-v1", "sochi-park-area", "sochi", "sochi-park-area", 5, "sochi-mzymta", "Площадь национального парка", "Площадь Сочинского национального парка составляет 214 098,6 гектара.", "Сочинский национальный парк", "https://npsochi.ru/about/", "Какова площадь Сочинского национального парка?", "214 098,6 га", ["21 409,86 га", "214 098,6 га", "2 140 986 га"]),
    ]
    op.bulk_insert(content, [{"id": cid, "kind": "fact-quiz", "payload": {"id": cid, "country": {"id": "ru", "name": "Россия", "city": "Санкт-Петербург" if city_id == "st-petersburg" else "Сочи"}, "chris": {"name": "Крис", "intro": "Продолжим маршрут и сверим факт с первоисточником."}, "scene": {"title": title, "mode": qid}, "fact": {"text": fact, "source_label": label, "source_url": url}, "question": {"id": f"{qid}-fact", "text": question, "options": [{"id": value, "label": value} for value in options], "correct_option_id": correct}, "reward": {"xp": 25, "stamp_key": qid, "stamp_title": f"Штамп «{title}»"}}, "is_published": True, "published_at": now, "created_at": now, "updated_at": now} for cid, qid, city_id, _, _, _, title, fact, label, url, question, correct, options in entries])
    op.bulk_insert(quest, [{"id": qid, "city_id": city_id, "content_revision_id": cid, "district_id": district_id, "kind": "fact-quiz", "position": position, "prerequisite_quest_id": prerequisite, "is_published": True, "created_at": now, "updated_at": now} for cid, qid, city_id, district_id, position, prerequisite, *_ in entries])
    op.execute(sa.text("UPDATE game_city SET required_quest_count = 5 WHERE id IN ('st-petersburg', 'sochi')"))


def downgrade() -> None:
    quest_ids = "'spb-collection', 'spb-fountains', 'spb-peterhof-history', 'sochi-forest', 'sochi-mzymta', 'sochi-park-area'"
    revision_ids = "'spb-collection-v1', 'spb-fountains-v1', 'spb-peterhof-history-v1', 'sochi-forest-v1', 'sochi-mzymta-v1', 'sochi-park-area-v1'"
    op.execute(sa.text(f"DELETE FROM game_quest_completion WHERE quest_id IN ({quest_ids})"))
    op.execute(sa.text(f"DELETE FROM game_quest WHERE id IN ({quest_ids})"))
    op.execute(sa.text(f"DELETE FROM game_content_revision WHERE id IN ({revision_ids})"))
    op.execute(sa.text("DELETE FROM game_district WHERE id IN ('spb-winter-palace', 'spb-fountains', 'spb-peterhof-history', 'sochi-forest', 'sochi-mzymta', 'sochi-park-area')"))
    op.execute(sa.text("UPDATE game_city SET required_quest_count = 2 WHERE id IN ('st-petersburg', 'sochi')"))
