from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.models import (
    DocumentStatus,
    DocumentType,
    EvidenceTag,
    GeneratedPlan,
    SectionBlock,
    SourceRef,
)

_ALLOWED_SOURCE_REF_KINDS = ("nursery_profile", "official_guidance", "user_input", "document")


@dataclass(frozen=True, slots=True)
class AnnualPlanPreviewResult:
    plan: GeneratedPlan
    generation_mode: str
    provider_name: str
    model_name: str = ""
    note: str = ""

    @property
    def is_llm(self) -> bool:
        return self.generation_mode == "llm"


@dataclass(frozen=True, slots=True)
class MonthlyPlanPreviewResult:
    plan: GeneratedPlan
    generation_mode: str
    provider_name: str
    model_name: str = ""
    note: str = ""

    @property
    def is_llm(self) -> bool:
        return self.generation_mode == "llm"



def annual_plan_json_schema(expected_section_keys: list[str]) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_type": {
                "type": "string",
                "enum": [DocumentType.ANNUAL.value],
            },
            "title": {"type": "string"},
            "missing_inputs": {
                "type": "array",
                "items": {"type": "string"},
            },
            "blocks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "section_key": {
                            "type": "string",
                            "enum": expected_section_keys,
                        },
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "source_refs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "kind": {
                                        "type": "string",
                                        "enum": list(_ALLOWED_SOURCE_REF_KINDS),
                                    },
                                    "ref": {"type": "string"},
                                    "label": {"type": "string"},
                                },
                                "required": ["kind", "ref", "label"],
                            },
                        },
                        "needs_confirmation": {"type": "boolean"},
                        "editor_note": {
                            "type": ["string", "null"],
                        },
                    },
                    "required": [
                        "section_key",
                        "title",
                        "body",
                        "source_refs",
                        "needs_confirmation",
                        "editor_note",
                    ],
                },
            },
        },
        "required": ["document_type", "title", "missing_inputs", "blocks"],
    }



def annual_plan_block_json_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "body": {"type": "string"},
            "needs_confirmation": {"type": "boolean"},
            "editor_note": {"type": ["string", "null"]},
        },
        "required": ["body", "needs_confirmation", "editor_note"],
    }


def block_response_format(name: str = "plan_block_preview") -> dict[str, object]:
    return {
        "type": "json_schema",
        "name": name,
        "strict": True,
        "schema": annual_plan_block_json_schema(),
    }



def annual_plan_response_format(expected_section_keys: list[str]) -> dict[str, object]:
    return {
        "type": "json_schema",
        "name": "annual_plan_preview",
        "strict": True,
        "schema": annual_plan_json_schema(expected_section_keys),
    }



def annual_preview_payload_to_plan(payload: dict[str, Any], *, fallback_plan: GeneratedPlan) -> GeneratedPlan:
    document_type = str(payload.get("document_type", ""))
    if document_type != DocumentType.ANNUAL.value:
        raise ValueError("annual plan preview payload must target document_type='annual'")

    blocks_payload = payload.get("blocks")
    if not isinstance(blocks_payload, list):
        raise ValueError("annual plan preview payload must contain a blocks list")

    fallback_blocks = {block.section_key: block for block in fallback_plan.blocks}
    expected_keys = [block.section_key for block in fallback_plan.blocks]
    payload_keys = [str(item.get("section_key", "")) for item in blocks_payload if isinstance(item, dict)]

    if payload_keys != expected_keys:
        raise ValueError("annual plan preview blocks must match the expected section order")

    blocks: list[SectionBlock] = []
    for block_payload in blocks_payload:
        if not isinstance(block_payload, dict):
            raise ValueError("annual plan preview block must be an object")
        section_key = str(block_payload.get("section_key", ""))
        fallback_block = fallback_blocks[section_key]
        body = str(block_payload.get("body", "")).strip()
        if not body:
            raise ValueError(f"annual plan preview block '{section_key}' must have a body")

        source_refs_payload = block_payload.get("source_refs")
        if not isinstance(source_refs_payload, list) or not source_refs_payload:
            raise ValueError(f"annual plan preview block '{section_key}' must include source refs")

        source_refs = [_source_ref_from_payload(item) for item in source_refs_payload]
        blocks.append(
            SectionBlock(
                section_key=section_key,
                title=str(block_payload.get("title", "")).strip() or fallback_block.title,
                body=body,
                evidence_tags=_evidence_tags_from_source_refs(source_refs),
                source_refs=source_refs,
                needs_confirmation=bool(block_payload.get("needs_confirmation", False)),
                editor_note=_optional_text(block_payload.get("editor_note")),
            )
        )

    missing_inputs_payload = payload.get("missing_inputs", [])
    if not isinstance(missing_inputs_payload, list):
        raise ValueError("annual plan preview payload must contain a missing_inputs list")

    return GeneratedPlan(
        document_type=DocumentType.ANNUAL,
        title=str(payload.get("title", "")).strip() or fallback_plan.title,
        status=DocumentStatus.DRAFT,
        blocks=blocks,
        missing_inputs=[str(item) for item in missing_inputs_payload],
    )



def annual_preview_payload_to_block(payload: dict[str, Any], *, fallback_block: SectionBlock) -> SectionBlock:
    return block_preview_payload_to_block(payload, fallback_block=fallback_block)


def block_preview_payload_to_block(payload: dict[str, Any], *, fallback_block: SectionBlock) -> SectionBlock:
    if not isinstance(payload, dict):
        raise ValueError("block payload must be an object")

    body = str(payload.get("body", "")).strip()
    if not body:
        raise ValueError(f"block '{fallback_block.section_key}' must have a body")

    needs_confirmation = payload.get("needs_confirmation")
    if not isinstance(needs_confirmation, bool):
        needs_confirmation = fallback_block.needs_confirmation

    editor_note = _optional_text(payload.get("editor_note"))
    if editor_note is None:
        editor_note = fallback_block.editor_note

    return SectionBlock(
        section_key=fallback_block.section_key,
        title=fallback_block.title,
        body=body,
        evidence_tags=list(fallback_block.evidence_tags),
        source_refs=list(fallback_block.source_refs),
        needs_confirmation=needs_confirmation,
        editor_note=editor_note,
    )



def _source_ref_from_payload(payload: dict[str, Any]) -> SourceRef:
    if not isinstance(payload, dict):
        raise ValueError("source ref payload must be an object")
    kind = str(payload.get("kind", "")).strip()
    if kind not in _ALLOWED_SOURCE_REF_KINDS:
        raise ValueError(f"unsupported source ref kind: {kind}")
    ref = str(payload.get("ref", "")).strip()
    label = str(payload.get("label", "")).strip()
    if not ref or not label:
        raise ValueError("source ref payload must include ref and label")
    return SourceRef(kind=kind, ref=ref, label=label)



def _evidence_tags_from_source_refs(source_refs: list[SourceRef]) -> list[EvidenceTag]:
    kinds = {item.kind for item in source_refs}
    tags: list[EvidenceTag] = []
    if "nursery_profile" in kinds:
        tags.append(EvidenceTag.NURSERY_POLICY)
    if "official_guidance" in kinds:
        tags.append(EvidenceTag.PUBLIC_GUIDANCE)
    if kinds.intersection({"user_input", "document"}):
        tags.append(EvidenceTag.USER_INPUT)
    tags.append(EvidenceTag.AI_COMPOSITION)
    return tags



def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
