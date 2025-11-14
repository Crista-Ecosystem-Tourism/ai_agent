Crista agent

source venv/bin/activate
pip install -r requirements.xtx

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
