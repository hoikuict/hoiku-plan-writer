from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_admin, require_can_edit
from ...db import get_session
from ...domain.safety import (
    FacilityType,
    SafetyComplianceStandard,
    SafetyLogType,
    SafetyPlanStatus,
)
from ...persistence.repositories import get_active_profile_record, profile_record_to_domain
from ...persistence.safety_repositories import (
    add_safety_log,
    approve_safety_plan,
    create_safety_plan,
    get_safety_plan,
    list_safety_plans,
    safety_log_pairs,
)
from ...services.safety import evaluate_safety_compliance, generate_safety_plan
from ..forms import SafetyLogFormData, SafetyPlanFormData, safety_log_form_data, safety_plan_form_data
from ..templating import render_template

router = APIRouter(prefix="/safety-plans", tags=["safety-plans"])


FACILITY_TYPE_OPTIONS = [
    (FacilityType.NURSERY.value, "保育所"),
    (FacilityType.KINDERGARTEN.value, "幼稚園"),
    (FacilityType.CERTIFIED_CHILD_CENTER.value, "認定こども園"),
    (FacilityType.HOME_BASED.value, "家庭的保育事業所"),
    (FacilityType.SMALL_SCALE.value, "小規模保育事業所"),
    (FacilityType.WORKPLACE.value, "事業所内保育事業所"),
    (FacilityType.HOME_VISIT.value, "居宅訪問型保育事業所"),
]


def _default_form(active_profile) -> SafetyPlanFormData:
    return SafetyPlanFormData(
        school_year=date.today().year,
        established_on_raw=date.today().isoformat(),
        facility_type=FacilityType.NURSERY.value,
        facility_name=getattr(active_profile, "nursery_name", "") or "",
        municipality="",
        capacity_summary=getattr(active_profile, "class_configuration", "") or "",
        age_groups=getattr(active_profile, "target_age_group", "") or "",
        has_bus=False,
        has_outdoor_activity=True,
        has_pool=False,
        has_kitchen=True,
        disaster_risks=getattr(active_profile, "local_context", "") or "",
        staff_counts="",
        outdoor_routes=getattr(active_profile, "community_resources", "") or "",
        safety_policy=getattr(active_profile, "health_and_safety_policy", "") or "",
    )


