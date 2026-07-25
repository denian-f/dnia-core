from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.whatsapp.webhook import router as whatsapp_router
from app.dna_connect.cards.routes import router as cards_router
from app.dna_connect.cards.service import init_cards_db
from app.dna_connect.users.routes import router as users_router
from app.dna_connect.users.service import init_users_db
from app.dna_connect.dashboard.routes import router as dashboard_router
from app.dna_connect.web.routes import router as web_router
from app.dna_connect.auth.dependencies import get_optional_user

app = FastAPI(
    title="DNIA Core",
    version="0.1.0"
)

app.include_router(whatsapp_router)
app.include_router(cards_router)
app.include_router(users_router)
app.include_router(dashboard_router)
app.include_router(web_router)

DASHBOARD_STATIC_DIR = (
    Path(__file__).resolve().parent
    / "app" / "dna_connect" / "dashboard" / "static"
)

app.mount(
    "/dashboard/static",
    StaticFiles(directory=str(DASHBOARD_STATIC_DIR)),
    name="dashboard_static"
)

LOGIN_STATIC_DIR = (
    Path(__file__).resolve().parent
    / "app" / "dna_connect" / "web" / "static"
)

app.mount(
    "/login/static",
    StaticFiles(directory=str(LOGIN_STATIC_DIR)),
    name="login_static"
)

CARDS_STATIC_DIR = (
    Path(__file__).resolve().parent
    / "app" / "dna_connect" / "cards" / "static"
)

app.mount(
    "/cards/static",
    StaticFiles(directory=str(CARDS_STATIC_DIR)),
    name="cards_static"
)

init_users_db()
init_cards_db()

@app.get("/")
def home(current_user=Depends(get_optional_user)):

    if current_user:
        return RedirectResponse(url="/dashboard/view", status_code=302)

    return RedirectResponse(url="/login/view", status_code=302)
