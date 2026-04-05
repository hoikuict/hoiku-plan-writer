from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Protocol
from urllib.parse import quote, unquote

from fastapi import Depends, HTTPException, Request, Response


class StaffRole(str, Enum):
    VIEW_ONLY = "view_only"
    CAN_EDIT = "can_edit"
    ADMIN = "admin"


ROLE_LABELS = {
    StaffRole.VIEW_ONLY: "閲覧のみ",
    StaffRole.CAN_EDIT: "編集可",
    StaffRole.ADMIN: "管理者",
}

MOCK_ROLE_COOKIE = "mock_role"
MOCK_ACTOR_REF_COOKIE = "mock_actor_ref"
MOCK_NURSERY_REF_COOKIE = "mock_nursery_ref"
MOCK_CLASSROOMS_COOKIE = "mock_classroom_refs"
MOCK_STAFF_NAME_COOKIE = "mock_staff_name"
COOKIE_MAX_AGE = 60 * 60 * 24


def _cookie_options(request: Request | None = None) -> dict[str, object]:
    from .demo_runtime import load_demo_settings, should_use_secure_cookies

    settings = load_demo_settings()
    options: dict[str, object] = {
        "httponly": True,
        "samesite": "lax",
        "secure": should_use_secure_cookies(request, settings),
        "path": "/",
    }
    if not settings.enabled:
        options["max_age"] = COOKIE_MAX_AGE
    return options


def _parse_role(raw: str | None) -> StaffRole:
    if raw in {item.value for item in StaffRole}:
        return StaffRole(raw)
    return StaffRole.CAN_EDIT


def _parse_classroom_refs(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ("classroom:5yo-a",)
    refs = tuple(item.strip() for item in raw.split(",") if item.strip())
    return refs or ("classroom:5yo-a",)


@dataclass(slots=True)
class StaffUser:
    role: StaffRole
    actor_ref: str = "staff:demo-editor"
    nursery_ref: str = "nursery:demo"
    classroom_refs: tuple[str, ...] = ("classroom:5yo-a",)
    name: str = "Mock Staff"

    @property
    def can_view(self) -> bool:
        return True

    @property
    def can_edit(self) -> bool:
        return self.role in (StaffRole.CAN_EDIT, StaffRole.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role == StaffRole.ADMIN

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role.value)

    def can_access_classroom(self, classroom_ref: str) -> bool:
        if self.is_admin:
            return True
        if not self.classroom_refs:
            return True
        return classroom_ref in self.classroom_refs


class StaffAuthBackend(Protocol):
    def get_current_user(self, request: Request) -> StaffUser: ...

    def set_session(
        self,
        response: Response,
        *,
        role: StaffRole,
        actor_ref: str,
        nursery_ref: str,
        classroom_refs: tuple[str, ...],
        name: str,
        request: Request | None = None,
    ) -> None: ...

    def clear_session(self, response: Response) -> None: ...


class MockStaffAuthBackend:
    def get_current_user(self, request: Request) -> StaffUser:
        role = _parse_role(request.query_params.get("as") or request.cookies.get(MOCK_ROLE_COOKIE))
        actor_ref = (
            request.query_params.get("actor_ref")
            or request.cookies.get(MOCK_ACTOR_REF_COOKIE)
            or "staff:demo-editor"
        )
        nursery_ref = (
            request.query_params.get("nursery_ref")
            or request.cookies.get(MOCK_NURSERY_REF_COOKIE)
            or "nursery:demo"
        )
        classroom_refs = _parse_classroom_refs(
            request.query_params.get("classrooms") or request.cookies.get(MOCK_CLASSROOMS_COOKIE)
        )
        raw_name = request.cookies.get(MOCK_STAFF_NAME_COOKIE) or "Mock%20Staff"
        name = unquote(raw_name)
        return StaffUser(
            role=role,
            actor_ref=actor_ref,
            nursery_ref=nursery_ref,
            classroom_refs=classroom_refs,
            name=name,
        )

    def set_session(
        self,
        response: Response,
        *,
        role: StaffRole,
        actor_ref: str,
        nursery_ref: str,
        classroom_refs: tuple[str, ...],
        name: str,
        request: Request | None = None,
    ) -> None:
        cookie_options = _cookie_options(request)
        response.set_cookie(MOCK_ROLE_COOKIE, role.value, **cookie_options)
        response.set_cookie(MOCK_ACTOR_REF_COOKIE, actor_ref, **cookie_options)
        response.set_cookie(MOCK_NURSERY_REF_COOKIE, nursery_ref, **cookie_options)
        response.set_cookie(MOCK_CLASSROOMS_COOKIE, ",".join(classroom_refs), **cookie_options)
        response.set_cookie(MOCK_STAFF_NAME_COOKIE, quote(name), **cookie_options)

    def clear_session(self, response: Response) -> None:
        response.delete_cookie(MOCK_ROLE_COOKIE, path="/")
        response.delete_cookie(MOCK_ACTOR_REF_COOKIE, path="/")
        response.delete_cookie(MOCK_NURSERY_REF_COOKIE, path="/")
        response.delete_cookie(MOCK_CLASSROOMS_COOKIE, path="/")
        response.delete_cookie(MOCK_STAFF_NAME_COOKIE, path="/")


_staff_auth_backend: StaffAuthBackend = MockStaffAuthBackend()


def configure_staff_auth_backend(backend: StaffAuthBackend) -> None:
    global _staff_auth_backend
    _staff_auth_backend = backend


def reset_staff_auth_backend() -> None:
    configure_staff_auth_backend(MockStaffAuthBackend())


def get_current_staff_user(request: Request) -> StaffUser:
    return _staff_auth_backend.get_current_user(request)


def set_staff_session(
    response: Response,
    *,
    role: StaffRole,
    actor_ref: str,
    nursery_ref: str,
    classroom_refs: tuple[str, ...],
    name: str,
    request: Request | None = None,
) -> None:
    _staff_auth_backend.set_session(
        response,
        role=role,
        actor_ref=actor_ref,
        nursery_ref=nursery_ref,
        classroom_refs=classroom_refs,
        name=name,
        request=request,
    )


def clear_staff_session(response: Response) -> None:
    _staff_auth_backend.clear_session(response)


CurrentUser = Annotated[StaffUser, Depends(get_current_staff_user)]


def require_can_edit(user: CurrentUser) -> None:
    if not user.can_edit:
        raise HTTPException(status_code=403, detail="編集権限がありません")


def require_admin(user: CurrentUser) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")


def require_classroom_access(user: CurrentUser, classroom_ref: str) -> None:
    if not user.can_access_classroom(classroom_ref):
        raise HTTPException(status_code=403, detail="このクラスの文書にアクセスできません")