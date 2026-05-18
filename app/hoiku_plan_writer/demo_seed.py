from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

from sqlmodel import Session

from .auth import StaffRole
from .db import create_db_and_tables, create_engine_for_url
from .demo_runtime import sqlite_url_for_path
from .domain.models import AnnualPlanInput, MonthlyPlanInput, NurseryProfile
from .domain.safety import FacilityType, SafetyFacilityProfile, SafetyLogType
from .persistence.repositories import create_document, profile_record_to_domain, save_profile
from .persistence.safety_repositories import add_safety_log, create_safety_plan
from .services.generators import generate_annual_plan, generate_monthly_plan
from .services.safety import generate_safety_plan

DEMO_NURSERY_REF = "nursery:demo"
DEMO_CLASSROOM_REF = "classroom:5yo-a"
DEMO_ADMIN_ACTOR_REF = "staff:demo-admin"


def build_demo_profile() -> NurseryProfile:
    return NurseryProfile(
        nursery_name="みどり保育園",
        target_age_group="3〜5歳児",
        class_configuration="5歳児 1クラス 20名",
        philosophy="子どもの思いや試したい気持ちを受け止め、対話しながら育ちを支える。",
        childcare_goal="自分で考え、友だちと関わりながら遊びを深める子ども",
        desired_child_image="安心して思いを出し合い、自分なりに挑戦する子ども",
        child_view="子どもは人との関わりや遊びの中で、自分なりの意味をつくりながら育つ存在である。",
        play_view="遊びは学びの土台であり、試行錯誤と対話を通して広がっていく。",
        support_policy="子どもの気づきや迷いを受け止め、必要なときに言葉や環境で支える。",
        indoor_environment="落ち着いて選べるコーナーと、試した跡が残る素材配置を意識する。",
        outdoor_environment="季節の変化を感じられる場で、身体を十分に動かせる活動を取り入れる。",
        corner_play="遊びが翌日にもつながるよう、継続できるコーナーを保つ。",
        community_resources="近隣公園や図書館を保育の題材として取り入れる。",
        family_collaboration_policy="家庭と育ちの姿を共有し、園と家庭で見通しをそろえる。",
        local_collaboration_policy="地域の人や場とのつながりを、子どもの安心感と興味につなげる。",
        health_and_safety_policy="安心して試せるよう、生活動線と安全面を日々見直す。",
        inclusive_policy="一人ひとりのペースや背景の違いを受け止め、参加の仕方を支える。",
        preferred_expressions="子どもが自ら、友だちと確かめ合う、安心して試す",
        avoid_expressions="一律にさせる、できて当たり前",
        sentence_tone="園内共有用の落ち着いた常体",
        missing_input_policy="未入力の内容は断定せず、確認が必要な前提で下書きに残す。",
        confirmation_marker="要確認",
        evidence_tag_policy="根拠タグを表示する。",
        approved=True,
    )


def build_demo_annual_input() -> AnnualPlanInput:
    return AnnualPlanInput(
        school_year=2026,
        class_name="5歳児",
        age_group="5歳児",
        class_outlook="友だちと相談しながら遊びを発展させる姿を大切にしたい。",
        focus_growth="自分の思いを出しつつ、相手の考えにも耳を傾ける力",
        annual_events="運動会、秋の遠足、生活発表会",
        seasonal_context="地域の公園や季節行事を保育に取り入れやすい。",
        community_resources="近隣公園、図書館、地域交流会館",
        care_points="話し合いで言葉にしにくい子にも参加しやすい流れをつくる。",
        handover_notes="昨年度から継続しているごっこ遊びの広がりを生かしたい。",
    )


def build_demo_monthly_input() -> MonthlyPlanInput:
    return MonthlyPlanInput(
        target_month="2026-05",
        class_name="5歳児",
        owner_name="公開デモ職員",
        related_term_key="term_1",
        previous_reflection="自分のやりたいことを出せる子が増えた一方、話し合いでは一部の子に発言が偏った。",
        current_children_snapshot="興味の近い友だち同士で遊びを続ける姿が見られ、役割分担も少しずつ生まれている。",
        play_interests="ごっこ遊び、製作、戸外でのルール遊び",
        seasonal_context="春から初夏への変化が感じられ、園庭や散歩先で自然物に触れやすい。",
        family_context="新年度の生活リズムが整い始め、家庭からも友だち関係の話題が増えている。",
        class_notes="話し合いに入りにくい子へは、少人数での相談場面を用意する。",
    )


def build_demo_safety_facility_profile() -> SafetyFacilityProfile:
    return SafetyFacilityProfile(
        facility_type=FacilityType.NURSERY,
        facility_name="みどり保育園",
        municipality="みどり市",
        capacity_summary="60名",
        age_groups="0〜5歳児",
        has_bus=False,
        has_outdoor_activity=True,
        has_pool=True,
        has_kitchen=True,
        disaster_risks="地震、風水害、熱中症、近隣道路の交通量",
        staff_counts="常勤12名、非常勤6名",
        outdoor_routes="園庭、近隣公園、図書館までの散歩コース",
        safety_policy="安心して試せるよう、生活動線と安全面を日々見直し、職員間で共有する。",
    )


