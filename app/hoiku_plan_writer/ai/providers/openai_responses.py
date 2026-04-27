from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from ...domain.models import AnnualPlanInput, GeneratedPlan, MonthlyPlanInput, NurseryProfile, SectionBlock
from ..contracts import (
    annual_plan_response_format,
    annual_preview_payload_to_plan,
    block_preview_payload_to_block,
    block_response_format,
)
from ..prompts import build_annual_plan_preview_messages, build_monthly_plan_block_messages


@dataclass(frozen=True, slots=True)
class OpenAIResponsesProvider:
    api_key: str
    model_name: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 20.0
    provider_name: str = "openai"

    def generate_annual_plan_preview(
        self,
        *,
        profile: NurseryProfile,
        plan_input: AnnualPlanInput,
        fallback_plan: GeneratedPlan,
        model_name: str | None = None,
    ) -> GeneratedPlan:
        response_payload = self._post_responses(
            {
                "model": self._effective_model_name(model_name),
                "input": build_annual_plan_preview_messages(
                    profile=profile,
                    plan_input=plan_input,
                    fallback_plan=fallback_plan,
                ),
                "text": {
                    "format": annual_plan_response_format(
                        [block.section_key for block in fallback_plan.blocks]
                    )
                },
            }
        )
        output_text = _extract_output_text(response_payload)
        try:
            plan_payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response did not contain valid JSON") from exc
        return annual_preview_payload_to_plan(plan_payload, fallback_plan=fallback_plan)

    def generate_monthly_plan_preview(
        self,
        *,
        profile: NurseryProfile,
        annual_plan: GeneratedPlan,
        plan_input: MonthlyPlanInput,
        fallback_plan: GeneratedPlan,
        model_name: str | None = None,
    ) -> GeneratedPlan:
        blocks: list[SectionBlock] = []
        failures: list[str] = []
        success_count = 0

        for fallback_block in fallback_plan.blocks:
            try:
                blocks.append(
                    self._generate_monthly_plan_block(
                        profile=profile,
                        annual_plan=annual_plan,
                        plan_input=plan_input,
                        fallback_plan=fallback_plan,
                        fallback_block=fallback_block,
                        model_name=model_name,
                    )
                )
                success_count += 1
            except Exception as exc:
                failures.append(f"{fallback_block.section_key}: {exc}")
                blocks.append(_copy_block(fallback_block))

        if success_count == 0:
            detail = failures[0] if failures else "no blocks returned"
            raise RuntimeError(detail)

        return GeneratedPlan(
            document_type=fallback_plan.document_type,
            title=fallback_plan.title,
            status=fallback_plan.status,
            blocks=blocks,
            missing_inputs=list(fallback_plan.missing_inputs),
        )

    def _generate_monthly_plan_block(
        self,
        *,
        profile: NurseryProfile,
        annual_plan: GeneratedPlan,
        plan_input: MonthlyPlanInput,
        fallback_plan: GeneratedPlan,
        fallback_block: SectionBlock,
        model_name: str | None = None,
    ) -> SectionBlock:
        response_payload = self._post_responses(
            {
                "model": self._effective_model_name(model_name),
                "input": build_monthly_plan_block_messages(
                    profile=profile,
                    annual_plan=annual_plan,
                    plan_input=plan_input,
                    fallback_plan=fallback_plan,
                    fallback_block=fallback_block,
                ),
                "text": {"format": block_response_format("monthly_plan_block_preview")},
            }
        )
        output_text = _extract_output_text(response_payload)
        try:
            block_payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response did not contain valid JSON") from exc
        return block_preview_payload_to_block(block_payload, fallback_block=fallback_block)

    def _post_responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            url=_responses_url(self.base_url),
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "hoiku-plan-writer/0.1.0",
            },
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"responses API returned HTTP {exc.code}: {detail[:400]}") from exc
        except error.URLError as exc:
            raise RuntimeError("responses API request failed") from exc

    def list_model_names(self) -> list[str]:
        return [self.model_name] if self.model_name else []

    def _effective_model_name(self, model_name: str | None) -> str:
        selected = (model_name or "").strip()
        return selected or self.model_name


def _responses_url(base_url: str) -> str:
    api_root = base_url.rstrip("/")
    if not api_root.endswith("/v1"):
        api_root = f"{api_root}/v1"
    return f"{api_root}/responses"


def _extract_output_text(payload: dict[str, Any]) -> str:
    direct_output_text = payload.get("output_text")
    if isinstance(direct_output_text, str) and direct_output_text.strip():
        return direct_output_text

    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") != "output_text":
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text

    raise ValueError("LLM response did not include output_text")


def _copy_block(block: SectionBlock) -> SectionBlock:
    return SectionBlock(
        section_key=block.section_key,
        title=block.title,
        body=block.body,
        evidence_tags=list(block.evidence_tags),
        source_refs=list(block.source_refs),
        needs_confirmation=block.needs_confirmation,
        editor_note=block.editor_note,
    )
