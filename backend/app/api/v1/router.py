from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.domains import router as domains_router
from app.api.v1.reports import router as reports_router
from app.api.v1.scans import router as scans_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(scans_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(domains_router)