def safety_facility_snapshot(facility_profile: SafetyFacilityProfile, *, school_year: int, established_on: date) -> dict[str, object]:
    return {
        "school_year": school_year,
        "established_on_raw": established_on.isoformat(),
        "facility_type": facility_profile.facility_type.value,
        "facility_name": facility_profile.facility_name,
        "municipality": facility_profile.municipality,
        "capacity_summary": facility_profile.capacity_summary,
        "age_groups": facility_profile.age_groups,
        "has_bus": facility_profile.has_bus,
        "has_outdoor_activity": facility_profile.has_outdoor_activity,
        "has_pool": facility_profile.has_pool,
        "has_kitchen": facility_profile.has_kitchen,
        "disaster_risks": facility_profile.disaster_risks,
        "staff_counts": facility_profile.staff_counts,
        "outdoor_routes": facility_profile.outdoor_routes,
        "safety_policy": facility_profile.safety_policy,
    }


def seed_demo_data(engine) -> None:
    with Session(engine) as session:
        profile_record = save_profile(
            session,
            nursery_ref=DEMO_NURSERY_REF,
            actor_ref=DEMO_ADMIN_ACTOR_REF,
            profile=build_demo_profile(),
            approve=True,
        )
        approved_profile = profile_record_to_domain(profile_record)

        annual_input = build_demo_annual_input()
        annual_plan = generate_annual_plan(approved_profile, annual_input)
        annual_document = create_document(
            session,
            generated_plan=annual_plan,
            nursery_ref=DEMO_NURSERY_REF,
            classroom_ref=DEMO_CLASSROOM_REF,
            actor_ref=DEMO_ADMIN_ACTOR_REF,
            school_year=annual_input.school_year,
            target_month=None,
            related_document_id=None,
            input_snapshot=asdict(annual_input),
            role=StaffRole.ADMIN.value,
        )

        monthly_input = build_demo_monthly_input()
        monthly_plan = generate_monthly_plan(approved_profile, annual_plan, monthly_input)
        create_document(
            session,
            generated_plan=monthly_plan,
            nursery_ref=DEMO_NURSERY_REF,
            classroom_ref=DEMO_CLASSROOM_REF,
            actor_ref=DEMO_ADMIN_ACTOR_REF,
            school_year=None,
            target_month=monthly_input.target_month,
            related_document_id=annual_document.id,
            input_snapshot=asdict(monthly_input),
            role=StaffRole.ADMIN.value,
        )

        safety_established_on = date(2026, 4, 1)
        safety_facility_profile = build_demo_safety_facility_profile()
        safety_plan = generate_safety_plan(
            approved_profile,
            safety_facility_profile,
            school_year=2026,
            established_on=safety_established_on,
        )
        safety_record = create_safety_plan(
            session,
            draft=safety_plan,
            nursery_ref=DEMO_NURSERY_REF,
            actor_ref=DEMO_ADMIN_ACTOR_REF,
            input_snapshot=safety_facility_snapshot(
                safety_facility_profile,
                school_year=2026,
                established_on=safety_established_on,
            ),
            approve=True,
        )
        safety_logs = [
            (
                SafetyLogType.TRAINING_DRILL,
                date(2026, 4, 10),
                "年度初め安全計画職員周知",
                "全職員",
                "園内研修",
                "安全計画と役割分担を読み合わせ、参加記録を保管。",
            ),
            (
                SafetyLogType.PARENT_NOTICE,
                date(2026, 4, 12),
                "入園・進級時の保護者周知",
                "全保護者",
                "園だより・掲示",
                "園だより控えと掲示写真を年度フォルダに保管。",
            ),
            (
                SafetyLogType.REVIEW,
                date(2026, 5, 8),
                "水遊び前の安全計画見直し",
                "施設長・主任・担任",
                "園内会議",
                "水遊び前の監視体制と熱中症対策を追記確認。",
            ),
        ]
        for log_type, implemented_on, title, participants, method, evidence_note in safety_logs:
            add_safety_log(
                session,
                plan=safety_record,
                log_type=log_type,
                implemented_on=implemented_on,
                title=title,
                participants=participants,
                method=method,
                evidence_note=evidence_note,
                evidence_file_ref="公開デモ用サンプル記録",
                actor_ref=DEMO_ADMIN_ACTOR_REF,
            )


def initialize_demo_template_database(db_path: Path) -> None:
    engine = create_engine_for_url(sqlite_url_for_path(db_path))
    try:
        create_db_and_tables(engine)
        seed_demo_data(engine)
    finally:
        engine.dispose()
