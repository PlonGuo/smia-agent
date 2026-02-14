from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports")
async def list_reports():
    return {"reports": [], "total": 0, "page": 1, "per_page": 20}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    return {"message": "Not implemented yet"}


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    return {"message": "Not implemented yet"}
