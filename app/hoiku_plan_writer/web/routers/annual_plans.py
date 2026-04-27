from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_can_edit, require_classroom_access
from ...db import get_session
from ...domain.models import DocumentStatus, DocumentType, GeneratedPlan
from ...persistence.repositories import (
    create_document,
    get_active_profile_record,
    list_profile_versions,
    profile_record_to_domain,
)
from ...services.generators import generate_annual_plan
from ...services.serializers import dict_to_plan, plan_to_dict
from ..forms import AnnualPlanFormData, annual_plan_form_data
from ..templating import is_htmx_request, render_template

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


def _render_form(
    request: Request,
    *,
    current_user,
    form_data: AnnualPlanFormData,
    active_profile,
    latest_profile_version,
    form_error: str,
    preview_plan=None,
    preview_error_message: str = "",
    preview_generation_note: str = "",
    use_llm_preview: bool | None = None,
    selected_ai_model: str | None = None,
):
    preview_service = request.app.state.annual_preview_service
    llm_preview_checked = preview_service.can_use_llm if use_llm_preview is None else use_llm_preview
    if not preview_service.can_use_llm:
        llm_preview_checked = False
    resolved_ai_model = preview_service.resolve_model_name(selected_ai_model)
    return render_template(
        request,
        "annual_plans/form.html",
        current_user=current_user,
        form_data=form_data,
        active_profile=active_profile,
        latest_profile_version=latest_profile_version,
        form_error=form_error,
        preview_plan=preview_plan,
        preview_error_message=preview_error_message,
        preview_generation_note=preview_generation_note,
        llm_preview_available=preview_service.can_use_llm,
        llm_preview_default_enabled=preview_service.can_use_llm,
        llm_preview_checked=llm_preview_checked,
        llm_preview_note=preview_service.availability_note,
        ai_model_options=preview_service.model_choices,
        selected_ai_model=resolved_ai_model,
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
    form_data: AnnualPlanFormData,
    active_profile,
    latest_profile_version,
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
        latest_profile_version=latest_profile_version,
        form_error="",
        preview_plan=plan,
        preview_error_message=error_message,
        preview_generation_note=generation_note,
        use_llm_preview=use_llm_preview,
        selected_ai_model=selected_ai_model,
    )


def _missing_profile_message(profile_versions) -> str:
    if profile_versions:
        latest_profile = profile_versions[0]
        return (
            f"園プロフィール v{latest_profile.version} / {latest_profile.nursery_name} は保存済みですが、"
            "まだ有効化されていません。年間指導計画には有効版のみ反映されます。管理者で有効化してください。"
        )
    return "先に有効な園プロファイルを登録してください。"


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
def new_annual_plan_form(
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    active_profile = get_active_profile_record(session, current_user.nursery_ref)
    profile_versions = list_profile_versions(session, current_user.nursery_ref)
    latest_profile_version = profile_versions[0] if profile_versions else None
    return _render_form(
        request,
        current_user=current_user,
        form_data=_default_form(current_user),
        active_profile=active_profile,
        latest_profile_version=latest_profile_version,
        form_error="",
    )


@router.post("/preview", response_class=HTMLResponse)
def preview_annual_plan(
    request: Request,
    form_data: AnnualPlanFormData = Depends(annual_plan_form_data),
    use_llm_preview: bool = Form(False),
    ai_model: str = Form(""),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    profile_record = get_active_profile_record(session, current_user.nursery_ref)
    if not profile_record:
        profile_versions = list_profile_versions(session, current_user.nursery_ref)
        latest_profile_version = profile_versions[0] if profile_versions else None
        return _render_preview_response(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=None,
            latest_profile_version=latest_profile_version,
            error_message=_missing_profile_message(profile_versions),
            use_llm_preview=use_llm_preview,
            selected_ai_model=ai_model,
        )

    preview_result = request.app.state.annual_preview_service.preview(
        profile=profile_record_to_domain(profile_record),
        plan_input=form_data.to_domain_input(),
        use_llm=use_llm_preview,
        selected_model=ai_model,
    )
    return _render_preview_response(
        request,
        current_user=current_user,
        form_data=form_data,
        active_profile=profile_record,
        latest_profile_version=profile_record,
        plan=preview_result.plan,
        generation_note=preview_result.note,
        use_llm_preview=use_llm_preview,
        selected_ai_model=preview_result.model_name or ai_model,
    )


@router.post("/")
def create_annual_plan(
    request: Request,
    form_data: AnnualPlanFormData = Depends(annual_plan_form_data),
    action: str = Form("save_rule_based"),
    preview_plan_json: str = Form(""),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    require_classroom_access(current_user, form_data.classroom_ref)
    profile_record = get_active_profile_record(session, current_user.nursery_ref)
    if not profile_record:
        profile_versions = list_profile_versions(session, current_user.nursery_ref)
        latest_profile_version = profile_versions[0] if profile_versions else None
        return _render_form(
            request,
            current_user=current_user,
            form_data=form_data,
            active_profile=None,
            latest_profile_version=latest_profile_version,
            form_error=_missing_profile_message(profile_versions),
        )

    profile = profile_record_to_domain(profile_record)
    if action == "adopt_preview":
        try:
            plan = _load_preview_plan(preview_plan_json, expected_type=DocumentType.ANNUAL)
        except (ValueError, json.JSONDecodeError):
            return _render_form(
                request,
                current_user=current_user,
                form_data=form_data,
                active_profile=profile_record,
                latest_profile_version=profile_record,
                form_error="プレビュー内容を読み込めませんでした。もう一度プレビューを作成してください。",
            )
    else:
        plan = generate_annual_plan(profile, form_data.to_domain_input())
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
