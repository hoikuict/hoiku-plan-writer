from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from sqlmodel import Session

from .auth import StaffRole
from .db import create_db_and_tables, create_engine_for_url
from .demo_runtime import sqlite_url_for_path
from .domain.models import AnnualPlanInput, MonthlyPlanInput, NurseryProfile
from .persistence.repositories import create_document, profile_record_to_domain, save_profile
from .services.generators import generate_annual_plan, generate_monthly_plan

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


def initialize_demo_template_database(db_path: Path) -> None:
    engine = create_engine_for_url(sqlite_url_for_path(db_path))
    try:
        create_db_and_tables(engine)
        seed_demo_data(engine)
    finally:
        engine.dispose()