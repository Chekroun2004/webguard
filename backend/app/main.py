import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.workers.celery_app
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models.scan import Scan
from app.db.session import AsyncSessionLocal
from app.workers.tasks.scan import run_scan_task

logger = logging.getLogger(__name__)


async def recover_stuck_scans(session: AsyncSession) -> None:
    result = await session.execute(
        select(Scan).where(Scan.status.in_(["pending", "running"]))
    )
    stuck = result.scalars().all()
    for scan in stuck:
        scan.status = "pending"
    await session.commit()
    for scan in stuck:
        run_scan_task.delay(scan.id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with AsyncSessionLocal() as db:
            await recover_stuck_scans(db)
    except Exception:
        logger.exception("Startup recovery failed — continuing anyway")
    yield


app = FastAPI(
    title="WebGuard API",
    description="Scanner de vulnérabilités web — backend API.",
    version="0.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
