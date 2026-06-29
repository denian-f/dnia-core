from fastapi import FastAPI

app = FastAPI(
    title="DNIA Core",
    version="0.1.0"
)


@app.get("/")
def home():
    return {
        "status": "online",
        "project": "DNIA Core",
        "version": "0.1.0"
    }