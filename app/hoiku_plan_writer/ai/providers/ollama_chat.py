from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from ...domain.models import AnnualPlanInput, GeneratedPlan, NurseryProfile, SectionBlock
from ..contracts import annual_plan_block_json_schema, annual_preview_payload_to_block
from ..prompts import build_annual_plan_block_messages


@dataclass(frozen=True, slots=True)
class OllamaChatProvider:
    model_name: str
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 20.0
    provider_name: str = "ollama"

    def generate_annual_plan_preview(
        self,
        *,
        profile: NurseryProfile,
        plan_input: AnnualPlanInput,
        fallback_plan: GeneratedPlan,
    ) -> GeneratedPlan:
        blocks: list[SectionBlock] = []
        failures: list[str] = []
        success_count = 0

        for fallback_block in fallback_plan.blocks:
            try:
                generated_block = self._generate_annual_plan_block(
                    profile=profile,
                    plan_input=plan_input,
                    fallback_plan=fallback_plan,
                    fallback_block=fallback_block,
                )
                blocks.append(generated_block)
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

    def _generate_annual_plan_block(
        self,
        *,
        profile: NurseryProfile,
        plan_input: AnnualPlanInput,
        fallback_plan: GeneratedPlan,
        fallback_block: SectionBlock,
    ) -> SectionBlock:
        response_payload = self._post_chat(
            {
                "model": self.model_name,
                "messages": build_annual_plan_block_messages(
                    profile=profile,
                    plan_input=plan_input,
                    fallback_plan=fallback_plan,
                    fallback_block=fallback_block,
                ),
                "stream": False,
                "format": annual_plan_block_json_schema(),
                "options": {
                    "temperature": 0,
                },
            }
        )
        output_text = _extract_message_content(response_payload)
        try:
            block_payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama response did not contain valid JSON") from exc
        return annual_preview_payload_to_block(block_payload, fallback_block=fallback_block)

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            url=_chat_url(self.base_url),
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "hoiku-plan-writer/0.1.0",
            },
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ollama chat API returned HTTP {exc.code}: {detail[:400]}") from exc
        except error.URLError as exc:
            raise RuntimeError("ollama chat API request failed") from exc



def _chat_url(base_url: str) -> str:
    api_root = base_url.rstrip("/")
    if api_root.endswith("/api"):
        return f"{api_root}/chat"
    return f"{api_root}/api/chat"



def _extract_message_content(payload: dict[str, Any]) -> str:
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("Ollama response did not include a message object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Ollama response did not include assistant content")
    return content



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