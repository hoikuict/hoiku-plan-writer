from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import get_current_staff_user, require_admin, require_can_edit, require_classroom_access
from ...db import get_session
from ...domain.models import DocumentStatus
from ...persistence.repositories import (
    get_document,
    list_documents,
    update_document_content,
    update_document_status,
)
from ..templating import is_htmx_request, render_template

router = APIRouter(prefix="/documents", tags=["documents"])

STATUS_OPTIONS = [
    {"value": "all", "label": "すべて"},
    {"value": "draft", "label": "下書き"},
    {"value": "submitted", "label": "送信済み"},
    {"value": "returned", "label": "差戻し"},
    {"value": "approved", "label": "承認済み"},
]

TYPE_OPTIONS = [
    {"value": "all", "label": "すべて"},
    {"value": "annual", "label": "年間指導計画"},
    {"value": "monthly", "label": "月案"},
]


@router.get("/", response_class=HTMLResponse)
def document_list(
    request: Request,
    status: str = "all",
    document_type: str = "all",
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    documents = list_documents(
        session,
        nursery_ref=current_user.nursery_ref,
        classroom_refs=current_user.classroom_refs,
        status_filter=status,
        document_type_filter=document_type,
    )

    template_name = "documents/_list.html" if is_htmx_request(request) else "documents/list.html"
    return render_template(
        request,
        template_name,
        current_user=current_user,
        documents=documents,
        status_filter=status,
        document_type_filter=document_type,
        status_options=STATUS_OPTIONS,
        type_options=TYPE_OPTIONS,
    )


@router.get("/{document_id}", response_class=HTMLResponse)
def document_detail(
    request: Request,
    document_id: int,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    document = get_document(session, document_id, nursery_ref=current_user.nursery_ref)
    if not document:
        raise HTTPException(status_code=404, detail="文書が見つかりません")
    require_classroom_access(current_user, document.classroom_ref)

    related_document = None
    if document.related_document_id is not None:
        related_document = get_document(session, document.related_document_id, nursery_ref=current_user.nursery_ref)

    return render_template(
        request,
        "documents/detail.html",
        current_user=current_user,
        document=document,
        related_document=related_document,
        result=request.query_params.get("result", ""),
    )


@router.post("/{document_id}/edit")
async def edit_document(
    document_id: int,
    request: Request,
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_can_edit(current_user)
    document = get_document(session, document_id, nursery_ref=current_user.nursery_ref)
    if not document:
        raise HTTPException(status_code=404, detail="文書が見つかりません")
    require_classroom_access(current_user, document.classroom_ref)
    if document.status == DocumentStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="承認済み文書は編集できません")

    form = await request.form()
    action = str(form.get("action", "save_draft"))
    if action not in {"save_draft", "submit"}:
        raise HTTPException(status_code=400, detail="不正な操作です")

    title = str(form.get("title", document.title))
    comment = str(form.get("comment", ""))
    block_bodies_by_id = {
        int(block.id): str(form.get(f"block_body_{block.id}", block.body))
        for block in document.blocks
        if block.id is not None
    }
    updated_document, log_action = update_document_content(
        session,
        document=document,
        title=title,
        block_bodies_by_id=block_bodies_by_id,
        actor_ref=current_user.actor_ref,
        role=current_user.role.value,
        action=action,
        comment=comment,
    )
    result = {
        "saved_draft": "saved",
        "submitted": "submitted",
        "resubmitted": "resubmitted",
    }.get(log_action, "saved")
    return RedirectResponse(url=f"/documents/{updated_document.id}?result={result}", status_code=303)


@router.post("/{document_id}/status")
def change_document_status(
    document_id: int,
    action: str = Form("approve"),
    comment: str = Form(""),
    session=Depends(get_session),
    current_user=Depends(get_current_staff_user),
):
    require_admin(current_user)
    document = get_document(session, document_id, nursery_ref=current_user.nursery_ref)
    if not document:
        raise HTTPException(status_code=404, detail="文書が見つかりません")
    require_classroom_access(current_user, document.classroom_ref)
    if document.status != DocumentStatus.SUBMITTED.value:
        raise HTTPException(status_code=400, detail="送信済み文書のみ承認または差戻しできます")

    next_status = DocumentStatus.APPROVED if action == "approve" else DocumentStatus.RETURNED
    update_document_status(
        session,
        document=document,
        status=next_status,
        actor_ref=current_user.actor_ref,
        role=current_user.role.value,
        comment=comment,
    )
    return RedirectResponse(url=f"/documents/{document_id}", status_code=303)
