from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..domain.models import (
    DocumentStatus,
    DocumentType,
    EvidenceTag,
    GeneratedPlan,
    NurseryProfile,
    SectionBlock,
    SourceRef,
)
from ..persistence.models import ApprovalLogRecord, NurseryProfileRecord, PlanBlockRecord, PlanDocumentRecord
from ..time_utils import utc_now


def list_profile_versions(session: Session, nursery_ref: str) -> list[NurseryProfileRecord]:
    return session.exec(
        select(NurseryProfileRecord)
        .where(NurseryProfileRecord.nursery_ref == nursery_ref)
        .order_by(NurseryProfileRecord.version.desc(), NurseryProfileRecord.id.desc())
    ).all()


def get_active_profile_record(session: Session, nursery_ref: str) -> NurseryProfileRecord | None:
    return session.exec(
        select(NurseryProfileRecord)
        .where(
            NurseryProfileRecord.nursery_ref == nursery_ref,
            NurseryProfileRecord.approved.is_(True),
        )
        .order_by(NurseryProfileRecord.version.desc(), NurseryProfileRecord.id.desc())
    ).first()


def save_profile(
    session: Session,
    *,
    nursery_ref: str,
    actor_ref: str,
    profile: NurseryProfile,
    approve: bool,
) -> NurseryProfileRecord:
    latest_versions = list_profile_versions(session, nursery_ref)
    next_version = (latest_versions[0].version if latest_versions else 0) + 1

    if approve:
        for existing in latest_versions:
            if existing.approved:
                existing.approved = False
                existing.updated_at = utc_now()
                session.add(existing)

    record = NurseryProfileRecord(
        nursery_ref=nursery_ref,
        actor_ref=actor_ref,
        version=next_version,
        approved=approve,
        nursery_name=profile.nursery_name,
        target_age_group=profile.target_age_group,
        class_configuration=profile.class_configuration,
        local_context=profile.local_context,
        philosophy=profile.philosophy,
        childcare_goal=profile.childcare_goal,
        desired_child_image=profile.desired_child_image,
        child_view=profile.child_view,
        play_view=profile.play_view,
        support_policy=profile.support_policy,
        curriculum_focus=profile.curriculum_focus,
        assessment_policy=profile.assessment_policy,
        indoor_environment=profile.indoor_environment,
        outdoor_environment=profile.outdoor_environment,
        corner_play=profile.corner_play,
        community_resources=profile.community_resources,
        family_collaboration_policy=profile.family_collaboration_policy,
        local_collaboration_policy=profile.local_collaboration_policy,
        health_and_safety_policy=profile.health_and_safety_policy,
        inclusive_policy=profile.inclusive_policy,
        daily_rhythm=profile.daily_rhythm,
        preferred_expressions=profile.preferred_expressions,
        avoid_expressions=profile.avoid_expressions,
        sentence_tone=profile.sentence_tone,
        document_format_notes=profile.document_format_notes,
        missing_input_policy=profile.missing_input_policy,
        confirmation_marker=profile.confirmation_marker,
        evidence_tag_policy=profile.evidence_tag_policy,
        privacy_policy=profile.privacy_policy,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def profile_record_to_domain(record: NurseryProfileRecord) -> NurseryProfile:
    return NurseryProfile(
        nursery_name=record.nursery_name,
        target_age_group=record.target_age_group,
        class_configuration=record.class_configuration,
        local_context=record.local_context,
        philosophy=record.philosophy,
        childcare_goal=record.childcare_goal,
        desired_child_image=record.desired_child_image,
        child_view=record.child_view,
        play_view=record.play_view,
        support_policy=record.support_policy,
        curriculum_focus=record.curriculum_focus,
        assessment_policy=record.assessment_policy,
        indoor_environment=record.indoor_environment,
        outdoor_environment=record.outdoor_environment,
        corner_play=record.corner_play,
        community_resources=record.community_resources,
        family_collaboration_policy=record.family_collaboration_policy,
        local_collaboration_policy=record.local_collaboration_policy,
        health_and_safety_policy=record.health_and_safety_policy,
        inclusive_policy=record.inclusive_policy,
        daily_rhythm=record.daily_rhythm,
        preferred_expressions=record.preferred_expressions,
        avoid_expressions=record.avoid_expressions,
        sentence_tone=record.sentence_tone,
        document_format_notes=record.document_format_notes,
        missing_input_policy=record.missing_input_policy,
        confirmation_marker=record.confirmation_marker,
        evidence_tag_policy=record.evidence_tag_policy,
        privacy_policy=record.privacy_policy,
        approved=record.approved,
        version=record.version,
    )


def create_document(
    session: Session,
    *,
    generated_plan: GeneratedPlan,
    nursery_ref: str,
    classroom_ref: str,
    actor_ref: str,
    school_year: int | None,
    target_month: str | None,
    related_document_id: int | None,
    input_snapshot: dict[str, Any],
    role: str,
) -> PlanDocumentRecord:
    document = PlanDocumentRecord(
        document_type=generated_plan.document_type.value,
        title=generated_plan.title,
        status=generated_plan.status.value,
        nursery_ref=nursery_ref,
        classroom_ref=classroom_ref,
        actor_ref=actor_ref,
        school_year=school_year,
        target_month=target_month,
        related_document_id=related_document_id,
        missing_inputs_json=list(generated_plan.missing_inputs),
        source_refs_json=_aggregate_source_refs(generated_plan.blocks),
        input_snapshot_json=input_snapshot,
    )
    session.add(document)
    session.flush()

    for index, block in enumerate(generated_plan.blocks):
        session.add(
            PlanBlockRecord(
                document_id=document.id,
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

    session.add(
        ApprovalLogRecord(
            document_id=document.id,
            action="created",
            actor_ref=actor_ref,
            role=role,
            comment="下書きを作成",
        )
    )
    session.commit()
    return get_document(session, document.id, nursery_ref=nursery_ref)


def list_documents(
    session: Session,
    *,
    nursery_ref: str,
    classroom_refs: tuple[str, ...],
    status_filter: str = "all",
    document_type_filter: str = "all",
) -> list[PlanDocumentRecord]:
    query = (
        select(PlanDocumentRecord)
        .where(PlanDocumentRecord.nursery_ref == nursery_ref)
        .options(selectinload(PlanDocumentRecord.blocks), selectinload(PlanDocumentRecord.approval_logs))
        .order_by(PlanDocumentRecord.updated_at.desc(), PlanDocumentRecord.id.desc())
    )
    if status_filter != "all":
        query = query.where(PlanDocumentRecord.status == status_filter)
    if document_type_filter != "all":
        query = query.where(PlanDocumentRecord.document_type == document_type_filter)
    if classroom_refs:
        query = query.where(PlanDocumentRecord.classroom_ref.in_(classroom_refs))

    documents = session.exec(query).all()
    for document in documents:
        _sort_document_relations(document)
    return documents


def get_document(
    session: Session,
    document_id: int,
    *,
    nursery_ref: str,
) -> PlanDocumentRecord | None:
    document = session.exec(
        select(PlanDocumentRecord)
        .where(
            PlanDocumentRecord.id == document_id,
            PlanDocumentRecord.nursery_ref == nursery_ref,
        )
        .options(selectinload(PlanDocumentRecord.blocks), selectinload(PlanDocumentRecord.approval_logs))
    ).first()
    if document:
        _sort_document_relations(document)
    return document


def document_record_to_domain(document: PlanDocumentRecord) -> GeneratedPlan:
    blocks = [
        SectionBlock(
            section_key=block.section_key,
            title=block.title,
            body=block.body,
            evidence_tags=[EvidenceTag(item) for item in block.evidence_tags_json],
            source_refs=[_dict_to_source_ref(item) for item in block.source_refs_json],
            needs_confirmation=block.needs_confirmation,
            editor_note=block.editor_note,
        )
        for block in sorted(document.blocks, key=lambda item: (item.sort_order, item.id or 0))
    ]
    return GeneratedPlan(
        document_type=DocumentType(document.document_type),
        title=document.title,
        status=DocumentStatus(document.status),
        blocks=blocks,
        missing_inputs=list(document.missing_inputs_json),
    )


def update_document_content(
    session: Session,
    *,
    document: PlanDocumentRecord,
    title: str,
    block_bodies_by_id: dict[int, str],
    actor_ref: str,
    role: str,
    action: str,
    comment: str,
) -> tuple[PlanDocumentRecord, str]:
    now = utc_now()
    previous_status = document.status
    had_prior_submission = any(log.action in {"submitted", "resubmitted"} for log in document.approval_logs)

    document.title = title.strip() or document.title
    document.updated_at = now
    document.approved_at = None
    document.approved_by_actor_ref = None

    if action == "submit":
        document.status = DocumentStatus.SUBMITTED.value
        log_action = (
            "resubmitted"
            if previous_status in {DocumentStatus.SUBMITTED.value, DocumentStatus.RETURNED.value} or had_prior_submission
            else "submitted"
        )
        default_comment = "修正内容を送信しました。" if log_action == "resubmitted" else "文書を送信しました。"
    else:
        document.status = DocumentStatus.DRAFT.value
        log_action = "saved_draft"
        default_comment = "下書きを保存しました。"

    session.add(document)

    any_needs_confirmation = False
    for block in sorted(document.blocks, key=lambda item: (item.sort_order, item.id or 0)):
        if block.id is None:
            continue
        new_body = block_bodies_by_id.get(block.id, block.body)
        if new_body != block.body:
            block.body = new_body
            block.updated_at = now
            if block.needs_confirmation:
                block.needs_confirmation = False
                block.editor_note = _append_editor_note(block.editor_note, "手動編集で確認済み")
        any_needs_confirmation = any_needs_confirmation or block.needs_confirmation
        session.add(block)

    if not any_needs_confirmation:
        document.missing_inputs_json = []
        session.add(document)

    session.add(
        ApprovalLogRecord(
            document_id=document.id,
            action=log_action,
            actor_ref=actor_ref,
            role=role,
            comment=comment.strip() or default_comment,
        )
    )
    session.commit()
    return get_document(session, document.id, nursery_ref=document.nursery_ref), log_action


def update_document_status(
    session: Session,
    *,
    document: PlanDocumentRecord,
    status: DocumentStatus,
    actor_ref: str,
    role: str,
    comment: str,
) -> PlanDocumentRecord:
    document.status = status.value
    document.updated_at = utc_now()
    if status == DocumentStatus.APPROVED:
        document.approved_at = utc_now()
        document.approved_by_actor_ref = actor_ref
    else:
        document.approved_at = None
        document.approved_by_actor_ref = None

    action = "approved" if status == DocumentStatus.APPROVED else "returned"
    session.add(document)
    session.add(
        ApprovalLogRecord(
            document_id=document.id,
            action=action,
            actor_ref=actor_ref,
            role=role,
            comment=comment or ("承認" if action == "approved" else "差戻し"),
        )
    )
    session.commit()
    return get_document(session, document.id, nursery_ref=document.nursery_ref)


def _sort_document_relations(document: PlanDocumentRecord) -> None:
    document.blocks.sort(key=lambda item: (item.sort_order, item.id or 0))
    document.approval_logs.sort(key=lambda item: (item.created_at, item.id or 0), reverse=True)


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


def _dict_to_source_ref(payload: dict[str, Any]) -> SourceRef:
    return SourceRef(
        kind=str(payload.get("kind", "")),
        ref=str(payload.get("ref", "")),
        label=str(payload.get("label", "")),
    )


def _append_editor_note(existing_note: str | None, suffix: str) -> str:
    if not existing_note:
        return suffix
    if suffix in existing_note:
        return existing_note
    return f"{existing_note} / {suffix}"
