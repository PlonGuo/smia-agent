import sys
from pathlib import Path

# Ensure the api/ directory is on sys.path so submodule imports resolve on Vercel.
_api_dir = str(Path(__file__).resolve().parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
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
from routes.internal import router as internal_router
from routes.mcp_server import mcp

init_langfuse()


@asynccontextmanager
async def lifespan(app):
    from services.database import seed_admin_if_empty
    seed_admin_if_empty()
    yield


app = FastAPI(title="SmIA API", version="0.1.0", lifespan=lifespan)

_ALLOWED_ORIGINS = [
    "https://smia-agent.vercel.app",
    "https://smia-agent-huizhirong-guos-projects.vercel.app",
    "https://smia-agent-git-main-huizhirong-guos-projects.vercel.app",
]

if settings.environment == "development":
    _ALLOWED_ORIGINS += ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://smia-agent(-[\w-]+)?-huizhirong-guos-projects\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-internal-secret"],
)

app.include_router(analyze_router)
app.include_router(reports_router)
app.include_router(telegram_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ai_daily_report_router)
app.include_router(bookmarks_router)
app.include_router(feedback_router)
app.include_router(internal_router)

# MCP server — fully public, no auth required
# AI clients (Claude Desktop, Cursor, Windsurf) connect via:
# { "mcpServers": { "smia": { "url": "https://smia-agent.fly.dev/mcp" } } }
# Note: CORSMiddleware does not cover mounted sub-apps; CORS is intentionally
# not set on /mcp since all current MCP clients are non-browser (direct HTTP).
app.mount("/mcp", mcp.streamable_http_app())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Log 422 validation errors with full detail for debugging."""
    print(f"[VALIDATION] {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions, log details, return sanitized response."""
    tb = traceback.format_exc()
    print(f"[UNHANDLED] {request.method} {request.url.path}: {type(exc).__name__}: {exc}\n{tb[-500:]}")
    if settings.environment == "development":
        return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
