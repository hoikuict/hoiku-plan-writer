from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "hoiku-plan-writer"
    database_url: str = "sqlite:///./hoiku_plan_writer.db"


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("HOIKU_PLAN_APP_NAME", "hoiku-plan-writer"),
        database_url=os.getenv("HOIKU_PLAN_DATABASE_URL", "sqlite:///./hoiku_plan_writer.db"),
    )
