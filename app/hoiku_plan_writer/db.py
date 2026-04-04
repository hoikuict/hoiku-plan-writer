from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlmodel import Session, SQLModel, create_engine


def create_engine_for_url(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, echo=False, connect_args=connect_args)


def create_db_and_tables(engine) -> None:
    SQLModel.metadata.create_all(engine)


def get_session(request: Request) -> Generator[Session, None, None]:
    with Session(request.app.state.engine) as session:
        yield session
