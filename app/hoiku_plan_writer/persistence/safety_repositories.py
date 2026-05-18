from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..domain.models import SectionBlock, SourceRef
from ..domain.safety import SafetyLogType, SafetyPlanDraft, SafetyPlanStatus
from ..persistence.models import (
    SafetyActionItemRecord,
    SafetyImplementationLogRecord,
    SafetyPlanBlockRecord,
    SafetyPlanRecord,
)
from ..time_utils import utc_now


def create_safety_plan(
    session: Session,
    *,
    draft: SafetyPlanDraft,
    nursery_ref: str,
    actor_ref: str,
    input_snapshot: dict[str, Any],
    approve: bool,
) -> SafetyPlanRecord:
    now = utc_now()
    status = SafetyPlanStatus.APPROVED.value if approve and not draft.missing_inputs else SafetyPlanStatus.DRAFT.value
    plan = SafetyPlanRecord(
        nursery_ref=nursery_ref,
        actor_ref=actor_ref,
        facility_type=draft.facility_profile.facility_type.value,
        compliance_standard=draft.facility_profile.compliance_standard.value,
        school_year=draft.school_year,
        title=draft.title,
        status=status,
        established_on=draft.established_on,
        approved_by_actor_ref=actor_ref if status == SafetyPlanStatus.APPROVED.value else None,
        approved_at=now if status == SafetyPlanStatus.APPROVED.value else None,
        missing_inputs_json=list(draft.missing_inputs),
        source_refs_json=_aggregate_source_refs(draft.blocks),
        input_snapshot_json=input_snapshot,
    )
    session.add(plan)
    session.flush()

    for index, block in enumerate(draft.blocks):
        session.add(
            SafetyPlanBlockRecord(
                safety_plan_id=plan.id,
                sort_order=index,
                section_key=block.section_key,
                title=block.title,
                body=block.body,
                evidence_tags_json=[tag.value for tag in block.evidence_tags],
                source_refs_json=[_source_ref_to_dict(item) for item in block.source_refs],
                needs_confirmation=block.needs_confirmation,
                editor_note=block.editor_note,
            )
        )

    for index, item in enumerate(draft.action_items):
        session.add(
            SafetyActionItemRecord(
                safety_plan_id=plan.id,
                sort_order=index,
                category=item.category,
                title=item.title,
                planned_month=item.planned_month,
                responsible_role=item.responsible_role,
                recurrence=item.recurrence,
                legal_axis=item.legal_axis.value,
            )
        )

    session.commit()
    return get_safety_plan(session, plan.id, nursery_ref=nursery_ref)


def list_safety_plans(session: Session, *, nursery_ref: str) -> list[SafetyPlanRecord]:
    plans = session.exec(
        select(SafetyPlanRecord)
        .where(SafetyPlanRecord.nursery_ref == nursery_ref)
        .options(
            selectinload(SafetyPlanRecord.blocks),
            selectinload(SafetyPlanRecord.action_items),
            selectinload(SafetyPlanRecord.implementation_logs),
        )
        .order_by(SafetyPlanRecord.updated_at.desc(), SafetyPlanRecord.id.desc())
    ).all()
    for plan in plans:
        _sort_plan_relations(plan)
    return plans


def get_safety_plan(session: Session, plan_id: int, *, nursery_ref: str) -> SafetyPlanRecord | None:
    plan = session.exec(
        select(SafetyPlanRecord)
        .where(
            SafetyPlanRecord.id == plan_id,
            SafetyPlanRecord.nursery_ref == nursery_ref,
        )
        .options(
            selectinload(SafetyPlanRecord.blocks),
            selectinload(SafetyPlanRecord.action_items),
            selectinload(SafetyPlanRecord.implementation_logs),
        )
    ).first()
    if plan:
        _sort_plan_relations(plan)
    return plan


def approve_safety_plan(
    session: Session,
    *,
    plan: SafetyPlanRecord,
    actor_ref: str,
) -> SafetyPlanRecord:
    plan.status = SafetyPlanStatus.APPROVED.value
    plan.approved_by_actor_ref = actor_ref
    plan.approved_at = utc_now()
    plan.updated_at = utc_now()
    session.add(plan)
    session.commit()
    return get_safety_plan(session, plan.id, nursery_ref=plan.nursery_ref)


def add_safety_log(
    session: Session,
    *,
    plan: SafetyPlanRecord,
    log_type: SafetyLogType,
    implemented_on: date,
    title: str,
    participants: str,
    method: str,
    evidence_note: str,
    evidence_file_ref: str,
    actor_ref: str,
    related_action_id: int | None = None,
) -> SafetyImplementationLogRecord:
    log = SafetyImplementationLogRecord(
        safety_plan_id=plan.id,
        related_action_id=related_action_id,
        log_type=log_type.value,
        implemented_on=implemented_on,
        title=title,
        participants=participants,
        method=method,
        evidence_note=evidence_note,
        evidence_file_ref=evidence_file_ref,
        actor_ref=actor_ref,
    )
    plan.updated_at = utc_now()
    session.add(log)
    session.add(plan)
    session.commit()
    session.refresh(log)
    return log


def safety_log_pairs(plan: SafetyPlanRecord) -> list[tuple[SafetyLogType, date]]:
    pairs: list[tuple[SafetyLogType, date]] = []
    for log in plan.implementation_logs:
        try:
            pairs.append((SafetyLogType(log.log_type), log.implemented_on))
        except ValueError:
            continue
    return pairs


def _sort_plan_relations(plan: SafetyPlanRecord) -> None:
    plan.blocks.sort(key=lambda item: (item.sort_order, item.id or 0))
    plan.action_items.sort(key=lambda item: (item.sort_order, item.id or 0))
    plan.implementation_logs.sort(key=lambda item: (item.implemented_on, item.id or 0), reverse=True)


def _aggregate_source_refs(blocks: Iterable[SectionBlock]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    results: list[dict[str, str]] = []
    for block in blocks:
        for source_ref in block.source_refs:
            key = (source_ref.kind, source_ref.ref, source_ref.label)
            if key in seen:
                continue
            seen.add(key)
            results.append(_source_ref_to_dict(source_ref))
    return results


def _source_ref_to_dict(source_ref: SourceRef) -> dict[str, str]:
    return {
        "kind": source_ref.kind,
        "ref": source_ref.ref,
        "label": source_ref.label,
    }
