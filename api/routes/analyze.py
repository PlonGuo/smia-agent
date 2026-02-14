from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze")
async def analyze_topic():
    return {"message": "Not implemented yet"}
