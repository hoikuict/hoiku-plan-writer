from __future__ import annotations

from typing import Protocol

from ...domain.models import AnnualPlanInput, GeneratedPlan, MonthlyPlanInput, NurseryProfile


class AnnualPreviewProvider(Protocol):
    provider_name: str
    model_name: str

    def generate_annual_plan_preview(
        self,
        *,
        profile: NurseryProfile,
        plan_input: AnnualPlanInput,
        fallback_plan: GeneratedPlan,
        model_name: str | None = None,
    ) -> GeneratedPlan: ...

    def generate_monthly_plan_preview(
        self,
        *,
        profile: NurseryProfile,
        annual_plan: GeneratedPlan,
        plan_input: MonthlyPlanInput,
        fallback_plan: GeneratedPlan,
        model_name: str | None = None,
    ) -> GeneratedPlan: ...
