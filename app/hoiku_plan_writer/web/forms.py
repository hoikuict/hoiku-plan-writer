from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from fastapi import Form

from ..domain.models import AnnualPlanInput, MonthlyPlanInput, NurseryProfile
from ..domain.safety import FacilityType, SafetyFacilityProfile, SafetyLogType


@dataclass(slots=True)
class ProfileFormData:
    nursery_name: str
    target_age_group: str
    class_configuration: str
    philosophy: str
    childcare_goal: str
    desired_child_image: str
    child_view: str
    play_view: str
    support_policy: str
    local_context: str = ""
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

    def to_domain(self, *, approved: bool = False) -> NurseryProfile:
        return NurseryProfile(
            nursery_name=self.nursery_name,
            target_age_group=self.target_age_group,
            class_configuration=self.class_configuration,
            local_context=self.local_context,
            philosophy=self.philosophy,
            childcare_goal=self.childcare_goal,
            desired_child_image=self.desired_child_image,
            child_view=self.child_view,
            play_view=self.play_view,
            support_policy=self.support_policy,
            curriculum_focus=self.curriculum_focus,
            assessment_policy=self.assessment_policy,
            indoor_environment=self.indoor_environment,
            outdoor_environment=self.outdoor_environment,
            corner_play=self.corner_play,
            community_resources=self.community_resources,
            family_collaboration_policy=self.family_collaboration_policy,
            local_collaboration_policy=self.local_collaboration_policy,
            health_and_safety_policy=self.health_and_safety_policy,
            inclusive_policy=self.inclusive_policy,
            daily_rhythm=self.daily_rhythm,
            preferred_expressions=self.preferred_expressions,
            avoid_expressions=self.avoid_expressions,
            sentence_tone=self.sentence_tone,
            document_format_notes=self.document_format_notes,
            missing_input_policy=self.missing_input_policy,
            confirmation_marker=self.confirmation_marker,
            evidence_tag_policy=self.evidence_tag_policy,
            privacy_policy=self.privacy_policy,
            approved=approved,
        )

    def as_snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class AnnualPlanFormData:
    classroom_ref: str
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

    def to_domain_input(self) -> AnnualPlanInput:
        return AnnualPlanInput(
            school_year=self.school_year,
            class_name=self.class_name,
            age_group=self.age_group,
            class_outlook=self.class_outlook,
            focus_growth=self.focus_growth,
            annual_events=self.annual_events,
            seasonal_context=self.seasonal_context,
            community_resources=self.community_resources,
            care_points=self.care_points,
            handover_notes=self.handover_notes,
        )

    def as_snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class MonthlyPlanFormData:
    classroom_ref: str
    target_month: str
    class_name: str
    owner_name: str
    related_annual_plan_id: int | None
    related_term_key: str
    previous_reflection: str
    current_children_snapshot: str
    play_interests: str = ""
    seasonal_context: str = ""
    family_context: str = ""
    class_notes: str = ""

    def to_domain_input(self) -> MonthlyPlanInput:
        return MonthlyPlanInput(
            target_month=self.target_month,
            class_name=self.class_name,
            owner_name=self.owner_name,
            related_term_key=self.related_term_key,
            previous_reflection=self.previous_reflection,
            current_children_snapshot=self.current_children_snapshot,
            play_interests=self.play_interests,
            seasonal_context=self.seasonal_context,
            family_context=self.family_context,
            class_notes=self.class_notes,
        )

    def as_snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SafetyPlanFormData:
    school_year: int
    established_on_raw: str
    facility_type: str
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
    def established_on(self) -> date | None:
        return _parse_date(self.established_on_raw)

    def to_facility_profile(self) -> SafetyFacilityProfile:
        try:
            facility_type = FacilityType(self.facility_type)
        except ValueError:
            facility_type = FacilityType.NURSERY
        return SafetyFacilityProfile(
            facility_type=facility_type,
            facility_name=self.facility_name,
            municipality=self.municipality,
            capacity_summary=self.capacity_summary,
            age_groups=self.age_groups,
            has_bus=self.has_bus,
            has_outdoor_activity=self.has_outdoor_activity,
            has_pool=self.has_pool,
            has_kitchen=self.has_kitchen,
            disaster_risks=self.disaster_risks,
            staff_counts=self.staff_counts,
            outdoor_routes=self.outdoor_routes,
            safety_policy=self.safety_policy,
        )

    def as_snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SafetyLogFormData:
    log_type: str
    implemented_on_raw: str
    title: str
    participants: str = ""
    method: str = ""
    evidence_note: str = ""
    evidence_file_ref: str = ""
    related_action_id_raw: str = ""

    @property
    def implemented_on(self) -> date | None:
        return _parse_date(self.implemented_on_raw)

    @property
    def related_action_id(self) -> int | None:
        if not self.related_action_id_raw.strip():
            return None
        return int(self.related_action_id_raw)

    @property
    def parsed_log_type(self) -> SafetyLogType:
        try:
            return SafetyLogType(self.log_type)
        except ValueError:
            return SafetyLogType.TRAINING_DRILL


