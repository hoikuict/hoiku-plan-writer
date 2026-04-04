from __future__ import annotations

from .domain.models import AnnualPlanInput, MonthlyPlanInput, NurseryProfile


def sample_profile() -> NurseryProfile:
    return NurseryProfile(
        nursery_name="さくら保育園",
        target_age_group="3〜5歳児",
        class_configuration="年少1クラス、年中1クラス、年長1クラス",
        philosophy="子どもの主体性を尊重し、安心して挑戦できる環境をつくる。",
        childcare_goal="遊びを通して人と関わる力、考える力、表現する力を育む。",
        desired_child_image="自分の思いを出しながら友だちと折り合いをつけて遊べる子ども。",
        child_view="子ども一人ひとりの気づきや選択を大切にする。",
        play_view="生活と遊びのつながりを重視し、探究が続く環境を整える。",
        support_policy="見守りを基本にしつつ、必要な場面で言葉掛けと環境調整を行う。",
        indoor_environment="落ち着いて選べるコーナーを複数用意する。",
        outdoor_environment="季節の変化を感じられる園庭活動を取り入れる。",
        corner_play="制作、ままごと、構成遊びのコーナーを継続的に整える。",
        community_resources="近隣公園、図書館、地域行事を活用する。",
        family_collaboration_policy="家庭と日々の姿を共有し、育ちの連続性を意識して対話する。",
        local_collaboration_policy="地域の人や場との関わりから社会性を育む。",
        health_and_safety_policy="安全確認を習慣化し、安心して活動できる流れを整える。",
        inclusive_policy="違いを受け止め合える集団づくりを大切にする。",
        preferred_expressions="子どもが自ら気づく、友だちと確かめ合う、安心して試す",
        avoid_expressions="一律に指示する、できて当然",
        sentence_tone="やわらかく丁寧",
        missing_input_policy="未入力は推測せず要確認として扱う。",
        confirmation_marker="要確認",
        evidence_tag_policy="根拠タグを各ブロックに表示する。",
        approved=True,
        version=1,
    )


def sample_annual_input() -> AnnualPlanInput:
    return AnnualPlanInput(
        school_year=2026,
        class_name="5歳児",
        age_group="5歳児",
        class_outlook="自分の思いを表現しながら、友だちと相談して遊びを進める姿を育てたい。",
        focus_growth="友だちと協力しながら遊びや生活を主体的につくる力。",
        annual_events="入園進級の集い、夏まつり、運動会、生活発表会、卒園に向かう活動",
        seasonal_context="春の安心づくり、夏の開放感、秋の協同性、冬のまとめ",
        community_resources="近隣公園、図書館、地域交流会",
        care_points="生活リズムの安定、安全な活動導線、友だち同士の対話支援",
        handover_notes="前年度末から、話し合いで役割を決めることへの意欲が高まっている。",
    )


def sample_monthly_input() -> MonthlyPlanInput:
    return MonthlyPlanInput(
        target_month="2026-05",
        class_name="5歳児",
        owner_name="山田",
        related_term_key="term_1",
        previous_reflection="新年度の生活に慣れ、自分から遊びを選ぶ姿が増えた。友だちとのやり取りはまだ保育者の仲立ちが必要な場面がある。",
        current_children_snapshot="気の合う友だちと一緒にイメージを共有しながら遊ぶ姿が見られる一方で、思いの違いから立ち止まる姿もある。",
        play_interests="ごっこ遊び、制作、園庭でのルール遊び",
        seasonal_context="連休明けの生活リズムの再調整と、春から初夏への自然の変化",
        family_context="家庭でも友だちの名前を話題にする姿が増えている。",
        class_notes="集団での話し合いでは、全員が安心して発言できる進め方を意識したい。",
    )
