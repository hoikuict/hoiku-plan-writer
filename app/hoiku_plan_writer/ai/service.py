from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..domain.models import AnnualPlanInput, GeneratedPlan, MonthlyPlanInput, NurseryProfile
from ..services.generators import generate_annual_plan, generate_monthly_plan
from .contracts import AnnualPlanPreviewResult, MonthlyPlanPreviewResult
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
    monthly_preview_enabled: bool = False
    disabled_note: str = ""
    configured_model_options: tuple[str, ...] = ()
    _model_choices_cache: list[str] | None = field(default=None, init=False, repr=False)

    @property
    def can_use_llm(self) -> bool:
        return self.can_use_annual_llm

    @property
    def can_use_annual_llm(self) -> bool:
        return self.annual_preview_enabled and self.provider is not None

    @property
    def can_use_monthly_llm(self) -> bool:
        return self.monthly_preview_enabled and self.provider is not None

    @property
    def provider_label(self) -> str:
        return self.model_label()

    @property
    def model_choices(self) -> list[str]:
        if self._model_choices_cache is not None:
            return list(self._model_choices_cache)

        choices: list[str] = []
        if self.provider is not None:
            list_models = getattr(self.provider, "list_model_names", None)
            if callable(list_models):
                try:
                    choices.extend(list_models())
                except Exception:
                    choices = []
            if self.provider.model_name:
                choices.insert(0, self.provider.model_name)
        choices.extend(self.configured_model_options)
        self._model_choices_cache = _unique_non_empty(choices)
        return list(self._model_choices_cache)

    @property
    def availability_note(self) -> str:
        return self.annual_availability_note

    @property
    def annual_availability_note(self) -> str:
        return self._availability_note(
            enabled=self.annual_preview_enabled,
            feature_name="年案AIプレビュー",
        )

    @property
    def monthly_availability_note(self) -> str:
        return self._availability_note(
            enabled=self.monthly_preview_enabled,
            feature_name="月案AIプレビュー",
        )

    def model_label(self, selected_model: str | None = None) -> str:
        if self.provider is None:
            return ""
        model_name = self.resolve_model_name(selected_model)
        if model_name:
            return f"{self.provider.provider_name} / {model_name}"
        return self.provider.provider_name

    def resolve_model_name(self, selected_model: str | None = None) -> str:
        selected = (selected_model or "").strip()
        if selected:
            return selected
        if self.provider is None:
            return ""
        return self.provider.model_name

    def preview(
        self,
        *,
        profile: NurseryProfile,
        plan_input: AnnualPlanInput,
        use_llm: bool = True,
        selected_model: str | None = None,
    ) -> AnnualPlanPreviewResult:
        fallback_plan = generate_annual_plan(profile, plan_input)

        fallback_result = self._annual_fallback_result(
            fallback_plan,
            enabled=self.annual_preview_enabled,
            use_llm=use_llm,
        )
        if fallback_result is not None:
            return fallback_result

        resolved_model = self.resolve_model_name(selected_model)
        try:
            llm_plan = self.provider.generate_annual_plan_preview(
                profile=profile,
                plan_input=plan_input,
                fallback_plan=fallback_plan,
                model_name=resolved_model,
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
            model_name=resolved_model,
            note=f"AIプレビュー: {self.model_label(resolved_model)} で年案を構成しました。",
        )

    def preview_monthly(
        self,
        *,
        profile: NurseryProfile,
        annual_plan: GeneratedPlan,
        plan_input: MonthlyPlanInput,
        use_llm: bool = True,
        selected_model: str | None = None,
    ) -> MonthlyPlanPreviewResult:
        fallback_plan = generate_monthly_plan(profile, annual_plan, plan_input)

        fallback_result = self._monthly_fallback_result(
            fallback_plan,
            enabled=self.monthly_preview_enabled,
            use_llm=use_llm,
        )
        if fallback_result is not None:
            return fallback_result

        resolved_model = self.resolve_model_name(selected_model)
        try:
            llm_plan = self.provider.generate_monthly_plan_preview(
                profile=profile,
                annual_plan=annual_plan,
                plan_input=plan_input,
                fallback_plan=fallback_plan,
                model_name=resolved_model,
            )
        except Exception as exc:
            return MonthlyPlanPreviewResult(
                plan=fallback_plan,
                generation_mode="fallback",
                provider_name="rule-based",
                note=_preview_failure_note(exc),
            )

        return MonthlyPlanPreviewResult(
            plan=llm_plan,
            generation_mode="llm",
            provider_name=self.provider.provider_name,
            model_name=resolved_model,
            note=f"AIプレビュー: {self.model_label(resolved_model)} で月案を構成しました。",
        )

    def _availability_note(self, *, enabled: bool, feature_name: str) -> str:
        if enabled and self.provider is not None:
            return f"利用モデル: {self.provider_label}"
        if not enabled:
            return f"{feature_name}は無効です。現在は既定generatorでプレビューします。"
        if self.disabled_note:
            return self.disabled_note
        return "LLMは未設定のため、既定generatorでプレビューします。"

    def _annual_fallback_result(
        self,
        plan: GeneratedPlan,
        *,
        enabled: bool,
        use_llm: bool,
    ) -> AnnualPlanPreviewResult | None:
        note = self._fallback_note(enabled=enabled, use_llm=use_llm)
        if note is None:
            return None
        return AnnualPlanPreviewResult(
            plan=plan,
            generation_mode="fallback",
            provider_name="rule-based",
            note=note,
        )

    def _monthly_fallback_result(
        self,
        plan: GeneratedPlan,
        *,
        enabled: bool,
        use_llm: bool,
    ) -> MonthlyPlanPreviewResult | None:
        note = self._fallback_note(enabled=enabled, use_llm=use_llm)
        if note is None:
            return None
        return MonthlyPlanPreviewResult(
            plan=plan,
            generation_mode="fallback",
            provider_name="rule-based",
            note=note,
        )

    def _fallback_note(self, *, enabled: bool, use_llm: bool) -> str | None:
        if not enabled:
            return self.disabled_note or "AIプレビューは無効です。既定generatorでプレビューしています。"
        if not use_llm:
            return "AIプレビューはオフです。既定generatorでプレビューしています。"
        if self.provider is None:
            return self.disabled_note or "LLMは未設定のため、既定generatorでプレビューしています。"
        return None


