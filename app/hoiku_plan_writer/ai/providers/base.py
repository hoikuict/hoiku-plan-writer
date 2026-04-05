from __future__ import annotations

from typing import Protocol

from ...domain.models import AnnualPlanInput, GeneratedPlan, NurseryProfile


class AnnualPreviewProvider(Protocol):
    provider_name: str
    model_name: str

    def generate_annual_plan_preview(
        self,
        *,
        profile: NurseryProfile,
        plan_input: AnnualPlanInput,
        fallback_plan: GeneratedPlan,
    ) -> GeneratedPlan: ...