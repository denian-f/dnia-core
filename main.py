from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.whatsapp.webhook import router as whatsapp_router
from app.dna_connect.cards.routes import router as cards_router
from app.dna_connect.cards.service import init_cards_db
from app.dna_connect.users.routes import router as users_router
from app.dna_connect.users.service import init_users_db
from app.dna_connect.dashboard.routes import router as dashboard_router

app = FastAPI(
    title="DNIA Core",
    version="0.1.0"
)

app.include_router(whatsapp_router)
app.include_router(cards_router)
app.include_router(users_router)
app.include_router(dashboard_router)

DASHBOARD_STATIC_DIR = (
    Path(__file__).resolve().parent
    / "app" / "dna_connect" / "dashboard" / "static"
)

app.mount(
    "/dashboard/static",
    StaticFiles(directory=str(DASHBOARD_STATIC_DIR)),
    name="dashboard_static"
)

init_users_db()
init_cards_db()

@app.get("/")
def home():
    return {
        "status": "online",
        "project": "DNIA Core",
        "version": "0.1.0"
    }