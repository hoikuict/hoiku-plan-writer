from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_can_edit, require_classroom_access
from ...db import get_session
from ...persistence.repositories import create_document, get_active_profile_record, get_usable_profile_record, profile_record_to_domain
from ...services.generators import generate_annual_plan
from ..forms import AnnualPlanFormData, annual_plan_form_data
from ..templating import render_template

router = APIRouter(prefix="/annual-plans", tags=["annual-plans"])


def _default_form(current_user) -> AnnualPlanFormData:
    classroom_ref = current_user.classroom_refs[0] if current_user.classroom_refs else "classroom:5yo-a"
    return AnnualPlanFormData(
        classroom_ref=classroom_ref,
        school_year=date.today().year,
        class_name="5歳児",
        age_group="5歳児",
        class_outlook="",
        focus_growth="",
    )


def _preview_context(request: Request, current_user, plan=None, error_message: str = ""):
    return render_template(
        request,
        "documents/_preview.html",
        current_user=current_user,
        plan=plan,
        error_message=error_message,
    )


@router.get("/new", response_class=HTMLResponse)
def new_annual_plan_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    return render_template(
        request,
        "annual_plans/form.html",
        current_user=current_user,
        form_data=_default_form(current_user),
        active_profile=get_active_profile_record(session, current_user.nursery_ref),
        usable_profile=get_usable_profile_record(session, current_user.nursery_ref),
        form_error="",
    )


@router.post("/preview", response_class=HTMLResponse)
def preview_annual_plan(
    request: Request,
    form_data: AnnualPlanFormData = Depends(annual_plan_form_data),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    profile_record = get_usable_profile_record(session, current_user.nursery_ref)
    if not profile_record:
        return _preview_context(request, current_user, error_message="先に園プロファイルを登録してください。")

    plan = generate_annual_plan(profile_record_to_domain(profile_record), form_data.to_domain_input())
    return _preview_context(request, current_user, plan=plan)


@router.post("/")
def create_annual_plan(
    request: Request,
    form_data: AnnualPlanFormData = Depends(annual_plan_form_data),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    active_profile = get_active_profile_record(session, current_user.nursery_ref)
    profile_record = get_usable_profile_record(session, current_user.nursery_ref)
    if not profile_record:
        return render_template(
            request,
            "annual_plans/form.html",
            current_user=current_user,
            form_data=form_data,
            active_profile=None,
            usable_profile=None,
            form_error="先に園プロファイルを登録してください。",
        )

    plan = generate_annual_plan(profile_record_to_domain(profile_record), form_data.to_domain_input())
    document = create_document(
        session,
        generated_plan=plan,
        nursery_ref=current_user.nursery_ref,
        classroom_ref=form_data.classroom_ref,
        actor_ref=current_user.actor_ref,
        school_year=form_data.school_year,
        target_month=None,
        related_document_id=None,
        input_snapshot=form_data.as_snapshot(),
        role=current_user.role.value,
    )
    return RedirectResponse(url=f"/documents/{document.id}", status_code=303)
