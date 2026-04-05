from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from ...domain.models import AnnualPlanInput, GeneratedPlan, NurseryProfile
from ..contracts import annual_plan_response_format, annual_preview_payload_to_plan
from ..prompts import build_annual_plan_preview_messages


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
    ) -> GeneratedPlan:
        response_payload = self._post_responses(
            {
                "model": self.model_name,
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