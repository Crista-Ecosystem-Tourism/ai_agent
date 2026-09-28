"""publish English editions of the remaining country Wiki pages

Revision ID: b30b1c2d3e4
Revises: b20b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b30b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "b20b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LICENSE = "CC BY 4.0"
EDITIONS = [
    {
        "country": "be", "title": "Belgium",
        "body": {
            "summary": "Belgium brings together several linguistic and regional traditions; Brussels and Bruges in the Crista catalogue offer different ways into this history.",
            "history": "Brussels' Grand-Place began as a market square in the twelfth century. Its Gothic Town Hall was built in the fifteenth century, and the surrounding houses are associated with the city's guilds. After the bombardment of 1695, the square was almost completely rebuilt; UNESCO describes the ensemble as an important political and commercial centre reflected in late-seventeenth-century architecture.",
            "cuisine": "Brussels has its own culinary features: the Brussels waffle is light, rectangular and usually unsweetened, with toppings added when it is served. Visit Brussels also associates the city with chocolate, beer, speculoos and other Belgian specialities. Recipes and customs vary between regions.",
            "traditions": "Belgium has three national languages: Dutch, French and German. The language of signs and everyday communication depends on the region; in Brussels, it helps to pay attention to the language used in signs and service information.",
            "practical": [
                {"label": "Currency", "value": "Euro (EUR)"},
                {"label": "Emergency assistance", "value": "112 · fire service, ambulance and police; 101 · urgent police assistance"},
            ],
        },
        "sources": [
            {"label": "Visit Brussels: history of the Grand-Place", "url": "https://www.visit.brussels/en/visitors/plan-your-trip/a-legendary-stay-for-history-buffs/day-1-exploring-the-historical-centre"},
            {"label": "UNESCO: Grand-Place, Brussels", "url": "https://whc.unesco.org/en/list/857"},
            {"label": "Visit Brussels: city culinary traditions", "url": "https://www.visit.brussels/en/visitors/where-to-eat/bruxelles-et-ses-specialites-culinaires"},
            {"label": "Belgium.be: Belgium at a glance", "url": "https://www.belgium.be/fr/la_belgique/connaitre_le_pays/la_belgique_en_bref/fiche_belgique"},
            {"label": "112 Belgium: how to call for help", "url": "https://112.be/en/how-call/how-call-112"},
        ],
    },
    {
        "country": "it", "title": "Italy",
        "body": {
            "summary": "Italy brings together diverse regional cultures. Its history, art and food are best understood through the context of a particular city or region.",
            "history": "Italy's cultural map includes the archaeological sites of Rome and Pompeii, art cities, historic settlements and UNESCO sites. These layers do not belong to a single period: each place is best approached through its own history and local sources.",
            "cuisine": "Italian cuisine is shaped by regional diversity: regions, cities and families have their own versions of recipes. The official tourism portal links this diversity to distinct landscapes, a long cultural history and local products.",
            "traditions": "Customs, crafts and celebrations differ between regions. A respectful way to encounter a local tradition is to ask the venue or organiser about its practices and avoid treating one city experience as universal for the whole country.",
            "practical": [
                {"label": "Currency", "value": "Euro (EUR)"},
                {"label": "Emergency assistance", "value": "112 · single emergency number"},
            ],
        },
        "sources": [
            {"label": "Italia.it: art and culture in Italy", "url": "https://www.italia.it/en/italy/things-to-do/art-culture"},
            {"label": "Italia.it: Italian cuisine and regional traditions", "url": "https://www.italia.it/en/italy/things-to-do/italian-cuisine-unesco-heritage"},
            {"label": "European Commission: Italy and the euro", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/italy-and-euro_en"},
            {"label": "Italian Government: single emergency number 112", "url": "https://www.affarieuropei.gov.it/media/3289/scarica-la-brochure-sul-112.pdf"},
        ],
    },
    {
        "country": "fr", "title": "France",
        "body": {
            "summary": "France brings together diverse regional cultural and natural settings. Understanding a particular city or territory helps avoid reducing the country to a single image.",
            "history": "France's UNESCO World Heritage list includes cultural, natural and mixed properties, from archaeological and medieval monuments to urban ensembles and landscapes. Each place has its own history, so the page encourages readers to start with its specific sources and context.",
            "cuisine": "The gastronomic meal of the French is inscribed on UNESCO's Representative List of the Intangible Cultural Heritage of Humanity. It is a social practice for important occasions that values togetherness, selecting products, pairing dishes and setting the table. Regional recipes and customs still vary.",
            "traditions": "Local practices and daily rhythms depend on the region and situation. In a cafe, on a tour or at a city event, follow the organiser's information and ask about the rules on site.",
            "practical": [
                {"label": "Currency", "value": "Euro (EUR)"},
                {"label": "Emergency assistance", "value": "112 · European emergency number"},
            ],
        },
        "sources": [
            {"label": "UNESCO: France World Heritage properties", "url": "https://whc.unesco.org/en/statesparties/fr"},
            {"label": "UNESCO: gastronomic meal of the French", "url": "https://ich.unesco.org/en/lists?RL=00437"},
            {"label": "European Commission: France and the euro", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/france-and-euro_en"},
            {"label": "Service-Public.fr: emergency numbers", "url": "https://lannuaire.service-public.fr/?lang=fr"},
        ],
    },
    {
        "country": "es", "title": "Spain",
        "body": {
            "summary": "Spain brings together diverse regional cultural and natural settings. Getting to know a particular territory helps reveal that diversity without oversimplifying it.",
            "history": "Spain's UNESCO World Heritage list includes cultural, natural and mixed properties: archaeological ensembles, historic cities, architectural complexes and national parks. The context of a particular place matters more than a general template for the country.",
            "cuisine": "Spanish food differs between regions and draws on local ingredients and traditions. When trying a dish, ask the venue or organiser about its region of origin and how it is served.",
            "traditions": "Flamenco is inscribed on UNESCO's Representative List of the Intangible Cultural Heritage of Humanity. It is an artistic expression that combines singing, dance and guitar accompaniment; its heartland is Andalusia, while the tradition also has links with other regions. Flamenco is one living practice, not a universal description of the whole country.",
            "practical": [
                {"label": "Currency", "value": "Euro (EUR)"},
                {"label": "Emergency assistance", "value": "112 · single emergency number"},
            ],
        },
        "sources": [
            {"label": "UNESCO: Spain World Heritage properties", "url": "https://whc.unesco.org/en/statesparties/es"},
            {"label": "UNESCO: flamenco", "url": "https://ich.unesco.org/es/RL/el-flamenco-00363"},
            {"label": "European Commission: Spain and the euro", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/spain-and-euro_en"},
            {"label": "112 Spain: single emergency number", "url": "https://www.112.es/"},
        ],
    },
    {
        "country": "th", "title": "Thailand",
        "body": {
            "summary": "Thailand combines historic cities, natural areas and living cultural practices. A place's regional and local context matters for understanding it well.",
            "history": "Thailand's UNESCO World Heritage list includes cultural and natural properties: the historic cities of Ayutthaya and Sukhothai, archaeological monuments and protected forest complexes. Each belongs to a different period and conservation setting, so the country does not follow a single historical line.",
            "cuisine": "Culinary traditions differ between regions. UNESCO lists tom yum kung as an element of Thailand's intangible cultural heritage; it is one example of a living practice and does not stand in for the variety of local cuisines.",
            "traditions": "Khon is Thailand's masked dance drama and is inscribed on UNESCO's Representative List. It brings together music, vocal performance, literature, dance, ritual and craft; today it is passed on through educational institutions and performing arts clubs as well as traditional methods.",
            "practical": [
                {"label": "Currency", "value": "Thai baht (THB)"},
                {"label": "Tourist police", "value": "1155 · assistance for tourists"},
            ],
        },
        "sources": [
            {"label": "UNESCO: Thailand World Heritage properties", "url": "https://whc.unesco.org/en/statesparties/th"},
            {"label": "UNESCO: Thailand intangible heritage", "url": "https://ich.unesco.org/en/state/thailand-TH"},
            {"label": "UNESCO: Khon masked dance drama", "url": "https://ich.unesco.org/en/RL/khon-masked-dance-drama-in-thailand-01385"},
            {"label": "Bank of Thailand: currency unit", "url": "https://www.bot.or.th/content/dam/bot/documents/en/laws-and-rules/laws-and-regulations/legal-department/2-currency-act/2.1%20LAW02_CurrencyAct.pdf"},
            {"label": "Tourism Authority of Thailand: tourist police", "url": "https://www.tourismthailand.org/Articles/tourist-police-app-en"},
        ],
    },
    {
        "country": "ae", "title": "United Arab Emirates",
        "body": {
            "summary": "The United Arab Emirates brings together oasis heritage, archaeological landscapes and modern cities. Respectful exploration requires attention to the local context and the rules of the relevant emirate or venue.",
            "history": "The UAE's UNESCO World Heritage list includes the Cultural Sites of Al Ain, the Faya Palaeolandscape and Wadi Wurayah. They show different layers of the country's history and natural heritage; each site has its own visiting and conservation rules.",
            "cuisine": "Food and hospitality practices have regional contexts. UNESCO's intangible heritage lists for the UAE include the harees dish; it is one living food practice and does not stand in for the diversity of local traditions.",
            "traditions": "Al-Ayyala is a shared traditional performing art of the UAE and Oman, inscribed on UNESCO's Representative List. It combines chanted poetry, drums and dance, and is performed at weddings and other celebratory occasions.",
            "practical": [
                {"label": "Currency", "value": "UAE dirham (AED)"},
                {"label": "Emergency assistance", "value": "999 · police; 998 · ambulance; 997 · fire service"},
            ],
        },
        "sources": [
            {"label": "UNESCO: UAE World Heritage properties", "url": "https://whc.unesco.org/en/statesparties/ae"},
            {"label": "UNESCO: UAE intangible heritage", "url": "https://ich.unesco.org/en/state/united-arab-emirates-AE?info=elements-on-the-lists"},
            {"label": "UNESCO: Al-Ayyala", "url": "https://ich.unesco.org/en/RL/al-ayyala-a-traditional-performing-art-of-the-sultanate-of-oman-and-the-united-arab-emirates-01012?RL=01012"},
            {"label": "Central Bank of the UAE: currency unit", "url": "https://rulebook.centralbank.ae/en/rulebook/article-52-currency-unit"},
            {"label": "UAE Government: emergency numbers", "url": "https://u.ae/en//information-and-services/justice-safety-and-the-law/handling-emergencies"},
        ],
    },
    {
        "country": "de", "title": "Germany",
        "body": {
            "summary": "Germany brings together regional cultural landscapes, historic cities and natural areas. The context of a particular state or city helps read this diversity more precisely.",
            "history": "Germany's UNESCO World Heritage list includes historic towns, cathedrals, architectural ensembles, industrial heritage and natural properties. They belong to different periods and regions, so no single history describes the country as a whole.",
            "cuisine": "Culinary traditions differ between regions. Ask the venue about a dish's origin, seasonal ingredients and local way of serving it instead of treating one recipe as common to the entire country.",
            "traditions": "Organ craftsmanship and music are inscribed on UNESCO's Representative List of the Intangible Cultural Heritage of Humanity. Instruments are created for specific architectural spaces, and knowledge is passed on through work with a master, vocational schools and universities.",
            "practical": [
                {"label": "Currency", "value": "Euro (EUR)"},
                {"label": "Emergency assistance", "value": "112 · fire and rescue services"},
            ],
        },
        "sources": [
            {"label": "UNESCO: Germany World Heritage properties", "url": "https://whc.unesco.org/en/statesparties/de"},
            {"label": "UNESCO: organ craftsmanship and music", "url": "https://ich.unesco.org/en/RL/organ-craftsmanship-and-music-01277"},
            {"label": "European Commission: Germany and the euro", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/germany-and-euro_en?prefLang=pt"},
            {"label": "Federal health portal: emergency number", "url": "https://gesund.bund.de/en/erste-hilfe"},
        ],
    },
    {
        "country": "eg", "title": "Egypt",
        "body": {
            "summary": "Egypt brings together ancient archaeological complexes, historic cities, desert and river landscapes. The context of a particular territory matters more than a single image of the country.",
            "history": "Egypt's UNESCO World Heritage list includes Memphis and the pyramid fields from Giza to Dahshur, ancient Thebes, Historic Cairo, Nubian monuments and the natural Wadi Al-Hitan. These are different periods and types of heritage, so each place needs its own historical and conservation context.",
            "cuisine": "Culinary customs differ between regions and families. When trying a dish, ask the venue or organiser about its ingredients, preparation and local context.",
            "traditions": "Tahteeb is a stick game inscribed on UNESCO's Representative List of the Intangible Cultural Heritage of Humanity. Historically connected with martial practices, it is now performed as a festive game: striking is not allowed, and its rules value mutual respect and self-control.",
            "practical": [
                {"label": "Currency", "value": "Egyptian pound (EGP)"},
                {"label": "Emergency assistance", "value": "122 · police; 123 · ambulance; 180 · fire service"},
            ],
        },
        "sources": [
            {"label": "UNESCO: Egypt World Heritage properties", "url": "https://whc.unesco.org/en/statesparties/eg/"},
            {"label": "UNESCO: Tahteeb stick game", "url": "https://ich.unesco.org/en/RL/tahteeb-stick-game-01189"},
            {"label": "Central Bank of Egypt: Egyptian pound clearing", "url": "https://www.cbe.org.eg/en/payment-systems-and-services/payment-systems/cheque-clearing-house-cch/egp-cch"},
            {"label": "Kafr El Sheikh government directory: emergency numbers", "url": "https://kfs.gov.eg/index.php/directory"},
        ],
    },
    {
        "country": "id", "title": "Indonesia",
        "body": {
            "summary": "Indonesia brings together many regional, island and cultural settings. Getting to know a particular territory helps avoid reducing them to a single image.",
            "history": "Indonesia's UNESCO World Heritage list includes the Borobudur and Prambanan temple compounds, the Cultural Landscape of Bali, industrial heritage, archaeological sites and national parks. These places belong to different periods and territories, so historical context should be read locally.",
            "cuisine": "Culinary traditions differ between islands and regions. When trying a dish, ask the venue or organiser about its origin, ingredients and local way of serving it.",
            "traditions": "Gamelan is a traditional Indonesian percussion orchestra and set of instruments inscribed on UNESCO's Representative List. Its music is played in rituals, ceremonies, theatre, festivals and concerts, and skills are passed on through families, schools and other educational practices.",
            "practical": [
                {"label": "Currency", "value": "Indonesian rupiah (IDR)"},
                {"label": "Emergency assistance", "value": "112 · single emergency call centre; check local availability"},
            ],
        },
        "sources": [
            {"label": "UNESCO: Indonesia World Heritage properties", "url": "https://whc.unesco.org/en/statesparties/ID/"},
            {"label": "UNESCO: gamelan", "url": "https://ich.unesco.org/en/RL/gamelan-01607"},
            {"label": "Bank Indonesia: rupiah currency management", "url": "https://www.bi.go.id/en/fungsi-utama/sistem-pembayaran/pengelolaan-rupiah/default.aspx"},
            {"label": "Indonesia.go.id: emergency service 112", "url": "https://indonesia.go.id/layanan/kependudukan/sosial/layanan-darurat-112?lang=1"},
        ],
    },
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": f"wiki-country-{edition['country']}-en",
        "slug": f"country-{edition['country']}-en",
        "published_version_id": None, "created_at": now, "updated_at": now,
    } for edition in EDITIONS])
    op.bulk_insert(sa.table(
        "wiki_article_version",
        sa.column("id", sa.String()), sa.column("article_id", sa.String()), sa.column("author_id", sa.String()),
        sa.column("status", sa.String()), sa.column("title", sa.String()), sa.column("body", postgresql.JSONB()),
        sa.column("sources", postgresql.JSONB()), sa.column("license", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": f"wiki-country-{edition['country']}-en-v1",
        "article_id": f"wiki-country-{edition['country']}-en",
        "author_id": "crista-editorial", "status": "published", "title": edition["title"],
        "body": edition["body"], "sources": edition["sources"], "license": LICENSE,
        "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    } for edition in EDITIONS])
    for edition in EDITIONS:
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = :version_id WHERE id = :article_id"
        ).bindparams(
            version_id=f"wiki-country-{edition['country']}-en-v1",
            article_id=f"wiki-country-{edition['country']}-en",
        ))


def downgrade() -> None:
    for edition in EDITIONS:
        article_id = f"wiki-country-{edition['country']}-en"
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = NULL WHERE id = :article_id"
        ).bindparams(article_id=article_id))
        op.execute(sa.text(
            "DELETE FROM wiki_article_version WHERE id = :version_id"
        ).bindparams(version_id=f"wiki-country-{edition['country']}-en-v1"))
        op.execute(sa.text(
            "DELETE FROM wiki_article WHERE id = :article_id"
        ).bindparams(article_id=article_id))
