from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .profile_fields import PROFILE_DEFAULT_ENABLED_KEYS, normalize_enabled_field_keys


class Role(StrEnum):
    ADMIN = "admin"
    TEACHER = "teacher"


class DocumentType(StrEnum):
    ANNUAL = "annual"
    MONTHLY = "monthly"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    RETURNED = "returned"


class EvidenceTag(StrEnum):
    NURSERY_POLICY = "園方針"
    PUBLIC_GUIDANCE = "公的根拠"
    USER_INPUT = "入力"
    AI_COMPOSITION = "AI構成"


@dataclass(slots=True)
class SourceRef:
    kind: str
    ref: str
    label: str


@dataclass(slots=True)
class SectionBlock:
    section_key: str
    title: str
    body: str
    evidence_tags: list[EvidenceTag] = field(default_factory=list)
    source_refs: list[SourceRef] = field(default_factory=list)
    needs_confirmation: bool = False
    editor_note: str | None = None


@dataclass(slots=True)
class NurseryProfile:
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
    approved: bool = True
    version: int = 1
    enabled_field_keys: tuple[str, ...] = PROFILE_DEFAULT_ENABLED_KEYS

    def __post_init__(self) -> None:
        self.enabled_field_keys = normalize_enabled_field_keys(self.enabled_field_keys)

    def is_field_enabled(self, field_key: str) -> bool:
        return field_key in self.enabled_field_keys

    def text_for(self, field_key: str) -> str:
        if not self.is_field_enabled(field_key):
            return ""
        return str(getattr(self, field_key, "") or "")


@dataclass(slots=True)
class AnnualPlanInput:
    school_year: int
    class_name: str
    age_group: str
    class_outlook: str
    focus_growth: str
    annual_events: str = ""
    seasonal_context: str = ""
    community_resources: str = ""
    care_points: str = ""
    handover_notes: str = ""


@dataclass(slots=True)
class MonthlyPlanInput:
    target_month: str
    class_name: str
    owner_name: str
    related_term_key: str
    previous_reflection: str
    current_children_snapshot: str
    play_interests: str = ""
    seasonal_context: str = ""
    family_context: str = ""
    class_notes: str = ""


@dataclass(slots=True)
class GeneratedPlan:
    document_type: DocumentType
    title: str
    status: DocumentStatus
    blocks: list[SectionBlock]
    missing_inputs: list[str] = field(default_factory=list)
