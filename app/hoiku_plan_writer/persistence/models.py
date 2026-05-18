from datetime import date, datetime
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
    local_context: str = ""
    philosophy: str
    childcare_goal: str
    desired_child_image: str
    child_view: str
    play_view: str
    support_policy: str
    curriculum_focus: str = ""
    assessment_policy: str = ""
    indoor_environment: str = ""
    outdoor_environment: str = ""
    corner_play: str = ""
    community_resources: str = ""
    family_collaboration_policy: str = ""
    local_collaboration_policy: str = ""
    health_and_safety_policy: str = ""
    inclusive_policy: str = ""
    daily_rhythm: str = ""
    preferred_expressions: str = ""
    avoid_expressions: str = ""
    sentence_tone: str = ""
    document_format_notes: str = ""
    missing_input_policy: str = "未入力は要確認として扱う。"
    confirmation_marker: str = "要確認"
    evidence_tag_policy: str = "根拠タグを表示する。"
    privacy_policy: str = "個人名、診断名、健康詳細、家庭の詳細事情は入力・出力に含めない。"
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
            "submitted": "送信済み",
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
            "saved_draft": "下書き保存",
            "submitted": "送信",
            "resubmitted": "再送信",
            "approved": "承認",
            "returned": "差戻し",
        }.get(self.action, self.action)


class SafetyPlanRecord(SQLModel, table=True):
    __tablename__ = "safety_plans"

    id: Optional[int] = Field(default=None, primary_key=True)
    nursery_ref: str = Field(index=True)
    actor_ref: str = Field(index=True)
    facility_type: str = Field(index=True)
    compliance_standard: str = Field(index=True)
    school_year: int = Field(index=True)
    title: str
    status: str = Field(default="draft", index=True)
    established_on: Optional[date] = Field(default=None, index=True)
    approved_by_actor_ref: Optional[str] = Field(default=None, index=True)
    approved_at: Optional[datetime] = None
    missing_inputs_json: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    source_refs_json: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    input_snapshot_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)

    blocks: list["SafetyPlanBlockRecord"] = Relationship(back_populates="plan")
    action_items: list["SafetyActionItemRecord"] = Relationship(back_populates="plan")
    implementation_logs: list["SafetyImplementationLogRecord"] = Relationship(back_populates="plan")

    @property
    def facility_type_label(self) -> str:
        return {
            "kindergarten": "幼稚園",
            "nursery": "保育所",
            "certified_child_center": "認定こども園",
            "home_based": "家庭的保育事業所",
            "small_scale": "小規模保育事業所",
            "workplace": "事業所内保育事業所",
            "home_visit": "居宅訪問型保育事業所",
        }.get(self.facility_type, self.facility_type)

    @property
    def compliance_standard_label(self) -> str:
        if self.compliance_standard == "school_safety":
            return "学校安全計画"
        return "安全計画"

    @property
    def status_label(self) -> str:
        return {
            "draft": "下書き",
            "approved": "承認済み",
            "needs_review": "要見直し",
        }.get(self.status, self.status)


class SafetyPlanBlockRecord(SQLModel, table=True):
    __tablename__ = "safety_plan_blocks"
    __table_args__ = (UniqueConstraint("safety_plan_id", "section_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    safety_plan_id: int = Field(foreign_key="safety_plans.id", index=True)
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

    plan: SafetyPlanRecord = Relationship(back_populates="blocks")


class SafetyActionItemRecord(SQLModel, table=True):
    __tablename__ = "safety_action_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    safety_plan_id: int = Field(foreign_key="safety_plans.id", index=True)
    sort_order: int = Field(default=0, index=True)
    category: str = Field(index=True)
    title: str
    planned_month: str = ""
    responsible_role: str = ""
    recurrence: str = ""
    legal_axis: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    plan: SafetyPlanRecord = Relationship(back_populates="action_items")


class SafetyImplementationLogRecord(SQLModel, table=True):
    __tablename__ = "safety_implementation_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    safety_plan_id: int = Field(foreign_key="safety_plans.id", index=True)
    related_action_id: Optional[int] = Field(default=None, foreign_key="safety_action_items.id")
    log_type: str = Field(index=True)
    implemented_on: date = Field(index=True)
    title: str
    participants: str = ""
    method: str = ""
    evidence_note: str = ""
    evidence_file_ref: str = ""
    actor_ref: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)

    plan: SafetyPlanRecord = Relationship(back_populates="implementation_logs")

    @property
    def log_type_label(self) -> str:
        return {
            "training_drill": "研修・訓練",
            "parent_notice": "保護者周知",
            "review": "見直し",
            "school_safety_action": "学校安全計画の取組",
            "safety_inspection": "安全点検",
            "child_guidance": "児童への安全指導",
            "manual_update": "マニュアル更新",
            "incident_reflection": "事故・ヒヤリ・ハット反映",
        }.get(self.log_type, self.log_type)
