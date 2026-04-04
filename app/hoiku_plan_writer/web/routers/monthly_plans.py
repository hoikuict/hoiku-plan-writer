from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_can_edit, require_classroom_access
from ...db import get_session
from ...domain.section_catalog import ANNUAL_TERM_ORDER
from ...persistence.repositories import (
    create_document,
    document_record_to_domain,
    get_active_profile_record,
    get_document,
    list_documents,
    profile_record_to_domain,
)
from ...services.generators import generate_monthly_plan
from ..forms import MonthlyPlanFormData, monthly_plan_form_data
from ..templating import render_template

router = APIRouter(prefix="/monthly-plans", tags=["monthly-plans"])
TERM_OPTIONS = [{"value": key, "label": label} for key, label in ANNUAL_TERM_ORDER]


def _default_form(current_user) -> MonthlyPlanFormData:
    classroom_ref = current_user.classroom_refs[0] if current_user.classroom_refs else "classroom:5yo-a"
    return MonthlyPlanFormData(
        classroom_ref=classroom_ref,
        target_month=date.today().strftime("%Y-%m"),
        class_name="5歳児",
        owner_name=current_user.name,
        related_annual_plan_id=None,
        related_term_key="term_1",
        previous_reflection="",
        current_children_snapshot="",
    )


def _annual_plan_options(session, current_user):
    return list_documents(
        session,
        nursery_ref=current_user.nursery_ref,
        classroom_refs=current_user.classroom_refs,
        document_type_filter="annual",
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
def new_monthly_plan_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    return render_template(
        request,
        "monthly_plans/form.html",
        current_user=current_user,
        form_data=_default_form(current_user),
        active_profile=get_active_profile_record(session, current_user.nursery_ref),
        annual_plan_options=_annual_plan_options(session, current_user),
        term_options=TERM_OPTIONS,
        form_error="",
    )


@router.post("/preview", response_class=HTMLResponse)
def preview_monthly_plan(
    request: Request,
    form_data: MonthlyPlanFormData = Depends(monthly_plan_form_data),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    profile_record = get_active_profile_record(session, current_user.nursery_ref)
    if not profile_record:
        return _preview_context(request, current_user, error_message="先に有効な園プロファイルを登録してください。")
    if form_data.related_annual_plan_id is None:
        return _preview_context(request, current_user, error_message="関連する年間指導計画を選択してください。")

    annual_document = get_document(
        session,
        form_data.related_annual_plan_id,
        nursery_ref=current_user.nursery_ref,
    )
    if not annual_document:
        return _preview_context(request, current_user, error_message="関連する年間指導計画が見つかりません。")
    require_classroom_access(current_user, annual_document.classroom_ref)

    plan = generate_monthly_plan(
        profile=profile_record_to_domain(profile_record),
        annual_plan=document_record_to_domain(annual_document),
        plan_input=form_data.to_domain_input(),
    )
    return _preview_context(request, current_user, plan=plan)


@router.post("/")
def create_monthly_plan(
    request: Request,
    form_data: MonthlyPlanFormData = Depends(monthly_plan_form_data),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    profile_record = get_active_profile_record(session, current_user.nursery_ref)
    annual_plan_options = _annual_plan_options(session, current_user)

    if not profile_record:
        return render_template(
            request,
            "monthly_plans/form.html",
            current_user=current_user,
            form_data=form_data,
            active_profile=None,
            annual_plan_options=annual_plan_options,
            term_options=TERM_OPTIONS,
            form_error="有効な園プロファイルが必要です。",
        )
    if form_data.related_annual_plan_id is None:
        return render_template(
            request,
            "monthly_plans/form.html",
            current_user=current_user,
            form_data=form_data,
            active_profile=profile_record,
            annual_plan_options=annual_plan_options,
            term_options=TERM_OPTIONS,
            form_error="関連する年間指導計画を選択してください。",
        )

    annual_document = get_document(
        session,
        form_data.related_annual_plan_id,
        nursery_ref=current_user.nursery_ref,
    )
    if not annual_document:
        return render_template(
            request,
            "monthly_plans/form.html",
            current_user=current_user,
            form_data=form_data,
            active_profile=profile_record,
            annual_plan_options=annual_plan_options,
            term_options=TERM_OPTIONS,
            form_error="関連する年間指導計画が見つかりません。",
        )
    require_classroom_access(current_user, annual_document.classroom_ref)

    plan = generate_monthly_plan(
        profile=profile_record_to_domain(profile_record),
        annual_plan=document_record_to_domain(annual_document),
        plan_input=form_data.to_domain_input(),
    )
    document = create_document(
        session,
        generated_plan=plan,
        nursery_ref=current_user.nursery_ref,
        classroom_ref=form_data.classroom_ref,
        actor_ref=current_user.actor_ref,
        school_year=None,
        target_month=form_data.target_month,
        related_document_id=annual_document.id,
        input_snapshot=form_data.as_snapshot(),
        role=current_user.role.value,
    )
    return RedirectResponse(url=f"/documents/{document.id}", status_code=303)
