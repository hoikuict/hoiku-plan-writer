from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from fastapi import Form

from ..domain.models import AnnualPlanInput, MonthlyPlanInput, NurseryProfile


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

    def to_domain(self, *, approved: bool = False) -> NurseryProfile:
        return NurseryProfile(
            nursery_name=self.nursery_name,
            target_age_group=self.target_age_group,
            class_configuration=self.class_configuration,
            philosophy=self.philosophy,
            childcare_goal=self.childcare_goal,
            desired_child_image=self.desired_child_image,
            child_view=self.child_view,
            play_view=self.play_view,
            support_policy=self.support_policy,
            indoor_environment=self.indoor_environment,
            outdoor_environment=self.outdoor_environment,
            corner_play=self.corner_play,
            community_resources=self.community_resources,
            family_collaboration_policy=self.family_collaboration_policy,
            local_collaboration_policy=self.local_collaboration_policy,
            health_and_safety_policy=self.health_and_safety_policy,
            inclusive_policy=self.inclusive_policy,
            preferred_expressions=self.preferred_expressions,
            avoid_expressions=self.avoid_expressions,
            sentence_tone=self.sentence_tone,
            missing_input_policy=self.missing_input_policy,
            confirmation_marker=self.confirmation_marker,
            evidence_tag_policy=self.evidence_tag_policy,
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


def profile_form_data(
    nursery_name: str = Form(""),
    target_age_group: str = Form(""),
    class_configuration: str = Form(""),
    philosophy: str = Form(""),
    childcare_goal: str = Form(""),
    desired_child_image: str = Form(""),
    child_view: str = Form(""),
    play_view: str = Form(""),
    support_policy: str = Form(""),
    indoor_environment: str = Form(""),
    outdoor_environment: str = Form(""),
    corner_play: str = Form(""),
    community_resources: str = Form(""),
    family_collaboration_policy: str = Form(""),
    local_collaboration_policy: str = Form(""),
    health_and_safety_policy: str = Form(""),
    inclusive_policy: str = Form(""),
    preferred_expressions: str = Form(""),
    avoid_expressions: str = Form(""),
    sentence_tone: str = Form(""),
    missing_input_policy: str = Form("未入力は要確認として扱う。"),
    confirmation_marker: str = Form("要確認"),
    evidence_tag_policy: str = Form("根拠タグを表示する。"),
) -> ProfileFormData:
    return ProfileFormData(
        nursery_name=nursery_name,
        target_age_group=target_age_group,
        class_configuration=class_configuration,
        philosophy=philosophy,
        childcare_goal=childcare_goal,
        desired_child_image=desired_child_image,
        child_view=child_view,
        play_view=play_view,
        support_policy=support_policy,
        indoor_environment=indoor_environment,
        outdoor_environment=outdoor_environment,
        corner_play=corner_play,
        community_resources=community_resources,
        family_collaboration_policy=family_collaboration_policy,
        local_collaboration_policy=local_collaboration_policy,
        health_and_safety_policy=health_and_safety_policy,
        inclusive_policy=inclusive_policy,
        preferred_expressions=preferred_expressions,
        avoid_expressions=avoid_expressions,
        sentence_tone=sentence_tone,
        missing_input_policy=missing_input_policy,
        confirmation_marker=confirmation_marker,
        evidence_tag_policy=evidence_tag_policy,
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

