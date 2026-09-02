from __future__ import annotations

from fastapi import Header, HTTPException, Request

from server.services.container import AppServices
from server.services.robot_hub import RobotHub
from server.services.sessions import SessionStore


def get_services(request: Request) -> AppServices:
    return request.app.state.services


def get_hub(request: Request) -> RobotHub:
    return get_services(request).hub


def get_session_store(request: Request) -> SessionStore:
    return get_services(request).sessions


def request_session(request: Request, authorization: str | None = Header(default=None)) -> str:
    services = get_services(request)
    token = request.cookies.get(services.settings.session_cookie_name, "")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if not services.sessions.valid(token):
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")
    return token
