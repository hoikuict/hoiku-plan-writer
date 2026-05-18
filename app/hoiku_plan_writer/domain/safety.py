from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from .models import EvidenceTag, SectionBlock, SourceRef


class FacilityType(StrEnum):
    KINDERGARTEN = "kindergarten"
    NURSERY = "nursery"
    CERTIFIED_CHILD_CENTER = "certified_child_center"
    HOME_BASED = "home_based"
    SMALL_SCALE = "small_scale"
    WORKPLACE = "workplace"
    HOME_VISIT = "home_visit"


FACILITY_TYPE_LABELS = {
    FacilityType.KINDERGARTEN: "幼稚園",
    FacilityType.NURSERY: "保育所",
    FacilityType.CERTIFIED_CHILD_CENTER: "認定こども園",
    FacilityType.HOME_BASED: "家庭的保育事業所",
    FacilityType.SMALL_SCALE: "小規模保育事業所",
    FacilityType.WORKPLACE: "事業所内保育事業所",
    FacilityType.HOME_VISIT: "居宅訪問型保育事業所",
}


class SafetyComplianceStandard(StrEnum):
    CHILD_WELFARE = "child_welfare"
    SCHOOL_SAFETY = "school_safety"


class SafetyPlanStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"


class SafetyLogType(StrEnum):
    TRAINING_DRILL = "training_drill"
    PARENT_NOTICE = "parent_notice"
    REVIEW = "review"
    SCHOOL_SAFETY_ACTION = "school_safety_action"
    SAFETY_INSPECTION = "safety_inspection"
    CHILD_GUIDANCE = "child_guidance"
    MANUAL_UPDATE = "manual_update"
    INCIDENT_REFLECTION = "incident_reflection"


class SafetyRiskStatus(StrEnum):
    COMPLIANT = "compliant"
    ATTENTION = "attention"
    WARNING = "warning"
    HIGH_RISK = "high_risk"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class SafetyFacilityProfile:
    facility_type: FacilityType
    facility_name: str
    municipality: str
    capacity_summary: str
    age_groups: str
    has_bus: bool = False
    has_outdoor_activity: bool = True
    has_pool: bool = False
    has_kitchen: bool = True
    disaster_risks: str = ""
    staff_counts: str = ""
    outdoor_routes: str = ""
    safety_policy: str = ""

    @property
    def facility_type_label(self) -> str:
        return FACILITY_TYPE_LABELS[self.facility_type]

    @property
    def compliance_standard(self) -> SafetyComplianceStandard:
        if self.facility_type in {FacilityType.KINDERGARTEN, FacilityType.CERTIFIED_CHILD_CENTER}:
            return SafetyComplianceStandard.SCHOOL_SAFETY
        return SafetyComplianceStandard.CHILD_WELFARE

    @property
    def compliance_standard_label(self) -> str:
        if self.compliance_standard == SafetyComplianceStandard.SCHOOL_SAFETY:
            return "学校安全計画"
        return "安全計画"


@dataclass(slots=True)
class SafetyActionItem:
    category: str
    title: str
    planned_month: str
    responsible_role: str
    recurrence: str
    legal_axis: SafetyLogType


@dataclass(slots=True)
class SafetyPlanDraft:
    title: str
    status: SafetyPlanStatus
    school_year: int
    facility_profile: SafetyFacilityProfile
    established_on: date | None
    blocks: list[SectionBlock]
    action_items: list[SafetyActionItem]
    missing_inputs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SafetyAxisStatus:
    log_type: SafetyLogType
    label: str
    status: SafetyRiskStatus
    last_implemented_on: date | None
    next_due_on: date | None
    days_until_due: int | None
    message: str


@dataclass(slots=True)
class SafetyComplianceResult:
    status: SafetyRiskStatus
    message: str
    axes: list[SafetyAxisStatus]
    missing_requirements: list[str] = field(default_factory=list)


def safety_official_source_ref() -> SourceRef:
    return SourceRef(kind="official_guidance", ref="official:safety-plan", label="安全計画公的根拠")


def safety_evidence_tags(*, include_public_guidance: bool = True) -> list[EvidenceTag]:
    tags = [EvidenceTag.NURSERY_POLICY, EvidenceTag.USER_INPUT, EvidenceTag.AI_COMPOSITION]
    if include_public_guidance:
        tags.insert(1, EvidenceTag.PUBLIC_GUIDANCE)
    return tags
