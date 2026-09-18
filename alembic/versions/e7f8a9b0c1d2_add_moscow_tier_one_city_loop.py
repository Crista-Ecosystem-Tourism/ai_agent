"""add the tier-one Moscow city loop

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-09-18
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_city",
        sa.Column("required_quest_count", sa.Integer(), nullable=False, server_default="2"),
    )
    op.add_column("game_city", sa.Column("completion_stamp_key", sa.String(), nullable=True))
    op.add_column("game_city", sa.Column("completion_stamp_title", sa.String(), nullable=True))
    op.create_table(
        "game_district",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("city_id", sa.String(), sa.ForeignKey("game_city.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("city_id", "position", name="uq_game_district_city_position"),
    )
    op.add_column("game_quest", sa.Column("district_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_game_quest_district", "game_quest", "game_district", ["district_id"], ["id"],
    )

    now = datetime.now(timezone.utc)
    district = sa.table(
        "game_district",
        sa.column("id", sa.String()),
        sa.column("city_id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("position", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    content = sa.table(
        "game_content_revision",
        sa.column("id", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("payload", postgresql.JSONB()),
        sa.column("is_published", sa.Boolean()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    quest = sa.table(
        "game_quest",
        sa.column("id", sa.String()),
        sa.column("city_id", sa.String()),
        sa.column("content_revision_id", sa.String()),
        sa.column("district_id", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("position", sa.Integer()),
        sa.column("prerequisite_quest_id", sa.String()),
        sa.column("is_published", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(district, [
        {"id": "moscow-kremlin", "city_id": "moscow", "name": "Кремль и Красная площадь", "position": 1, "created_at": now, "updated_at": now},
        {"id": "moscow-kitaigorod", "city_id": "moscow", "name": "Китай-город и Зарядье", "position": 2, "created_at": now, "updated_at": now},
        {"id": "moscow-zamoskvorechye", "city_id": "moscow", "name": "Замоскворечье", "position": 3, "created_at": now, "updated_at": now},
        {"id": "moscow-teatralny", "city_id": "moscow", "name": "Театральный центр", "position": 4, "created_at": now, "updated_at": now},
        {"id": "moscow-vdnh", "city_id": "moscow", "name": "ВДНХ", "position": 5, "created_at": now, "updated_at": now},
    ])
    op.execute(sa.text("""
        UPDATE game_city
        SET required_quest_count = 10,
            completion_stamp_key = 'moscow-city-explorer',
            completion_stamp_title = 'Штамп «Москва: городской круг»'
        WHERE id = 'moscow'
    """))
    op.execute(sa.text("""
        UPDATE game_quest
        SET district_id = 'moscow-kremlin'
        WHERE id IN ('moscow-red-square', 'moscow-spasskaya-tower', 'moscow-tsar-bell')
    """))

    entries = [
        {
            "content_id": "moscow-annunciation-cathedral-v1",
            "quest_id": "moscow-annunciation-cathedral",
            "district_id": "moscow-kremlin",
            "position": 4,
            "prerequisite": "moscow-tsar-bell",
            "title": "Благовещенский собор",
            "intro": "На Соборной площади сохранился памятник русской архитектурной традиции времени Ивана III.",
            "fact": "Благовещенский собор построили в 1484–1489 годах и освятили в 1489 году.",
            "source_label": "Музеи Московского Кремля",
            "source_url": "https://annunciation-cathedral.kreml.ru/history/view/",
            "question_id": "annunciation-year",
            "question": "В каком году освятили Благовещенский собор?",
            "options": [("1489", "1489"), ("1561", "1561"), ("1613", "1613")],
            "correct": "1489",
            "stamp_key": "moscow-annunciation-cathedral",
            "stamp_title": "Штамп «Благовещенский собор»",
        },
        {
            "content_id": "moscow-gum-v1",
            "quest_id": "moscow-gum",
            "district_id": "moscow-kitaigorod",
            "position": 5,
            "prerequisite": "moscow-annunciation-cathedral",
            "title": "ГУМ",
            "intro": "От кремлёвских стен путь ведёт к историческим торговым рядам у Красной площади.",
            "fact": "Верхние торговые ряды, будущий ГУМ, открылись 2 декабря 1893 года.",
            "source_label": "ГУМ",
            "source_url": "https://gum.ru/history/",
            "question_id": "gum-opening-year",
            "question": "В каком году открылись Верхние торговые ряды?",
            "options": [("1825", "1825"), ("1893", "1893"), ("1939", "1939")],
            "correct": "1893",
            "stamp_key": "moscow-gum",
            "stamp_title": "Штамп «ГУМ»",
        },
        {
            "content_id": "moscow-zaryadye-v1",
            "quest_id": "moscow-zaryadye",
            "district_id": "moscow-kitaigorod",
            "position": 6,
            "prerequisite": "moscow-gum",
            "title": "Парк «Зарядье»",
            "intro": "За торговыми рядами Москва соединяет исторический центр с современным ландшафтным парком.",
            "fact": "Ландшафтный парк «Зарядье» у стен Кремля открылся в 2017 году.",
            "source_label": "Комплекс градостроительной политики Москвы",
            "source_url": "https://stroi.mos.ru/park-zariad-ie",
            "question_id": "zaryadye-opening-year",
            "question": "В каком году открылся парк «Зарядье»?",
            "options": [("1997", "1997"), ("2012", "2012"), ("2017", "2017")],
            "correct": "2017",
            "stamp_key": "moscow-zaryadye",
            "stamp_title": "Штамп «Зарядье»",
        },
        {
            "content_id": "moscow-tretyakov-gallery-v1",
            "quest_id": "moscow-tretyakov-gallery",
            "district_id": "moscow-zamoskvorechye",
            "position": 7,
            "prerequisite": "moscow-zaryadye",
            "title": "Третьяковская галерея",
            "intro": "Через реку начинается купеческое Замоскворечье и история национальной художественной коллекции.",
            "fact": "Годом основания Третьяковской галереи считают 1856-й: тогда Павел Третьяков приобрёл первую картину русского художника.",
            "source_label": "Третьяковская галерея",
            "source_url": "https://www.tretyakovgallery.ru/about/history/",
            "question_id": "tretyakov-founded-year",
            "question": "Какой год считают годом основания Третьяковской галереи?",
            "options": [("1812", "1812"), ("1856", "1856"), ("1918", "1918")],
            "correct": "1856",
            "stamp_key": "moscow-tretyakov-gallery",
            "stamp_title": "Штамп «Третьяковская галерея»",
        },
        {
            "content_id": "moscow-bolshoi-theatre-v1",
            "quest_id": "moscow-bolshoi-theatre",
            "district_id": "moscow-teatralny",
            "position": 8,
            "prerequisite": "moscow-tretyakov-gallery",
            "title": "Большой театр",
            "intro": "На Театральной площади маршрут переходит от частной коллекции к главной сцене города.",
            "fact": "Большой театр открылся в 1825 году после перепланировки Театральной площади.",
            "source_label": "Узнай Москву",
            "source_url": "https://um.mos.ru/periods/moskva-pri-aleksandre-i-/",
            "question_id": "bolshoi-opening-year",
            "question": "В каком году открылся Большой театр?",
            "options": [("1780", "1780"), ("1825", "1825"), ("1853", "1853")],
            "correct": "1825",
            "stamp_key": "moscow-bolshoi-theatre",
            "stamp_title": "Штамп «Большой театр»",
        },
        {
            "content_id": "moscow-metro-v1",
            "quest_id": "moscow-metro",
            "district_id": "moscow-teatralny",
            "position": 9,
            "prerequisite": "moscow-bolshoi-theatre",
            "title": "Московское метро",
            "intro": "Дальше город раскрывается под землёй: первая линия связала центр с новыми районами.",
            "fact": "Первая очередь Московского метрополитена открылась 15 мая 1935 года.",
            "source_label": "Московский метрополитен",
            "source_url": "https://mosmetro.ru/about/history",
            "question_id": "metro-opening-year",
            "question": "В каком году открылась первая очередь Московского метро?",
            "options": [("1917", "1917"), ("1935", "1935"), ("1954", "1954")],
            "correct": "1935",
            "stamp_key": "moscow-metro",
            "stamp_title": "Штамп «Московское метро»",
        },
        {
            "content_id": "moscow-vdnh-v1",
            "quest_id": "moscow-vdnh",
            "district_id": "moscow-vdnh",
            "position": 10,
            "prerequisite": "moscow-metro",
            "title": "ВДНХ",
            "intro": "Финальная точка основного круга выводит к выставочному городу на северо-востоке Москвы.",
            "fact": "Всесоюзная сельскохозяйственная выставка, с которой началась история ВДНХ, открылась 1 августа 1939 года.",
            "source_label": "ВДНХ",
            "source_url": "https://vdnh.ru/visitors/about/",
            "question_id": "vdnh-opening-year",
            "question": "В каком году открылась первая выставка на территории ВДНХ?",
            "options": [("1923", "1923"), ("1939", "1939"), ("1959", "1959")],
            "correct": "1939",
            "stamp_key": "moscow-vdnh",
            "stamp_title": "Штамп «ВДНХ»",
        },
    ]

    op.bulk_insert(content, [
        {
            "id": entry["content_id"], "kind": "fact-quiz",
            "payload": {
                "id": entry["content_id"],
                "country": {"id": "ru", "name": "Россия", "city": "Москва"},
                "chris": {"name": "Крис", "intro": entry["intro"]},
                "scene": {"title": entry["title"], "mode": entry["quest_id"]},
                "fact": {"text": entry["fact"], "source_label": entry["source_label"], "source_url": entry["source_url"]},
                "question": {
                    "id": entry["question_id"], "text": entry["question"],
                    "options": [{"id": option_id, "label": label} for option_id, label in entry["options"]],
                    "correct_option_id": entry["correct"],
                },
                "reward": {"xp": 25, "stamp_key": entry["stamp_key"], "stamp_title": entry["stamp_title"]},
            },
            "is_published": True, "published_at": now, "created_at": now, "updated_at": now,
        }
        for entry in entries
    ])
    op.bulk_insert(quest, [
        {
            "id": entry["quest_id"], "city_id": "moscow", "content_revision_id": entry["content_id"],
            "district_id": entry["district_id"], "kind": "fact-quiz", "position": entry["position"],
            "prerequisite_quest_id": entry["prerequisite"], "is_published": True,
            "created_at": now, "updated_at": now,
        }
        for entry in entries
    ])


def downgrade() -> None:
    quest_ids = "'moscow-annunciation-cathedral', 'moscow-gum', 'moscow-zaryadye', 'moscow-tretyakov-gallery', 'moscow-bolshoi-theatre', 'moscow-metro', 'moscow-vdnh'"
    content_ids = "'moscow-annunciation-cathedral-v1', 'moscow-gum-v1', 'moscow-zaryadye-v1', 'moscow-tretyakov-gallery-v1', 'moscow-bolshoi-theatre-v1', 'moscow-metro-v1', 'moscow-vdnh-v1'"
    op.execute(sa.text(f"DELETE FROM game_quest_completion WHERE quest_id IN ({quest_ids})"))
    op.execute(sa.text(f"DELETE FROM game_reward_ledger WHERE quest_id IN ({quest_ids})"))
    op.execute(sa.text(f"DELETE FROM game_stamp WHERE content_revision_id IN ({content_ids})"))
    op.execute(sa.text(f"DELETE FROM game_attempt WHERE content_revision_id IN ({content_ids})"))
    op.execute(sa.text(f"DELETE FROM game_quest WHERE id IN ({quest_ids})"))
    op.execute(sa.text(f"DELETE FROM game_content_revision WHERE id IN ({content_ids})"))
    op.execute(sa.text("UPDATE game_quest SET district_id = NULL WHERE city_id = 'moscow'"))
    op.drop_constraint("fk_game_quest_district", "game_quest", type_="foreignkey")
    op.drop_column("game_quest", "district_id")
    op.drop_table("game_district")
    op.drop_column("game_city", "completion_stamp_title")
    op.drop_column("game_city", "completion_stamp_key")
    op.drop_column("game_city", "required_quest_count")
