from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_can_edit, require_classroom_access
from ...db import get_session
from ...domain.models import DocumentStatus, DocumentType, GeneratedPlan
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
from ...services.serializers import dict_to_plan, plan_to_dict
from ..forms import MonthlyPlanFormData, monthly_plan_form_data
from ..templating import is_htmx_request, render_template

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


def _render_form(
    request: Request,
    *,
    current_user,
    form_data: MonthlyPlanFormData,
    active_profile,
    annual_plan_options,
    form_error: str,
    preview_plan=None,
    preview_error_message: str = "",
    preview_generation_note: str = "",
    use_llm_preview: bool | None = None,
    selected_ai_model: str | None = None,
):
    preview_service = request.app.state.annual_preview_service
    llm_preview_checked = preview_service.can_use_monthly_llm if use_llm_preview is None else use_llm_preview
    if not preview_service.can_use_monthly_llm:
        llm_preview_checked = False
    return render_template(
        request,
        "monthly_plans/form.html",
        current_user=current_user,
        form_data=form_data,
        active_profile=active_profile,
        annual_plan_options=annual_plan_options,
        term_options=TERM_OPTIONS,
        form_error=form_error,
        preview_plan=preview_plan,
        preview_error_message=preview_error_message,
        preview_generation_note=preview_generation_note,
        llm_preview_available=preview_service.can_use_monthly_llm,
        llm_preview_checked=llm_preview_checked,
        llm_preview_note=preview_service.monthly_availability_note,
        ai_model_options=preview_service.model_choices,
        selected_ai_model=preview_service.resolve_model_name(selected_ai_model),
        preview_plan_json=_preview_plan_json(preview_plan),
    )


def _preview_context(
    request: Request,
    current_user,
    plan=None,
    error_message: str = "",
    generation_note: str = "",
):
    return render_template(
        request,
        "documents/_preview.html",
        current_user=current_user,
        plan=plan,
        error_message=error_message,
        generation_note=generation_note,
    )


def _render_preview_response(
    request: Request,
    *,
    current_user,
    form_data: MonthlyPlanFormData,
    active_profile,
    annual_plan_options,
    plan=None,
    error_message: str = "",
    generation_note: str = "",
    use_llm_preview: bool,
    selected_ai_model: str | None = None,
):
    if is_htmx_request(request):
        return _preview_context(
            request,
            current_user,
            plan=plan,
            error_message=error_message,
            generation_note=generation_note,
        )
    return _render_form(
        request,
        current_user=current_user,
        form_data=form_data,
        active_profile=active_profile,
        annual_plan_options=annual_plan_options,
        form_error="",
        preview_plan=plan,
        preview_error_message=error_message,
        preview_generation_note=generation_note,
        use_llm_preview=use_llm_preview,
        selected_ai_model=selected_ai_model,
    )


def _preview_plan_json(plan: GeneratedPlan | None) -> str:
    if plan is None:
        return ""
    return json.dumps(plan_to_dict(plan), ensure_ascii=False)


def _load_preview_plan(raw_payload: str, *, expected_type: DocumentType) -> GeneratedPlan:
    if not raw_payload.strip():
        raise ValueError("preview payload is empty")
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("preview payload must be an object")
    plan = dict_to_plan(payload)
    if plan.document_type != expected_type:
        raise ValueError("preview document type does not match the form")
    plan.status = DocumentStatus.DRAFT
    return plan


@router.get("/new", response_class=HTMLResponse)
def new_monthly_plan_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    return _render_form(
        request,
        current_user=current_user,
        form_data=_default_form(current_user),
        active_profile=get_active_profile_record(session, current_user.nursery_ref),
        annual_plan_options=_annual_plan_options(session, current_user),
        form_error="",
    )


@router.post("/preview", response_class=HTMLResponse)
def preview_monthly_plan(
    request: Request,
    form_data: MonthlyPlanFormData = Depends(monthly_plan_form_data),
    use_llm_preview: bool = Form(False),
    ai_model: str = Form(""),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    annual_plan_options = _annual_plan_options(session, current_user)
    profile_record = get_active_profile_record(session, current_user.nursery_ref)
    if not profile_record:
        return _render_preview_response(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=None,
            annual_plan_options=annual_plan_options,
            error_message="先に有効な園プロファイルを登録してください。",
            use_llm_preview=use_llm_preview,
            selected_ai_model=ai_model,
        )
    if form_data.related_annual_plan_id is None:
        return _render_preview_response(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=profile_record,
            annual_plan_options=annual_plan_options,
            error_message="関連する年間指導計画を選択してください。",
            use_llm_preview=use_llm_preview,
            selected_ai_model=ai_model,
        )

    annual_document = get_document(
        session,
        form_data.related_annual_plan_id,
        nursery_ref=current_user.nursery_ref,
    )
    if not annual_document:
        return _render_preview_response(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=profile_record,
            annual_plan_options=annual_plan_options,
            error_message="関連する年間指導計画が見つかりません。",
            use_llm_preview=use_llm_preview,
            selected_ai_model=ai_model,
        )
    require_classroom_access(current_user, annual_document.classroom_ref)

    preview_result = request.app.state.annual_preview_service.preview_monthly(
        profile=profile_record_to_domain(profile_record),
        annual_plan=document_record_to_domain(annual_document),
        plan_input=form_data.to_domain_input(),
        use_llm=use_llm_preview,
        selected_model=ai_model,
    )
    return _render_preview_response(
        request,
        current_user=current_user,
        form_data=form_data,
        active_profile=profile_record,
        annual_plan_options=annual_plan_options,
        plan=preview_result.plan,
        generation_note=preview_result.note,
        use_llm_preview=use_llm_preview,
        selected_ai_model=preview_result.model_name or ai_model,
    )


@router.post("/")
def create_monthly_plan(
    request: Request,
    form_data: MonthlyPlanFormData = Depends(monthly_plan_form_data),
    action: str = Form("save_rule_based"),
    preview_plan_json: str = Form(""),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    profile_record = get_active_profile_record(session, current_user.nursery_ref)
    annual_plan_options = _annual_plan_options(session, current_user)

    if not profile_record:
        return _render_form(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=None,
            annual_plan_options=annual_plan_options,
            form_error="有効な園プロファイルが必要です。",
        )
    if form_data.related_annual_plan_id is None:
        return _render_form(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=profile_record,
            annual_plan_options=annual_plan_options,
            form_error="関連する年間指導計画を選択してください。",
        )

    annual_document = get_document(
        session,
        form_data.related_annual_plan_id,
        nursery_ref=current_user.nursery_ref,
    )
    if not annual_document:
        return _render_form(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=profile_record,
            annual_plan_options=annual_plan_options,
            form_error="関連する年間指導計画が見つかりません。",
        )
    require_classroom_access(current_user, annual_document.classroom_ref)

    profile = profile_record_to_domain(profile_record)
    annual_plan = document_record_to_domain(annual_document)
    if action == "adopt_preview":
        try:
            plan = _load_preview_plan(preview_plan_json, expected_type=DocumentType.MONTHLY)
        except (ValueError, json.JSONDecodeError):
            return _render_form(
                request,
                current_user=current_user,
                form_data=form_data,
                active_profile=profile_record,
                annual_plan_options=annual_plan_options,
                form_error="プレビュー内容を読み込めませんでした。もう一度プレビューを作成してください。",
            )
    else:
        plan = generate_monthly_plan(
            profile=profile,
            annual_plan=annual_plan,
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
