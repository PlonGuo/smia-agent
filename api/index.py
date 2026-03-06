import sys
from pathlib import Path

# Ensure the api/ directory is on sys.path so submodule imports resolve on Vercel.
_api_dir = str(Path(__file__).resolve().parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.langfuse_config import init_langfuse
from contextlib import asynccontextmanager

from routes.analyze import router as analyze_router
from routes.reports import router as reports_router
from routes.telegram import router as telegram_router
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.ai_daily_report import router as ai_daily_report_router
from routes.bookmarks import router as bookmarks_router
from routes.feedback import router as feedback_router

init_langfuse()


@asynccontextmanager
async def lifespan(app):
    from services.database import seed_admin_if_empty
    seed_admin_if_empty()
    yield


app = FastAPI(title="SmIA API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(reports_router)
app.include_router(telegram_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ai_daily_report_router)
app.include_router(bookmarks_router)
app.include_router(feedback_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


