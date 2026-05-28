from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_admin, require_can_edit
from ...db import get_session
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
        philosophy=record.philosophy,
        childcare_goal=record.childcare_goal,
        desired_child_image=record.desired_child_image,
        child_view=record.child_view,
        play_view=record.play_view,
        support_policy=record.support_policy,
        indoor_environment=record.indoor_environment,
        outdoor_environment=record.outdoor_environment,
        corner_play=record.corner_play,
        community_resources=record.community_resources,
        family_collaboration_policy=record.family_collaboration_policy,
        local_collaboration_policy=record.local_collaboration_policy,
        health_and_safety_policy=record.health_and_safety_policy,
        inclusive_policy=record.inclusive_policy,
        preferred_expressions=record.preferred_expressions,
        avoid_expressions=record.avoid_expressions,
        sentence_tone=record.sentence_tone,
        missing_input_policy=record.missing_input_policy,
        confirmation_marker=record.confirmation_marker,
        evidence_tag_policy=record.evidence_tag_policy,
    )


@router.get("/", response_class=HTMLResponse)
def nursery_profile_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    active_profile = get_active_profile_record(session, current_user.nursery_ref)
    versions = list_profile_versions(session, current_user.nursery_ref)
    latest_profile = versions[0] if versions else None
    return render_template(
        request,
        "nursery_profiles/form.html",
        current_user=current_user,
        form_data=_form_from_record(latest_profile),
        active_profile=active_profile,
        profile_versions=versions,
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
    approve = action == "activate"
    if approve:
        require_admin(current_user)

    record = save_profile(
        session,
        nursery_ref=current_user.nursery_ref,
        actor_ref=current_user.actor_ref,
        profile=form_data.to_domain(approved=approve),
        approve=approve,
    )
    return RedirectResponse(url=f"/nursery-profile/?saved=1&version={record.version}", status_code=303)
