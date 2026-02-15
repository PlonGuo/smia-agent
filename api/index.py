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
    key = settings.effective_openai_key
    results["openai_key_prefix"] = key[:8] + "..." if len(key) > 8 else "too_short"
    results["openai_key_length"] = len(key)

    # 3a. Raw httpx test to api.openai.com
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as hc:
            resp = await hc.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            results["openai_raw_httpx"] = f"status={resp.status_code}"
    except Exception as e:
        results["openai_raw_httpx"] = f"error: {type(e).__name__}: {e}"

    # 3b. OpenAI SDK test
    try:
        import openai
        results["openai_sdk_version"] = openai.__version__
        oc = openai.AsyncOpenAI(api_key=key)
        await oc.models.list()
        results["openai_connection"] = "ok"
    except Exception as e:
        import traceback
        results["openai_connection"] = f"error: {type(e).__name__}: {e}"
        results["openai_traceback"] = traceback.format_exc()[-500:]

    # 4. Check crawl4ai availability
    try:
        import crawl4ai
        results["crawl4ai"] = "installed"
    except ImportError:
        results["crawl4ai"] = "not installed (expected on Vercel)"

    # 5. Check YARS availability and path resolution
    api_dir = Path(__file__).resolve().parent
    yars_src = api_dir.parent / "libs" / "yars" / "src"
    results["yars_expected_path"] = str(yars_src)
    results["yars_path_exists"] = yars_src.exists()
    if yars_src.exists():
        results["yars_path_contents"] = [str(p.name) for p in yars_src.iterdir()]
    # Also check what the crawler sees
    crawler_file = api_dir / "services" / "crawler.py"
    crawler_yars_src = crawler_file.resolve().parent.parent.parent / "libs" / "yars" / "src"
    results["crawler_yars_path"] = str(crawler_yars_src)
    results["crawler_yars_exists"] = crawler_yars_src.exists()

    # Try importing with the correct path
    if str(yars_src) not in sys.path and yars_src.exists():
        sys.path.insert(0, str(yars_src))
    try:
        from yars.yars import YARS
        results["yars"] = "available"
    except ImportError as e:
        results["yars"] = f"not available: {e}"

    # 6. Test Reddit fetch via YARS (with ScraperAPI proxy if configured)
    results["scraper_api_key"] = bool(settings.scraper_api_key.strip())
    try:
        from services.crawler import fetch_reddit
        reddit_posts = await fetch_reddit("test", limit=2)
        results["reddit_fetch"] = f"ok: {len(reddit_posts)} posts"
        if reddit_posts:
            results["reddit_sample_title"] = reddit_posts[0].get("title", "")[:80]
    except Exception as e:
        import traceback
        results["reddit_fetch"] = f"error: {type(e).__name__}: {e}"
        results["reddit_traceback"] = traceback.format_exc()[-500:]

    return results
