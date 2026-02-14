from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from routes.analyze import router as analyze_router
from routes.reports import router as reports_router
from routes.telegram import router as telegram_router
from routes.auth import router as auth_router

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


# Vercel serverless handler
handler = Mangum(app, lifespan="off")
