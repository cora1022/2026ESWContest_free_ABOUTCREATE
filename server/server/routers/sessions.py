from __future__ import annotations

import asyncio
import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from server.dependencies import get_services, request_session
from server.schemas import LoginRequest
from server.services.container import AppServices


router = APIRouter(prefix="/api/session", tags=["session"])


def set_session_cookie(request: Request, response: Response, token: str) -> None:
    services = get_services(request)
    response.set_cookie(
        key=services.settings.session_cookie_name,
        value=token,
        max_age=services.settings.session_hours * 3600,
        httponly=True,
        secure=services.settings.use_secure_cookie(request.url.scheme),
        samesite="strict",
        path="/",
    )


@router.post("")
async def create_session(
    body: LoginRequest,
    request: Request,
    response: Response,
    x_session_mode: str | None = Header(default=None),
    services: AppServices = Depends(get_services),
) -> dict[str, Any]:
    if not secrets.compare_digest(body.key, services.settings.dashboard_key):
        await asyncio.sleep(0.25)
        raise HTTPException(status_code=401, detail="접속 키가 올바르지 않습니다.")
    token, expires_at = services.sessions.create()
    set_session_cookie(request, response, token)
    payload: dict[str, Any] = {"authenticated": True, "expires_at": expires_at}
    if x_session_mode != "cookie":
        payload["session"] = token
    return payload


@router.get("")
async def session_status(
    request: Request,
    response: Response,
    token: str = Depends(request_session),
    services: AppServices = Depends(get_services),
) -> dict[str, Any]:
    set_session_cookie(request, response, token)
    return {"authenticated": True, "expires_at": services.sessions.expires_at(token)}


@router.delete("")
async def delete_session(
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None),
    services: AppServices = Depends(get_services),
) -> dict[str, bool]:
    token = request.cookies.get(services.settings.session_cookie_name, "")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    if token:
        services.sessions.revoke(token)
        await services.hub.close_dashboards_for_session(token, reason="dashboard session revoked")
    response.delete_cookie(services.settings.session_cookie_name, path="/", samesite="strict")
    return {"authenticated": False}
