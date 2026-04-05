from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_admin, require_can_edit
from ...db import get_session
from ...domain.profile_fields import PROFILE_DEFAULT_ENABLED_KEYS, PROFILE_FIELD_SECTIONS
from ...persistence.models import NurseryProfileRecord
from ...persistence.repositories import (
    activate_profile_version,
    get_active_profile_record,
    list_profile_versions,
    save_profile,
)
from ..forms import ProfileFormData, profile_form_data
from ..templating import render_template

router = APIRouter(prefix="/nursery-profile", tags=["nursery-profile"])


def _enabled_keys_from_record(record: NurseryProfileRecord | None) -> tuple[str, ...]:
    if not record:
        return PROFILE_DEFAULT_ENABLED_KEYS
    stored_keys = record.enabled_field_keys_json or []
    if stored_keys:
        return tuple(str(item) for item in stored_keys)
    return PROFILE_DEFAULT_ENABLED_KEYS


def _form_from_record(record: NurseryProfileRecord | None) -> ProfileFormData:
    enabled_field_keys = _enabled_keys_from_record(record)
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
            enabled_field_keys=enabled_field_keys,
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
        enabled_field_keys=enabled_field_keys,
    )


@router.get("/", response_class=HTMLResponse)
def nursery_profile_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    active_profile = get_active_profile_record(session, current_user.nursery_ref)
    profile_versions = list_profile_versions(session, current_user.nursery_ref)
    form_record = active_profile or (profile_versions[0] if profile_versions else None)
    form_data = _form_from_record(form_record)
    return render_template(
        request,
        "nursery_profiles/form.html",
        current_user=current_user,
        form_data=form_data,
        form_values=form_data.as_snapshot(),
        active_profile=active_profile,
        profile_versions=profile_versions,
        profile_field_sections=PROFILE_FIELD_SECTIONS,
        saved=request.query_params.get("saved") == "1",
        activated=request.query_params.get("activated") == "1",
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


@router.post("/{profile_id}/activate")
def activate_saved_profile(
    profile_id: int,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_admin(current_user)
    record = activate_profile_version(
        session,
        profile_id=profile_id,
        nursery_ref=current_user.nursery_ref,
    )
    if not record:
        raise HTTPException(status_code=404, detail="園プロファイルが見つかりません")
    return RedirectResponse(url=f"/nursery-profile/?activated=1&version={record.version}", status_code=303)
