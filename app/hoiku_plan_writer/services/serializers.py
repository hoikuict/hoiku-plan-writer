from __future__ import annotations

from ..domain.models import GeneratedPlan, SectionBlock
from ..domain.section_catalog import MONTHLY_SECTIONS, annual_section_definitions


def plan_to_dict(plan: GeneratedPlan) -> dict[str, object]:
    return {
        "document_type": plan.document_type.value,
        "title": plan.title,
        "status": plan.status.value,
        "missing_inputs": plan.missing_inputs,
        "blocks": [block_to_dict(block) for block in plan.blocks],
    }


def block_to_dict(block: SectionBlock) -> dict[str, object]:
    return {
        "section_key": block.section_key,
        "title": block.title,
        "body": block.body,
        "evidence_tags": [tag.value for tag in block.evidence_tags],
        "needs_confirmation": block.needs_confirmation,
        "editor_note": block.editor_note,
    }


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
