from fastapi import APIRouter

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook():
    return {"ok": True}