@router.get("/", response_class=HTMLResponse)
def list_safety_plan_page(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    plans = list_safety_plans(session, nursery_ref=current_user.nursery_ref)
    compliance_by_plan_id = {
        plan.id: _evaluate_plan(plan)
        for plan in plans
        if plan.id is not None
    }
    return render_template(
        request,
        "safety_plans/list.html",
        current_user=current_user,
        plans=plans,
        compliance_by_plan_id=compliance_by_plan_id,
    )


@router.get("/new", response_class=HTMLResponse)
def new_safety_plan_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_admin(current_user)
    active_profile = get_active_profile_record(session, current_user.nursery_ref)
    form_data = _default_form(active_profile)
    return _render_form(
        request,
        current_user=current_user,
        form_data=form_data,
        active_profile=active_profile,
        form_error="",
    )


@router.post("/preview", response_class=HTMLResponse)
def preview_safety_plan(
    request: Request,
    form_data: SafetyPlanFormData = Depends(safety_plan_form_data),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_admin(current_user)
    active_profile_record = get_active_profile_record(session, current_user.nursery_ref)
    active_profile = profile_record_to_domain(active_profile_record) if active_profile_record else None
    draft = generate_safety_plan(
        active_profile,
        form_data.to_facility_profile(),
        school_year=form_data.school_year,
        established_on=form_data.established_on,
    )
    return _render_form(
        request,
        current_user=current_user,
        form_data=form_data,
        active_profile=active_profile_record,
        form_error="",
        preview_plan=draft,
    )


@router.post("/")
def create_safety_plan_page(
    request: Request,
    form_data: SafetyPlanFormData = Depends(safety_plan_form_data),
    action: str = Form("save_draft"),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_admin(current_user)
    active_profile_record = get_active_profile_record(session, current_user.nursery_ref)
    active_profile = profile_record_to_domain(active_profile_record) if active_profile_record else None
    draft = generate_safety_plan(
        active_profile,
        form_data.to_facility_profile(),
        school_year=form_data.school_year,
        established_on=form_data.established_on,
    )
    if action == "approve" and draft.missing_inputs:
        return _render_form(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=active_profile_record,
            form_error="未入力項目があるため承認保存できません。確認してから再度保存してください。",
            preview_plan=draft,
        )
    plan = create_safety_plan(
        session,
        draft=draft,
        nursery_ref=current_user.nursery_ref,
        actor_ref=current_user.actor_ref,
        input_snapshot=form_data.as_snapshot(),
        approve=action == "approve",
    )
    return RedirectResponse(url=f"/safety-plans/{plan.id}", status_code=303)


@router.get("/{plan_id}", response_class=HTMLResponse)
def safety_plan_detail(
    plan_id: int,
    request: Request,
    result: str = "",
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    plan = _get_plan_or_404(session, plan_id, current_user.nursery_ref)
    return _render_detail(request, current_user=current_user, plan=plan, result=result)


@router.post("/{plan_id}/approve")
def approve_safety_plan_page(
    plan_id: int,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_admin(current_user)
    plan = _get_plan_or_404(session, plan_id, current_user.nursery_ref)
    if plan.missing_inputs_json:
        return RedirectResponse(url=f"/safety-plans/{plan.id}?result=missing", status_code=303)
    approve_safety_plan(session, plan=plan, actor_ref=current_user.actor_ref)
    return RedirectResponse(url=f"/safety-plans/{plan.id}?result=approved", status_code=303)


@router.post("/{plan_id}/logs")
def add_safety_log_page(
    plan_id: int,
    form_data: SafetyLogFormData = Depends(safety_log_form_data),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    plan = _get_plan_or_404(session, plan_id, current_user.nursery_ref)
    if not form_data.title.strip() or form_data.implemented_on is None:
        return RedirectResponse(url=f"/safety-plans/{plan.id}?result=log_error", status_code=303)
    add_safety_log(
        session,
        plan=plan,
        log_type=form_data.parsed_log_type,
        implemented_on=form_data.implemented_on,
        title=form_data.title,
        participants=form_data.participants,
        method=form_data.method,
        evidence_note=form_data.evidence_note,
        evidence_file_ref=form_data.evidence_file_ref,
        actor_ref=current_user.actor_ref,
        related_action_id=form_data.related_action_id,
    )
    return RedirectResponse(url=f"/safety-plans/{plan.id}?result=log_created", status_code=303)


def _render_form(
    request: Request,
    *,
    current_user,
    form_data: SafetyPlanFormData,
    active_profile,
    form_error: str,
    preview_plan=None,
):
    return render_template(
        request,
        "safety_plans/form.html",
        current_user=current_user,
        form_data=form_data,
        active_profile=active_profile,
        form_error=form_error,
        preview_plan=preview_plan,
        facility_type_options=FACILITY_TYPE_OPTIONS,
    )


def _render_detail(request: Request, *, current_user, plan, result: str):
    compliance = _evaluate_plan(plan)
    return render_template(
        request,
        "safety_plans/detail.html",
        current_user=current_user,
        plan=plan,
        result=result,
        compliance=compliance,
        log_type_options=_log_type_options(plan),
    )


def _get_plan_or_404(session, plan_id: int, nursery_ref: str):
    plan = get_safety_plan(session, plan_id, nursery_ref=nursery_ref)
    if not plan:
        raise HTTPException(status_code=404, detail="安全計画が見つかりません")
    return plan


def _evaluate_plan(plan):
    try:
        compliance_standard = SafetyComplianceStandard(plan.compliance_standard)
    except ValueError:
        compliance_standard = SafetyComplianceStandard.CHILD_WELFARE
    try:
        status = SafetyPlanStatus(plan.status)
    except ValueError:
        status = SafetyPlanStatus.DRAFT
    return evaluate_safety_compliance(
        compliance_standard=compliance_standard,
        status=status,
        established_on=plan.established_on,
        section_keys=[block.section_key for block in plan.blocks],
        logs=safety_log_pairs(plan),
        today=date.today(),
    )


def _log_type_options(plan) -> list[tuple[str, str]]:
    if plan.compliance_standard == SafetyComplianceStandard.SCHOOL_SAFETY.value:
        return [(SafetyLogType.SCHOOL_SAFETY_ACTION.value, "学校安全計画の取組")]
    return [
        (SafetyLogType.TRAINING_DRILL.value, "研修・訓練"),
        (SafetyLogType.PARENT_NOTICE.value, "保護者周知"),
        (SafetyLogType.REVIEW.value, "見直し"),
        (SafetyLogType.SAFETY_INSPECTION.value, "安全点検"),
        (SafetyLogType.CHILD_GUIDANCE.value, "児童への安全指導"),
        (SafetyLogType.MANUAL_UPDATE.value, "マニュアル更新"),
        (SafetyLogType.INCIDENT_REFLECTION.value, "事故・ヒヤリ・ハット反映"),
    ]