def profile_form_data(
    nursery_name: str = Form(""),
    target_age_group: str = Form(""),
    class_configuration: str = Form(""),
    local_context: str = Form(""),
    philosophy: str = Form(""),
    childcare_goal: str = Form(""),
    desired_child_image: str = Form(""),
    child_view: str = Form(""),
    play_view: str = Form(""),
    support_policy: str = Form(""),
    curriculum_focus: str = Form(""),
    assessment_policy: str = Form(""),
    indoor_environment: str = Form(""),
    outdoor_environment: str = Form(""),
    corner_play: str = Form(""),
    community_resources: str = Form(""),
    family_collaboration_policy: str = Form(""),
    local_collaboration_policy: str = Form(""),
    health_and_safety_policy: str = Form(""),
    inclusive_policy: str = Form(""),
    daily_rhythm: str = Form(""),
    preferred_expressions: str = Form(""),
    avoid_expressions: str = Form(""),
    sentence_tone: str = Form(""),
    document_format_notes: str = Form(""),
    missing_input_policy: str = Form("未入力は要確認として扱う。"),
    confirmation_marker: str = Form("要確認"),
    evidence_tag_policy: str = Form("根拠タグを表示する。"),
    privacy_policy: str = Form("個人名、診断名、健康詳細、家庭の詳細事情は入力・出力に含めない。"),
) -> ProfileFormData:
    return ProfileFormData(
        nursery_name=nursery_name,
        target_age_group=target_age_group,
        class_configuration=class_configuration,
        local_context=local_context,
        philosophy=philosophy,
        childcare_goal=childcare_goal,
        desired_child_image=desired_child_image,
        child_view=child_view,
        play_view=play_view,
        support_policy=support_policy,
        curriculum_focus=curriculum_focus,
        assessment_policy=assessment_policy,
        indoor_environment=indoor_environment,
        outdoor_environment=outdoor_environment,
        corner_play=corner_play,
        community_resources=community_resources,
        family_collaboration_policy=family_collaboration_policy,
        local_collaboration_policy=local_collaboration_policy,
        health_and_safety_policy=health_and_safety_policy,
        inclusive_policy=inclusive_policy,
        daily_rhythm=daily_rhythm,
        preferred_expressions=preferred_expressions,
        avoid_expressions=avoid_expressions,
        sentence_tone=sentence_tone,
        document_format_notes=document_format_notes,
        missing_input_policy=missing_input_policy,
        confirmation_marker=confirmation_marker,
        evidence_tag_policy=evidence_tag_policy,
        privacy_policy=privacy_policy,
    )


