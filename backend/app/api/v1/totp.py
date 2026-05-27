"""TOTP enrollment & management routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.auth import (
    TotpConfirmRequest,
    TotpDisableRequest,
    TotpEnrollResponse,
    TotpStatus,
)
from app.services.totp_service import (
    InvalidTotpCodeError,
    TotpNotEnrolledError,
    TotpService,
)

router = APIRouter(prefix="/auth/totp", tags=["auth"])


@router.get("/status", response_model=TotpStatus)
async def totp_status(current_user: User = Depends(get_current_user)) -> TotpStatus:
    return TotpStatus(
        enabled=current_user.totp_enabled,
        pending_setup=bool(current_user.totp_secret_encrypted) and not current_user.totp_enabled,
    )


@router.post("/enroll", response_model=TotpEnrollResponse)
async def totp_enroll(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TotpEnrollResponse:
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="2FA déjà activée — désactivez-la avant de la régénérer.",
        )
    secret, uri = await TotpService(db).enroll(current_user)
    return TotpEnrollResponse(secret=secret, otpauth_uri=uri)


@router.post("/confirm", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def totp_confirm(
    body: TotpConfirmRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await TotpService(db).confirm(current_user, body.code)
    except TotpNotEnrolledError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun secret 2FA en attente — lancez d'abord /enroll.",
        ) from exc
    except InvalidTotpCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Code 2FA invalide."
        ) from exc


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def totp_disable(
    body: TotpDisableRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await TotpService(db).disable(current_user, body.code)
    except TotpNotEnrolledError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA non activée sur ce compte.",
        ) from exc
    except InvalidTotpCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Code 2FA invalide."
        ) from exc
