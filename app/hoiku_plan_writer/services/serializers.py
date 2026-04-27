from __future__ import annotations

from ..domain.models import DocumentStatus, DocumentType, EvidenceTag, GeneratedPlan, SectionBlock, SourceRef
from ..domain.section_catalog import MONTHLY_SECTIONS, annual_section_definitions


def plan_to_dict(plan: GeneratedPlan) -> dict[str, object]:
    return {
        "document_type": plan.document_type.value,
        "title": plan.title,
        "status": plan.status.value,
        "missing_inputs": plan.missing_inputs,
        "blocks": [block_to_dict(block) for block in plan.blocks],
    }


def dict_to_plan(payload: dict[str, object]) -> GeneratedPlan:
    return GeneratedPlan(
        document_type=DocumentType(str(payload.get("document_type", ""))),
        title=str(payload.get("title", "")),
        status=DocumentStatus(str(payload.get("status", DocumentStatus.DRAFT.value))),
        missing_inputs=[str(item) for item in _list_payload(payload.get("missing_inputs"))],
        blocks=[dict_to_block(item) for item in _list_payload(payload.get("blocks"))],
    )


def block_to_dict(block: SectionBlock) -> dict[str, object]:
    return {
        "section_key": block.section_key,
        "title": block.title,
        "body": block.body,
        "evidence_tags": [tag.value for tag in block.evidence_tags],
        "source_refs": [source_ref_to_dict(source_ref) for source_ref in block.source_refs],
        "needs_confirmation": block.needs_confirmation,
        "editor_note": block.editor_note,
    }


def dict_to_block(payload: object) -> SectionBlock:
    if not isinstance(payload, dict):
        raise ValueError("block payload must be an object")
    return SectionBlock(
        section_key=str(payload.get("section_key", "")),
        title=str(payload.get("title", "")),
        body=str(payload.get("body", "")),
        evidence_tags=[EvidenceTag(str(tag)) for tag in _list_payload(payload.get("evidence_tags"))],
        source_refs=[dict_to_source_ref(source_ref) for source_ref in _list_payload(payload.get("source_refs"))],
        needs_confirmation=bool(payload.get("needs_confirmation", False)),
        editor_note=_optional_text(payload.get("editor_note")),
    )


def source_ref_to_dict(source_ref: SourceRef) -> dict[str, str]:
    return {
        "kind": source_ref.kind,
        "ref": source_ref.ref,
        "label": source_ref.label,
    }


def dict_to_source_ref(payload: object) -> SourceRef:
    if not isinstance(payload, dict):
        raise ValueError("source ref payload must be an object")
    return SourceRef(
        kind=str(payload.get("kind", "")),
        ref=str(payload.get("ref", "")),
        label=str(payload.get("label", "")),
    )


def section_keys_to_dict() -> dict[str, list[dict[str, str]]]:
    return {
        "annual": [
            {
                "section_key": definition.key,
                "title": definition.title,
                "purpose": definition.purpose,
            }
            for definition in annual_section_definitions()
        ],
        "monthly": [
            {
                "section_key": definition.key,
                "title": definition.title,
                "purpose": definition.purpose,
            }
            for definition in MONTHLY_SECTIONS
        ],
    }


def _list_payload(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
