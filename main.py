from fastapi import FastAPI
from app.whatsapp.webhook import router as whatsapp_router

app = FastAPI(
    title="DNIA Core",
    version="0.1.0"
)

app.include_router(whatsapp_router)

@app.get("/")
def home():
    return {
        "status": "online",
        "project": "DNIA Core",
        "version": "0.1.0"
    }