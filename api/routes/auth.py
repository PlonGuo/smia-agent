from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/bind/code")
async def generate_bind_code():
    return {"message": "Not implemented yet"}


@router.post("/bind/confirm")
async def confirm_binding():
    return {"message": "Not implemented yet"}
