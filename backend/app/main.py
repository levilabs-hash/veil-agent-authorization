"""FastAPI entrypoint. Tool calls must enter VEIL through this process."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import cors_allow_origin_regex, cors_allow_origins

app = FastAPI(title="VEIL", description="Runtime authorization gateway for AI agents")

_cors_kwargs: dict = {
    "allow_origins": cors_allow_origins(),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
_cors_regex = cors_allow_origin_regex()
if _cors_regex:
    _cors_kwargs["allow_origin_regex"] = _cors_regex

app.add_middleware(CORSMiddleware, **_cors_kwargs)

app.include_router(router)
app.include_router(router, prefix="/veil-api")
