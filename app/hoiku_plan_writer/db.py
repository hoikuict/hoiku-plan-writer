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
    if engine.dialect.name == "sqlite":
        _ensure_sqlite_profile_columns(engine)


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


def _ensure_sqlite_profile_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("nursery_profiles"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("nursery_profiles")}
    column_definitions = {
        "local_context": "TEXT NOT NULL DEFAULT ''",
        "curriculum_focus": "TEXT NOT NULL DEFAULT ''",
        "assessment_policy": "TEXT NOT NULL DEFAULT ''",
        "daily_rhythm": "TEXT NOT NULL DEFAULT ''",
        "document_format_notes": "TEXT NOT NULL DEFAULT ''",
        "privacy_policy": "TEXT NOT NULL DEFAULT '個人名、診断名、健康詳細、家庭の詳細事情は入力・出力に含めない。'",
        "enabled_field_keys_json": "JSON",
    }

    with engine.begin() as connection:
        for column_name, definition in column_definitions.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE nursery_profiles ADD COLUMN {column_name} {definition}"))
