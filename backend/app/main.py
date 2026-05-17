from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.workers.celery_app
from app.api.v1.router import api_v1_router
from app.core.config import settings

app = FastAPI(
    title="WebGuard API",
    description="Scanner de vulnérabilités web — backend API.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
