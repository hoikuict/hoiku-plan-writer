from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from . import __version__
from .ai.service import AnnualPlanPreviewService, build_annual_preview_service
from .config import Settings, load_settings
from .db import create_db_and_tables, create_engine_for_url
from .demo_runtime import (
    DEMO_SESSION_COOKIE_NAME,
    MUTATING_METHODS,
    get_demo_session_manager,
    load_demo_settings,
    reset_demo_runtime_cache,
    should_use_secure_cookies,
)
from .demo_seed import initialize_demo_template_database
from .web.routers.annual_plans import router as annual_plans_router
from .web.routers.demo import router as demo_router
from .web.routers.documents import router as documents_router
from .web.routers.home import router as home_router
from .web.routers.monthly_plans import router as monthly_plans_router
from .web.routers.nursery_profiles import router as nursery_profiles_router
from .web.routers.safety_plans import router as safety_plans_router
from .web.routers.staff_auth import router as staff_auth_router


def _content_length(header_value: str | None) -> int:
    if not header_value:
        return 0
    try:
        return max(int(header_value), 0)
    except (TypeError, ValueError):
        return 0


def _limit_response(status_code: int, title: str, message: str) -> HTMLResponse:
    body = f"""
    <!doctype html>
    <html lang="ja">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
        <style>
          body {{
            font-family: sans-serif;
            margin: 0;
            background: #f7f4ee;
            color: #222;
          }}
          main {{
            max-width: 720px;
            margin: 48px auto;
            padding: 24px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.08);
          }}
          a {{
            color: #0b57d0;
          }}
        </style>
      </head>
      <body>
        <main>
          <h1>{title}</h1>
          <p>{message}</p>
          <p><a href="/documents/">デモに戻る</a></p>
        </main>
      </body>
    </html>
    """
    return HTMLResponse(body, status_code=status_code)


def create_app(
    settings: Settings | None = None,
    *,
    annual_preview_service: AnnualPlanPreviewService | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings()
    demo_settings = load_demo_settings()
    engine = create_engine_for_url(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if demo_settings.enabled:
            get_demo_session_manager().prepare_base_database(initialize_demo_template_database)
        else:
            create_db_and_tables(engine)
        try:
            yield
        finally:
            if demo_settings.enabled:
                get_demo_session_manager().close()
                reset_demo_runtime_cache()
            engine.dispose()

    app = FastAPI(title=resolved_settings.app_name, version=__version__, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.demo_settings = demo_settings
    app.state.engine = engine
    app.state.annual_preview_service = annual_preview_service or build_annual_preview_service(resolved_settings)

    @app.middleware("http")
    async def public_demo_middleware(request: Request, call_next):
        if not demo_settings.enabled:
            return await call_next(request)

        manager = get_demo_session_manager()
        manager.cleanup_expired_sessions()

        incoming_session_id = request.cookies.get(DEMO_SESSION_COOKIE_NAME)
        session_id, should_set_cookie = manager.ensure_session_id(incoming_session_id)
        request.state.demo_session_id = session_id
        manager.ensure_session_database(session_id)
        manager.touch_session(session_id)

        if request.method in MUTATING_METHODS:
            body_bytes = _content_length(request.headers.get("content-length"))
            if body_bytes > demo_settings.max_request_body_bytes:
                return _limit_response(
                    413,
                    "リクエストが大きすぎます",
                    f"公開デモでは、1回の書き込みリクエストを {demo_settings.max_request_body_bytes} bytes までに制限しています。",
                )

            allowed, _ = manager.reserve_input_budget(session_id, body_bytes)
            if not allowed:
                return _limit_response(
                    413,
                    "このセッションの入力上限に達しました",
                    "この公開デモセッションでは書き込み上限に達しました。新しいセッションを開始してリセットしてください。",
                )

        response = await call_next(request)
        if should_set_cookie and not getattr(request.state, "skip_demo_session_cookie", False):
            response.set_cookie(
                DEMO_SESSION_COOKIE_NAME,
                session_id,
                httponly=True,
                samesite="lax",
                secure=should_use_secure_cookies(request, demo_settings),
                path="/",
            )
        return response

    app.include_router(home_router)
    app.include_router(documents_router)
    app.include_router(nursery_profiles_router)
    app.include_router(annual_plans_router)
    app.include_router(monthly_plans_router)
    app.include_router(safety_plans_router)
    app.include_router(staff_auth_router)
    app.include_router(demo_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("hoiku_plan_writer.main:app", host="127.0.0.1", port=8000, reload=True)