def build_annual_preview_service(settings: Settings) -> AnnualPlanPreviewService:
    requested = settings.ai_enable_annual_preview or settings.ai_enable_monthly_preview
    if not requested:
        return AnnualPlanPreviewService(
            annual_preview_enabled=False,
            monthly_preview_enabled=False,
            disabled_note="AIプレビューは無効です。既定generatorでプレビューしています。",
            configured_model_options=settings.ai_model_options,
        )

    if settings.ai_provider in {"", "disabled"}:
        return AnnualPlanPreviewService(
            annual_preview_enabled=settings.ai_enable_annual_preview,
            monthly_preview_enabled=settings.ai_enable_monthly_preview,
            disabled_note="LLMは未設定のため、既定generatorでプレビューしています。",
            configured_model_options=settings.ai_model_options,
        )

    if settings.ai_provider == "ollama":
        return AnnualPlanPreviewService(
            provider=OllamaChatProvider(
                model_name=settings.ai_model or DEFAULT_OLLAMA_MODEL,
                base_url=settings.ai_base_url or DEFAULT_OLLAMA_BASE_URL,
                timeout_seconds=settings.ai_timeout_seconds,
            ),
            annual_preview_enabled=settings.ai_enable_annual_preview,
            monthly_preview_enabled=settings.ai_enable_monthly_preview,
            configured_model_options=settings.ai_model_options,
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
                annual_preview_enabled=settings.ai_enable_annual_preview,
                monthly_preview_enabled=settings.ai_enable_monthly_preview,
                disabled_note=f"LLM設定が不足しています ({missing})。既定generatorでプレビューしています。",
                configured_model_options=settings.ai_model_options,
            )

        return AnnualPlanPreviewService(
            provider=OpenAIResponsesProvider(
                api_key=settings.ai_api_key,
                model_name=settings.ai_model,
                base_url=settings.ai_base_url or DEFAULT_OPENAI_BASE_URL,
                timeout_seconds=settings.ai_timeout_seconds,
            ),
            annual_preview_enabled=settings.ai_enable_annual_preview,
            monthly_preview_enabled=settings.ai_enable_monthly_preview,
            configured_model_options=settings.ai_model_options,
        )

    return AnnualPlanPreviewService(
        annual_preview_enabled=settings.ai_enable_annual_preview,
        monthly_preview_enabled=settings.ai_enable_monthly_preview,
        disabled_note=f"未対応のAI provider '{settings.ai_provider}' のため、既定generatorでプレビューしています。",
        configured_model_options=settings.ai_model_options,
    )


def _preview_failure_note(exc: Exception) -> str:
    message = str(exc).strip()
    if "timed out" in message.lower():
        return (
            "LLMプレビューがタイムアウトしたため、既定generatorを表示しています。"
            "タイムアウトを延ばすか、より軽いモデルに切り替えてください。"
        )
    if message:
        return f"LLMプレビューに失敗したため、既定generatorを表示しています。詳細: {message}"
    return "LLMプレビューに失敗したため、既定generatorを表示しています。"


def _unique_non_empty(values: list[str] | tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in values if item and item.strip()))
