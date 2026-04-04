from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from ..time_utils import utc_now


class NurseryProfileRecord(SQLModel, table=True):
    __tablename__ = "nursery_profiles"
    __table_args__ = (UniqueConstraint("nursery_ref", "version"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    nursery_ref: str = Field(index=True)
    actor_ref: str = Field(index=True)
    version: int = Field(index=True)
    approved: bool = Field(default=False, index=True)
    nursery_name: str
    target_age_group: str
    class_configuration: str
    philosophy: str
    childcare_goal: str
    desired_child_image: str
    child_view: str
    play_view: str
    support_policy: str
    indoor_environment: str = ""
    outdoor_environment: str = ""
    corner_play: str = ""
    community_resources: str = ""
    family_collaboration_policy: str = ""
    local_collaboration_policy: str = ""
    health_and_safety_policy: str = ""
    inclusive_policy: str = ""
    preferred_expressions: str = ""
    avoid_expressions: str = ""
    sentence_tone: str = ""
    missing_input_policy: str = "未入力は要確認として扱う。"
    confirmation_marker: str = "要確認"
    evidence_tag_policy: str = "根拠タグを表示する。"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PlanDocumentRecord(SQLModel, table=True):
    __tablename__ = "plan_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_type: str = Field(index=True)
    title: str
    status: str = Field(index=True)
    nursery_ref: str = Field(index=True)
    classroom_ref: str = Field(index=True)
    actor_ref: str = Field(index=True)
    school_year: Optional[int] = Field(default=None, index=True)
    target_month: Optional[str] = Field(default=None, index=True)
    related_document_id: Optional[int] = Field(default=None, foreign_key="plan_documents.id")
    missing_inputs_json: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    source_refs_json: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    input_snapshot_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    approved_by_actor_ref: Optional[str] = Field(default=None, index=True)
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)

    blocks: list["PlanBlockRecord"] = Relationship(back_populates="document")
    approval_logs: list["ApprovalLogRecord"] = Relationship(back_populates="document")

    @property
    def document_type_label(self) -> str:
        return {
            "annual": "年間指導計画",
            "monthly": "月案",
        }.get(self.document_type, self.document_type)

    @property
    def status_label(self) -> str:
        return {
            "draft": "下書き",
            "approved": "承認済み",
            "returned": "差戻し",
        }.get(self.status, self.status)


class PlanBlockRecord(SQLModel, table=True):
    __tablename__ = "plan_blocks"
    __table_args__ = (UniqueConstraint("document_id", "section_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="plan_documents.id", index=True)
    sort_order: int = Field(default=0, index=True)
    section_key: str = Field(index=True)
    title: str
    body: str
    evidence_tags_json: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    source_refs_json: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    needs_confirmation: bool = Field(default=False, index=True)
    editor_note: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    document: PlanDocumentRecord = Relationship(back_populates="blocks")


class ApprovalLogRecord(SQLModel, table=True):
    __tablename__ = "approval_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="plan_documents.id", index=True)
    action: str = Field(index=True)
    actor_ref: str = Field(index=True)
    role: str
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now, index=True)

    document: PlanDocumentRecord = Relationship(back_populates="approval_logs")

    @property
    def action_label(self) -> str:
        return {
            "created": "作成",
            "approved": "承認",
            "returned": "差戻し",
        }.get(self.action, self.action)

