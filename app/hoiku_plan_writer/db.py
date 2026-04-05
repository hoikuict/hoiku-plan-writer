from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


def create_engine_for_url(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, echo=False, connect_args=connect_args)


def create_db_and_tables(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_legacy_columns(engine)


def get_session(request: Request) -> Generator[Session, None, None]:
    resolved_engine = request.app.state.engine
    from .demo_runtime import DEMO_SESSION_COOKIE_NAME, get_demo_session_manager, is_public_demo_enabled

    if is_public_demo_enabled():
        session_id = (
            getattr(request.state, "demo_session_id", None)
            or request.cookies.get(DEMO_SESSION_COOKIE_NAME)
            or request.query_params.get(DEMO_SESSION_COOKIE_NAME)
        )
        if session_id:
            resolved_engine = get_demo_session_manager().get_engine(session_id)

    with Session(resolved_engine) as session:
        yield session


def _ensure_legacy_columns(engine: Engine) -> None:
    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "nursery_profiles" not in inspector.get_table_names():
        return

    nursery_profile_columns = {column["name"] for column in inspector.get_columns("nursery_profiles")}
    if "enabled_field_keys_json" not in nursery_profile_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE nursery_profiles ADD COLUMN enabled_field_keys_json JSON"))