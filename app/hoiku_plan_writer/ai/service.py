from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..domain.models import AnnualPlanInput, NurseryProfile
from ..services.generators import generate_annual_plan
from .contracts import AnnualPlanPreviewResult
from .providers.base import AnnualPreviewProvider
from .providers.ollama_chat import OllamaChatProvider
from .providers.openai_responses import OpenAIResponsesProvider

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass(slots=True)
class AnnualPlanPreviewService:
    provider: AnnualPreviewProvider | None = None
    annual_preview_enabled: bool = False
    disabled_note: str = ""

    @property
    def can_use_llm(self) -> bool:
        return self.annual_preview_enabled and self.provider is not None

    @property
    def provider_label(self) -> str:
        if self.provider is None:
            return ""
        if self.provider.model_name:
            return f"{self.provider.provider_name} / {self.provider.model_name}"
        return self.provider.provider_name

    @property
    def availability_note(self) -> str:
        if self.can_use_llm:
            return f"利用モデル: {self.provider_label}"
        if self.disabled_note:
            return self.disabled_note
        return "LLM は未設定のため、既定 generator でプレビューします。"

    def preview(
        self,
        *,
        profile: NurseryProfile,
        plan_input: AnnualPlanInput,
        use_llm: bool = True,
    ) -> AnnualPlanPreviewResult:
        fallback_plan = generate_annual_plan(profile, plan_input)

        if not self.annual_preview_enabled:
            return AnnualPlanPreviewResult(
                plan=fallback_plan,
                generation_mode="fallback",
                provider_name="rule-based",
                note=self.disabled_note or "現在は既定 generator でプレビューしています。",
            )

        if not use_llm:
            return AnnualPlanPreviewResult(
                plan=fallback_plan,
                generation_mode="fallback",
                provider_name="rule-based",
                note="LLMプレビューはオフです。現在は既定 generator でプレビューしています。",
            )

        if self.provider is None:
            return AnnualPlanPreviewResult(
                plan=fallback_plan,
                generation_mode="fallback",
                provider_name="rule-based",
                note=self.disabled_note or "LLM は未設定のため、既定 generator でプレビューしています。",
            )

        try:
            llm_plan = self.provider.generate_annual_plan_preview(
                profile=profile,
                plan_input=plan_input,
                fallback_plan=fallback_plan,
            )
        except Exception as exc:
            return AnnualPlanPreviewResult(
                plan=fallback_plan,
                generation_mode="fallback",
                provider_name="rule-based",
                note=_preview_failure_note(exc),
            )

        return AnnualPlanPreviewResult(
            plan=llm_plan,
            generation_mode="llm",
            provider_name=self.provider.provider_name,
            model_name=self.provider.model_name,
            note=f"LLMプレビュー: {self.provider_label} を使って草案を構成しています。",
        )



def build_annual_preview_service(settings: Settings) -> AnnualPlanPreviewService:
    if not settings.ai_enable_annual_preview:
        return AnnualPlanPreviewService(
            annual_preview_enabled=False,
            disabled_note="AIプレビューは無効です。現在は既定 generator でプレビューしています。",
        )

    if settings.ai_provider in {"", "disabled"}:
        return AnnualPlanPreviewService(
            annual_preview_enabled=True,
            disabled_note="LLM は未設定のため、既定 generator でプレビューしています。",
        )

    if settings.ai_provider == "ollama":
        return AnnualPlanPreviewService(
            provider=OllamaChatProvider(
                model_name=settings.ai_model or DEFAULT_OLLAMA_MODEL,
                base_url=settings.ai_base_url or DEFAULT_OLLAMA_BASE_URL,
                timeout_seconds=settings.ai_timeout_seconds,
            ),
            annual_preview_enabled=True,
        )

    if settings.ai_provider == "openai":
        missing_settings: list[str] = []
        if not settings.ai_model:
            missing_settings.append("HOIKU_PLAN_AI_MODEL")
        if not settings.ai_api_key:
            missing_settings.append("HOIKU_PLAN_AI_API_KEY")
        if missing_settings:
            missing = ", ".join(missing_settings)
            return AnnualPlanPreviewService(
                annual_preview_enabled=True,
                disabled_note=f"LLM 設定が不足しています ({missing})。既定 generator でプレビューしています。",
            )

        return AnnualPlanPreviewService(
            provider=OpenAIResponsesProvider(
                api_key=settings.ai_api_key,
                model_name=settings.ai_model,
                base_url=settings.ai_base_url or DEFAULT_OPENAI_BASE_URL,
                timeout_seconds=settings.ai_timeout_seconds,
            ),
            annual_preview_enabled=True,
        )

    return AnnualPlanPreviewService(
        annual_preview_enabled=True,
        disabled_note=f"未対応の AI provider '{settings.ai_provider}' のため、既定 generator を表示しています。",
    )



def _preview_failure_note(exc: Exception) -> str:
    message = str(exc).strip()
    if "timed out" in message.lower():
        return "LLMプレビューがタイムアウトしたため、既定 generator を表示しています。タイムアウトを延ばすか、より軽い設定に切り替えてください。"
    if message:
        return f"LLMプレビューに失敗したため、既定 generator を表示しています。詳細: {message}"
    return "LLMプレビューに失敗したため、既定 generator を表示しています。"