def annual_plan_form_data(
    classroom_ref: str = Form("classroom:5yo-a"),
    school_year: int = Form(date.today().year),
    class_name: str = Form(""),
    age_group: str = Form(""),
    class_outlook: str = Form(""),
    focus_growth: str = Form(""),
    annual_events: str = Form(""),
    seasonal_context: str = Form(""),
    community_resources: str = Form(""),
    care_points: str = Form(""),
    handover_notes: str = Form(""),
) -> AnnualPlanFormData:
    return AnnualPlanFormData(
        classroom_ref=classroom_ref,
        school_year=school_year,
        class_name=class_name,
        age_group=age_group,
        class_outlook=class_outlook,
        focus_growth=focus_growth,
        annual_events=annual_events,
        seasonal_context=seasonal_context,
        community_resources=community_resources,
        care_points=care_points,
        handover_notes=handover_notes,
    )


def monthly_plan_form_data(
    classroom_ref: str = Form("classroom:5yo-a"),
    target_month: str = Form(date.today().strftime("%Y-%m")),
    class_name: str = Form(""),
    owner_name: str = Form(""),
    related_annual_plan_id_raw: str = Form(""),
    related_term_key: str = Form("term_1"),
    previous_reflection: str = Form(""),
    current_children_snapshot: str = Form(""),
    play_interests: str = Form(""),
    seasonal_context: str = Form(""),
    family_context: str = Form(""),
    class_notes: str = Form(""),
) -> MonthlyPlanFormData:
    related_annual_plan_id = None
    if related_annual_plan_id_raw.strip():
        related_annual_plan_id = int(related_annual_plan_id_raw)
    return MonthlyPlanFormData(
        classroom_ref=classroom_ref,
        target_month=target_month,
        class_name=class_name,
        owner_name=owner_name,
        related_annual_plan_id=related_annual_plan_id,
        related_term_key=related_term_key,
        previous_reflection=previous_reflection,
        current_children_snapshot=current_children_snapshot,
        play_interests=play_interests,
        seasonal_context=seasonal_context,
        family_context=family_context,
        class_notes=class_notes,
    )


def safety_plan_form_data(
    school_year: int = Form(date.today().year),
    established_on_raw: str = Form(date.today().isoformat()),
    facility_type: str = Form(FacilityType.NURSERY.value),
    facility_name: str = Form(""),
    municipality: str = Form(""),
    capacity_summary: str = Form(""),
    age_groups: str = Form(""),
    has_bus: bool = Form(False),
    has_outdoor_activity: bool = Form(False),
    has_pool: bool = Form(False),
    has_kitchen: bool = Form(False),
    disaster_risks: str = Form(""),
    staff_counts: str = Form(""),
    outdoor_routes: str = Form(""),
    safety_policy: str = Form(""),
) -> SafetyPlanFormData:
    return SafetyPlanFormData(
        school_year=school_year,
        established_on_raw=established_on_raw,
        facility_type=facility_type,
        facility_name=facility_name,
        municipality=municipality,
        capacity_summary=capacity_summary,
        age_groups=age_groups,
        has_bus=has_bus,
        has_outdoor_activity=has_outdoor_activity,
        has_pool=has_pool,
        has_kitchen=has_kitchen,
        disaster_risks=disaster_risks,
        staff_counts=staff_counts,
        outdoor_routes=outdoor_routes,
        safety_policy=safety_policy,
    )


def safety_log_form_data(
    log_type: str = Form(SafetyLogType.TRAINING_DRILL.value),
    implemented_on_raw: str = Form(date.today().isoformat()),
    title: str = Form(""),
    participants: str = Form(""),
    method: str = Form(""),
    evidence_note: str = Form(""),
    evidence_file_ref: str = Form(""),
    related_action_id_raw: str = Form(""),
) -> SafetyLogFormData:
    return SafetyLogFormData(
        log_type=log_type,
        implemented_on_raw=implemented_on_raw,
        title=title,
        participants=participants,
        method=method,
        evidence_note=evidence_note,
        evidence_file_ref=evidence_file_ref,
        related_action_id_raw=related_action_id_raw,
    )


def _parse_date(raw_value: str) -> date | None:
    if not raw_value.strip():
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None
