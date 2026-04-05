from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "hoiku-plan-writer"
    database_url: str = "sqlite:///./hoiku_plan_writer.db"
    ai_provider: str = "disabled"
    ai_model: str = ""
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_timeout_seconds: float = 20.0
    ai_enable_annual_preview: bool = False



def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("HOIKU_PLAN_APP_NAME", "hoiku-plan-writer"),
        database_url=os.getenv("HOIKU_PLAN_DATABASE_URL", "sqlite:///./hoiku_plan_writer.db"),
        ai_provider=os.getenv("HOIKU_PLAN_AI_PROVIDER", "disabled").strip().lower(),
        ai_model=os.getenv("HOIKU_PLAN_AI_MODEL", "").strip(),
        ai_api_key=os.getenv("HOIKU_PLAN_AI_API_KEY", "").strip(),
        ai_base_url=os.getenv("HOIKU_PLAN_AI_BASE_URL", "").strip(),
        ai_timeout_seconds=_load_float_env("HOIKU_PLAN_AI_TIMEOUT_SECONDS", 20.0),
        ai_enable_annual_preview=_load_bool_env("HOIKU_PLAN_AI_ENABLE_ANNUAL_PREVIEW", False),
    )



def _load_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}



def _load_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default