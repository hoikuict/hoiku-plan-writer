from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...auth import clear_staff_session
from ...demo_runtime import DEMO_SESSION_COOKIE_NAME, is_public_demo_enabled

router = APIRouter(prefix="/demo", tags=["demo"])


def _normalize_redirect(redirect_to: str | None, fallback: str) -> str:
    if redirect_to and redirect_to.startswith("/") and not redirect_to.startswith("//"):
        return redirect_to
    return fallback


@router.post("/reset")
def reset_demo_session(request: Request, redirect_to: str = Form("/staff/login")):
    target = _normalize_redirect(redirect_to, "/staff/login")
    response = RedirectResponse(url=target, status_code=303)
    clear_staff_session(response)
    if is_public_demo_enabled():
        request.state.skip_demo_session_cookie = True
        response.delete_cookie(DEMO_SESSION_COOKIE_NAME, path="/")
    return response