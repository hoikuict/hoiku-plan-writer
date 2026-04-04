from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__
from .config import Settings, load_settings
from .db import create_db_and_tables, create_engine_for_url
from .web.routers.annual_plans import router as annual_plans_router
from .web.routers.documents import router as documents_router
from .web.routers.home import router as home_router
from .web.routers.monthly_plans import router as monthly_plans_router
from .web.routers.nursery_profiles import router as nursery_profiles_router
from .web.routers.staff_auth import router as staff_auth_router



def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    engine = create_engine_for_url(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        create_db_and_tables(engine)
        yield

    app = FastAPI(title=resolved_settings.app_name, version=__version__, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.engine = engine

    app.include_router(home_router)
    app.include_router(documents_router)
    app.include_router(nursery_profiles_router)
    app.include_router(annual_plans_router)
    app.include_router(monthly_plans_router)
    app.include_router(staff_auth_router)
    return app


app = create_app()



def run() -> None:
    import uvicorn

    uvicorn.run("hoiku_plan_writer.main:app", host="127.0.0.1", port=8000, reload=True)
