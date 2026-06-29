from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(request: Request):

    return PlainTextResponse("Webhook funcionando!")