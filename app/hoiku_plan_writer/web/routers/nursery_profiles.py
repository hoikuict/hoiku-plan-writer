from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_admin, require_can_edit
from ...db import get_session
from ...domain.profile_fields import review_profile_completeness
from ...persistence.models import NurseryProfileRecord
from ...persistence.repositories import get_active_profile_record, list_profile_versions, save_profile
from ..forms import ProfileFormData, profile_form_data
from ..templating import render_template

router = APIRouter(prefix="/nursery-profile", tags=["nursery-profile"])


def _form_from_record(record: NurseryProfileRecord | None) -> ProfileFormData:
    if not record:
        return ProfileFormData(
            nursery_name="",
            target_age_group="3〜5歳児",
            class_configuration="",
            local_context="",
            philosophy="",
            childcare_goal="",
            desired_child_image="",
            child_view="",
            play_view="",
            support_policy="",
        )
    return ProfileFormData(
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
    )


def _render_profile_form(
    request: Request,
    *,
    current_user,
    session,
    form_data: ProfileFormData,
    active_profile: NurseryProfileRecord | None,
    saved: bool = False,
    reviewed: bool = False,
    form_error: str = "",
):
    return render_template(
        request,
        "nursery_profiles/form.html",
        current_user=current_user,
        form_data=form_data,
        active_profile=active_profile,
        profile_versions=list_profile_versions(session, current_user.nursery_ref),
        profile_review=review_profile_completeness(form_data.to_domain(approved=bool(active_profile and active_profile.approved))),
        saved=saved,
        reviewed=reviewed,
        form_error=form_error,
    )


@router.get("/", response_class=HTMLResponse)
def nursery_profile_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    active_profile = get_active_profile_record(session, current_user.nursery_ref)
    return _render_profile_form(
        request,
        current_user=current_user,
        session=session,
        form_data=_form_from_record(active_profile),
        active_profile=active_profile,
        saved=request.query_params.get("saved") == "1",
    )


@router.post("/")
def save_nursery_profile(
    request: Request,
    action: str = Form("save"),
    form_data: ProfileFormData = Depends(profile_form_data),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    active_profile = get_active_profile_record(session, current_user.nursery_ref)
    profile = form_data.to_domain(approved=action == "activate")
    profile_review = review_profile_completeness(profile)

    if action == "review":
        return _render_profile_form(
            request,
            current_user=current_user,
            session=session,
            form_data=form_data,
            active_profile=active_profile,
            reviewed=True,
        )

    approve = action == "activate"
    if approve:
        require_admin(current_user)
        if not profile_review.can_activate:
            missing_labels = "、".join(issue.label for issue in profile_review.missing_required)
            return _render_profile_form(
                request,
                current_user=current_user,
                session=session,
                form_data=form_data,
                active_profile=active_profile,
                form_error=f"有効化には必須項目の入力が必要です: {missing_labels}",
            )

    record = save_profile(
        session,
        nursery_ref=current_user.nursery_ref,
        actor_ref=current_user.actor_ref,
        profile=profile,
        approve=approve,
    )
    return RedirectResponse(url=f"/nursery-profile/?saved=1&version={record.version}", status_code=303)
