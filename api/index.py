import sys
from pathlib import Path

# Ensure the api/ directory is on sys.path so submodule imports resolve on Vercel.
_api_dir = str(Path(__file__).resolve().parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.langfuse_config import init_langfuse
from routes.analyze import router as analyze_router
from routes.reports import router as reports_router
from routes.telegram import router as telegram_router
from routes.auth import router as auth_router

init_langfuse()

app = FastAPI(title="SmIA API", version="0.1.0")

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


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/debug")
async def debug_check():
    """Diagnostic endpoint to test each dependency on Vercel."""
    results = {}

    # 1. Check env vars
    from core.config import settings
    results["supabase_url"] = bool(settings.supabase_url)
    results["supabase_anon_key"] = bool(settings.supabase_anon_key)
    results["openai_key"] = bool(settings.effective_openai_key)
    results["youtube_api_key"] = bool(settings.youtube_api_key)
    results["firecrawl_api_key"] = bool(settings.firecrawl_api_key)
    results["langfuse_public_key"] = bool(settings.langfuse_public_key)
    results["langfuse_secret_key"] = bool(settings.langfuse_secret_key)

    # 2. Check Supabase connectivity
    try:
        from services.database import get_supabase_client
        client = get_supabase_client()
        client.table("analysis_reports").select("id").limit(1).execute()
        results["supabase_connection"] = "ok"
    except Exception as e:
        results["supabase_connection"] = f"error: {e}"

    # 3. Check OpenAI key validity
    try:
        import openai
        oc = openai.OpenAI(api_key=settings.effective_openai_key)
        oc.models.list()
        results["openai_connection"] = "ok"
    except Exception as e:
        results["openai_connection"] = f"error: {e}"

    # 4. Check crawl4ai availability
    try:
        import crawl4ai
        results["crawl4ai"] = "installed"
    except ImportError:
        results["crawl4ai"] = "not installed (expected on Vercel)"

    # 5. Check YARS availability
    try:
        from yars.yars import YARS
        results["yars"] = "available"
    except ImportError:
        results["yars"] = "not available (expected on Vercel)"

    return results
