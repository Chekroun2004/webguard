from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginResponse(BaseModel):
    """Either a full token pair or a pending-TOTP challenge."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    totp_required: bool = False
    pending_token: str | None = None


class TotpLoginRequest(BaseModel):
    pending_token: str
    code: str = Field(min_length=6, max_length=6)


class TotpEnrollResponse(BaseModel):
    """Returned once during enrollment — secret is shown ONLY here."""

    secret: str
    otpauth_uri: str


class TotpConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TotpDisableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TotpStatus(BaseModel):
    enabled: bool
    pending_setup: bool
