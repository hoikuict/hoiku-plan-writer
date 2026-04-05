from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import StaffRole, clear_staff_session, get_current_staff_user, set_staff_session
from ..templating import render_template

router = APIRouter(prefix="/staff", tags=["staff-auth"])

DEFAULT_STAFF_REDIRECT = "/documents/"
DEFAULT_LOGOUT_REDIRECT = "/staff/login"


def _normalize_redirect(redirect_to: str | None, fallback: str) -> str:
    if redirect_to and redirect_to.startswith("/") and not redirect_to.startswith("//"):
        return redirect_to
    return fallback


@router.get("/login", response_class=HTMLResponse)
def staff_login_page(
    request: Request,
    redirect: str = DEFAULT_STAFF_REDIRECT,
    current_user=Depends(get_current_staff_user),
):
    return render_template(
        request,
        "staff_auth/login.html",
        current_user=current_user,
        redirect_to=_normalize_redirect(redirect, DEFAULT_STAFF_REDIRECT),
        available_roles=[StaffRole.CAN_EDIT, StaffRole.ADMIN, StaffRole.VIEW_ONLY],
    )


@router.post("/login")
def staff_login(
    request: Request,
    role: str = Form(StaffRole.CAN_EDIT.value),
    actor_ref: str = Form("staff:demo-editor"),
    nursery_ref: str = Form("nursery:demo"),
    classroom_refs_raw: str = Form("classroom:5yo-a"),
    name: str = Form("モック職員"),
    redirect_to: str = Form(DEFAULT_STAFF_REDIRECT),
):
    target = _normalize_redirect(redirect_to, DEFAULT_STAFF_REDIRECT)
    selected_role = StaffRole(role) if role in {item.value for item in StaffRole} else StaffRole.CAN_EDIT
    classroom_refs = tuple(item.strip() for item in classroom_refs_raw.split(",") if item.strip()) or (
        "classroom:5yo-a",
    )

    response = RedirectResponse(url=target, status_code=303)
    set_staff_session(
        response,
        role=selected_role,
        actor_ref=actor_ref.strip() or "staff:demo-editor",
        nursery_ref=nursery_ref.strip() or "nursery:demo",
        classroom_refs=classroom_refs,
        name=name.strip() or "モック職員",
        request=request,
    )
    return response


@router.post("/logout")
def staff_logout(redirect_to: str = Form(DEFAULT_LOGOUT_REDIRECT)):
    target = _normalize_redirect(redirect_to, DEFAULT_LOGOUT_REDIRECT)
    response = RedirectResponse(url=target, status_code=303)
    clear_staff_session(response)
    return response