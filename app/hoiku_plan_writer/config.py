from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "hoiku-plan-writer"
    database_url: str = "sqlite:///./hoiku_plan_writer.db"
    ai_provider: str = "disabled"
    ai_model: str = ""
    ai_model_options: tuple[str, ...] = ()
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_timeout_seconds: float = 20.0
    ai_enable_annual_preview: bool = False
    ai_enable_monthly_preview: bool = False


def load_settings() -> Settings:
    annual_preview_enabled = _load_bool_env("HOIKU_PLAN_AI_ENABLE_ANNUAL_PREVIEW", False)
    return Settings(
        app_name=os.getenv("HOIKU_PLAN_APP_NAME", "hoiku-plan-writer"),
        database_url=os.getenv("HOIKU_PLAN_DATABASE_URL", "sqlite:///./hoiku_plan_writer.db"),
        ai_provider=os.getenv("HOIKU_PLAN_AI_PROVIDER", "disabled").strip().lower(),
        ai_model=os.getenv("HOIKU_PLAN_AI_MODEL", "").strip(),
        ai_model_options=_load_list_env("HOIKU_PLAN_AI_MODEL_OPTIONS"),
        ai_api_key=os.getenv("HOIKU_PLAN_AI_API_KEY", "").strip(),
        ai_base_url=os.getenv("HOIKU_PLAN_AI_BASE_URL", "").strip(),
        ai_timeout_seconds=_load_float_env("HOIKU_PLAN_AI_TIMEOUT_SECONDS", 20.0),
        ai_enable_annual_preview=annual_preview_enabled,
        ai_enable_monthly_preview=_load_bool_env(
            "HOIKU_PLAN_AI_ENABLE_MONTHLY_PREVIEW",
            annual_preview_enabled,
        ),
    )


def _load_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_list_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(dict.fromkeys(values))


def _load_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
