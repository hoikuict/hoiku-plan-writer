from __future__ import annotations

from ..domain.models import (
    AnnualPlanInput,
    DocumentStatus,
    DocumentType,
    EvidenceTag,
    GeneratedPlan,
    MonthlyPlanInput,
    NurseryProfile,
    SectionBlock,
    SourceRef,
)
from ..domain.section_catalog import ANNUAL_TERM_ORDER

TERM_FOCUS = {
    "term_1": "新しい生活に安心して入り、関係づくりの土台を整える。",
    "term_2": "開放感のある活動の中で、自分たちで遊びを広げる。",
    "term_3": "経験を共有しながら、目的に向かって協力する。",
    "term_4": "育ちを確かめ合い、次の生活への見通しを持つ。",
}

TERM_LABELS = dict(ANNUAL_TERM_ORDER)


def generate_annual_plan(profile: NurseryProfile, plan_input: AnnualPlanInput) -> GeneratedPlan:
    missing_inputs = _collect_missing_annual_inputs(profile, plan_input)
    confirmation_note = _confirmation_text(profile, missing_inputs)

    blocks = [
        SectionBlock(
            section_key="annual_goal",
            title="年間の大きなねらい",
            body=_with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        f"{plan_input.school_year}年度の{plan_input.class_name}では、{plan_input.focus_growth} を年間の軸に据える。",
                        f"園の保育目標「{profile.childcare_goal}」と、育てたい子ども像「{profile.desired_child_image}」を踏まえ、{plan_input.class_outlook}",
                        f"理念「{profile.philosophy}」を基盤に、{profile.child_view} という子ども観と、{profile.play_view} という遊びの考え方を保育全体に通す。",
                        _writing_style_sentence(profile),
                    ]
                ),
            ),
            evidence_tags=_evidence_tags(include_public_guidance=True),
            source_refs=[
                _profile_source_ref(profile),
                _official_source_ref(),
                _input_source_ref("class_outlook", "今年のクラスの見通し"),
                _input_source_ref("focus_growth", "今年特に大切にしたい育ち"),
            ],
            needs_confirmation=bool(missing_inputs),
            editor_note=_editor_note(missing_inputs),
        )
    ]

    for term_key, term_label in ANNUAL_TERM_ORDER:
        term_focus = TERM_FOCUS[term_key]
        blocks.extend(
            [
                SectionBlock(
                    section_key=f"{term_key}_outlook",
                    title=f"{term_label}の見通し",
                    body=_with_confirmation(
                        confirmation_note,
                        "\n".join(
                            [
                                f"{term_label}は、{term_focus}",
                                f"対象は {profile.target_age_group}、編成は {profile.class_configuration} を前提に、クラスの見通しとして {plan_input.class_outlook}",
                                f"年間の大きなねらい「{plan_input.focus_growth}」につながる姿として、{profile.desired_child_image} を丁寧に支える。",
                            ]
                        ),
                    ),
                    evidence_tags=_evidence_tags(include_public_guidance=True),
                    source_refs=[
                        _profile_source_ref(profile),
                        _official_source_ref(),
                        _input_source_ref("class_outlook", "今年のクラスの見通し"),
                        _input_source_ref("focus_growth", "今年特に大切にしたい育ち"),
                    ],
                    needs_confirmation=bool(missing_inputs),
                    editor_note=_editor_note(missing_inputs),
                ),
                SectionBlock(
                    section_key=f"{term_key}_environment",
                    title=f"{term_label}の環境構成",
                    body=_with_confirmation(
                        confirmation_note,
                        "\n".join(
                            [
                                f"室内では {_profile_text(profile, 'indoor_environment', '落ち着いて選べる環境')} を意識する。",
                                f"戸外では {_profile_text(profile, 'outdoor_environment', '季節を感じる活動')} を取り入れる。",
                                f"遊びの継続性を高めるため、{_profile_text(profile, 'corner_play', '継続的なコーナー設定')} を行う。",
                                f"地域資源は { _profile_text(profile, 'community_resources', plan_input.community_resources or '地域の資源') } を見通しに入れて活用する。",
                            ]
                        ),
                    ),
                    evidence_tags=_evidence_tags(include_public_guidance=False),
                    source_refs=[
                        _profile_source_ref(profile),
                        _input_source_ref("seasonal_context", "季節・地域文脈"),
                        _input_source_ref("community_resources", "地域資源"),
                    ],
                    needs_confirmation=bool(missing_inputs),
                    editor_note=_editor_note(missing_inputs),
                ),
                SectionBlock(
                    section_key=f"{term_key}_support",
                    title=f"{term_label}の援助",
                    body=_with_confirmation(
                        confirmation_note,
                        "\n".join(
                            [
                                f"{profile.support_policy}",
                                f"子ども観として {profile.child_view} を踏まえ、遊びの中で {profile.play_view} が続くように関わる。",
                                f"特に {plan_input.care_points or '対話と安全の両立'} を意識し、必要に応じて {_profile_text(profile, 'health_and_safety_policy', '安心して活動できる流れ')} を整える。",
                                f"また、{_profile_text(profile, 'inclusive_policy', '違いを受け止め合える関わり')} を意識して、一人ひとりの参加の仕方を支える。",
                            ]
                        ),
                    ),
                    evidence_tags=_evidence_tags(include_public_guidance=True),
                    source_refs=[
                        _profile_source_ref(profile),
                        _official_source_ref(),
                        _input_source_ref("care_points", "配慮事項"),
                    ],
                    needs_confirmation=bool(missing_inputs),
                    editor_note=_editor_note(missing_inputs),
                ),
                SectionBlock(
                    section_key=f"{term_key}_family_collaboration",
                    title=f"{term_label}の家庭連携",
                    body=_with_confirmation(
                        confirmation_note,
                        "\n".join(
                            [
                                f"{_profile_text(profile, 'family_collaboration_policy', '家庭と育ちの姿を共有する。')}",
                                f"地域との関わりとして {_profile_text(profile, 'local_collaboration_policy', '地域とのつながりを保育に生かす。')} を意識する。",
                                f"年間行事として {plan_input.annual_events or '年間行事'} を踏まえ、家庭と見通しを共有する。",
                            ]
                        ),
                    ),
                    evidence_tags=_evidence_tags(include_public_guidance=False),
                    source_refs=[
                        _profile_source_ref(profile),
                        _input_source_ref("annual_events", "年間行事"),
                    ],
                    needs_confirmation=bool(missing_inputs),
                    editor_note=_editor_note(missing_inputs),
                ),
                SectionBlock(
                    section_key=f"{term_key}_reflection_viewpoint",
                    title=f"{term_label}の振り返り観点",
                    body=_with_confirmation(
                        confirmation_note,
                        "\n".join(
                            [
                                f"保育目標「{profile.childcare_goal}」や、育てたい子ども像「{profile.desired_child_image}」につながる姿が見られたか。",
                                "子どもが自分なりの思いを出せていたか。",
                                "友だちとの関わりが次の活動につながっていたか。",
                                "環境構成と援助が年間のねらいと矛盾なくつながっていたかを確認する。",
                            ]
                        ),
                    ),
                    evidence_tags=_evidence_tags(include_public_guidance=True),
                    source_refs=[
                        _official_source_ref(),
                        _profile_source_ref(profile),
                    ],
                    needs_confirmation=bool(missing_inputs),
                    editor_note=_editor_note(missing_inputs),
                ),
            ]
        )

    return GeneratedPlan(
        document_type=DocumentType.ANNUAL,
        title=f"{plan_input.school_year}年度 年間指導計画（{plan_input.class_name}）",
        status=DocumentStatus.DRAFT,
        blocks=blocks,
        missing_inputs=missing_inputs,
    )


def generate_monthly_plan(
    profile: NurseryProfile,
    annual_plan: GeneratedPlan,
    plan_input: MonthlyPlanInput,
) -> GeneratedPlan:
    annual_term_context = _collect_annual_term_context(annual_plan, plan_input.related_term_key)
    missing_inputs = _collect_missing_monthly_inputs(profile, plan_input, annual_term_context)
    confirmation_note = _confirmation_text(profile, missing_inputs)

    term_label = TERM_LABELS.get(plan_input.related_term_key, plan_input.related_term_key)
    goal_text = (
        f"{plan_input.target_month}は、年間計画の{term_label}で示した方向性を踏まえ、"
        f"{plan_input.current_children_snapshot} に応じたねらいを立てる。"
    )
    if annual_term_context:
        goal_text = f"{goal_text}\n年間計画の関連文脈: {annual_term_context}"

    blocks = [
        SectionBlock(
            section_key="monthly_goal",
            title="今月のねらい",
            body=_with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        goal_text,
                        f"前月の反省「{plan_input.previous_reflection}」を受けて、子ども同士の対話が続く活動を増やす。",
                    ]
                ),
            ),
            evidence_tags=_evidence_tags(include_public_guidance=True),
            source_refs=[
                _profile_source_ref(profile),
                _official_source_ref(),
                _annual_plan_source_ref(annual_plan),
                _input_source_ref("previous_reflection", "前月の反省"),
                _input_source_ref("current_children_snapshot", "今の子どもの姿"),
            ],
            needs_confirmation=bool(missing_inputs),
            editor_note=_editor_note(missing_inputs),
        ),
        SectionBlock(
            section_key="children_snapshot",
            title="子どもの姿の捉え",
            body=_with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        f"現在の姿: {plan_input.current_children_snapshot}",
                        f"前月からのつながり: {plan_input.previous_reflection}",
                        "遊びや生活の中で、思いを出し合いながら関係を調整する姿を丁寧に捉える。",
                    ]
                ),
            ),
            evidence_tags=_evidence_tags(include_public_guidance=False),
            source_refs=[
                _input_source_ref("current_children_snapshot", "今の子どもの姿"),
                _input_source_ref("previous_reflection", "前月の反省"),
            ],
            needs_confirmation=bool(missing_inputs),
            editor_note=_editor_note(missing_inputs),
        ),
        SectionBlock(
            section_key="monthly_environment",
            title="環境構成",
            body=_with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        f"興味の中心となっている {plan_input.play_interests or '遊びと生活'} が継続するよう、コーナーや素材を見直す。",
                        f"季節の文脈として {plan_input.seasonal_context or '月の生活リズム'} を取り込む。",
                        f"{_profile_text(profile, 'indoor_environment', '室内環境')} と {_profile_text(profile, 'outdoor_environment', '戸外環境')} を往還できる流れを整える。",
                    ]
                ),
            ),
            evidence_tags=_evidence_tags(include_public_guidance=False),
            source_refs=[
                _profile_source_ref(profile),
                _input_source_ref("play_interests", "興味を持っている遊び・生活"),
                _input_source_ref("seasonal_context", "季節・家庭文脈"),
            ],
            needs_confirmation=bool(missing_inputs),
            editor_note=_editor_note(missing_inputs),
        ),
        SectionBlock(
            section_key="monthly_support",
            title="援助",
            body=_with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        f"{profile.support_policy}",
                        f"必要に応じて {plan_input.class_notes or '話し合いの進め方'} を調整し、子どもが安心して思いを出せるようにする。",
                        f"{_profile_text(profile, 'inclusive_policy', '違いを受け止め合える関わり')} を意識して援助する。",
                    ]
                ),
            ),
            evidence_tags=_evidence_tags(include_public_guidance=True),
            source_refs=[
                _profile_source_ref(profile),
                _official_source_ref(),
                _input_source_ref("class_notes", "クラス全体の留意事項"),
            ],
            needs_confirmation=bool(missing_inputs),
            editor_note=_editor_note(missing_inputs),
        ),
        SectionBlock(
            section_key="monthly_family_collaboration",
            title="家庭連携",
            body=_with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        f"{_profile_text(profile, 'family_collaboration_policy', '家庭と育ちの姿を共有する。')}",
                        f"家庭の状況として {plan_input.family_context or '家庭での様子'} を踏まえ、生活の連続性を意識して伝え合う。",
                    ]
                ),
            ),
            evidence_tags=_evidence_tags(include_public_guidance=False),
            source_refs=[
                _profile_source_ref(profile),
                _input_source_ref("family_context", "家庭の状況"),
            ],
            needs_confirmation=bool(missing_inputs),
            editor_note=_editor_note(missing_inputs),
        ),
        SectionBlock(
            section_key="monthly_reflection_viewpoint",
            title="月末の振り返り観点",
            body=_with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        "年間計画の該当期と矛盾なくつながっていたか。",
                        "前月の反省で挙がった課題に対して手立てが届いていたか。",
                        "環境構成と援助が子どもの姿の変化に合っていたかを確認する。",
                    ]
                ),
            ),
            evidence_tags=_evidence_tags(include_public_guidance=True),
            source_refs=[
                _official_source_ref(),
                _annual_plan_source_ref(annual_plan),
            ],
            needs_confirmation=bool(missing_inputs),
            editor_note=_editor_note(missing_inputs),
        ),
    ]

    return GeneratedPlan(
        document_type=DocumentType.MONTHLY,
        title=f"{plan_input.target_month} 月案（{plan_input.class_name}）",
        status=DocumentStatus.DRAFT,
        blocks=blocks,
        missing_inputs=missing_inputs,
    )


def _collect_missing_annual_inputs(profile: NurseryProfile, plan_input: AnnualPlanInput) -> list[str]:
    fields = {
        "承認済み園プロファイル": "OK" if profile.approved else "",
        "年度": str(plan_input.school_year),
        "クラス": plan_input.class_name,
        "年齢": plan_input.age_group,
        "今年のクラスの見通し": plan_input.class_outlook,
        "今年特に大切にしたい育ち": plan_input.focus_growth,
    }
    return [label for label, value in fields.items() if not str(value).strip()]


def _collect_missing_monthly_inputs(
    profile: NurseryProfile,
    plan_input: MonthlyPlanInput,
    annual_term_context: str,
) -> list[str]:
    fields = {
        "承認済み園プロファイル": "OK" if profile.approved else "",
        "対象月": plan_input.target_month,
        "クラス": plan_input.class_name,
        "担当者": plan_input.owner_name,
        "関連する年間計画の該当期": plan_input.related_term_key,
        "前月の反省": plan_input.previous_reflection,
        "今の子どもの姿": plan_input.current_children_snapshot,
        "年間計画の関連文脈": annual_term_context,
    }
    return [label for label, value in fields.items() if not str(value).strip()]


def _collect_annual_term_context(annual_plan: GeneratedPlan, related_term_key: str) -> str:
    matching_blocks = [
        block.body
        for block in annual_plan.blocks
        if block.section_key.startswith(related_term_key)
        and block.section_key.endswith(("outlook", "support"))
    ]
    return " ".join(matching_blocks[:2]).strip()


def _confirmation_text(profile: NurseryProfile, missing_inputs: list[str]) -> str:
    if not missing_inputs:
        return ""
    missing_labels = "、".join(missing_inputs)
    return f"{profile.confirmation_marker}: {missing_labels} が未入力または未確定です。{profile.missing_input_policy}"


def _with_confirmation(prefix: str, body: str) -> str:
    if not prefix:
        return body
    return f"{prefix}\n{body}"


def _evidence_tags(include_public_guidance: bool) -> list[EvidenceTag]:
    tags = [
        EvidenceTag.NURSERY_POLICY,
        EvidenceTag.USER_INPUT,
        EvidenceTag.AI_COMPOSITION,
    ]
    if include_public_guidance:
        tags.insert(1, EvidenceTag.PUBLIC_GUIDANCE)
    return tags


def _editor_note(missing_inputs: list[str]) -> str | None:
    if not missing_inputs:
        return "必要に応じて表現を園の書式に合わせて微調整する。"
    return f"未入力項目の確認後に再生成する: {', '.join(missing_inputs)}"


def _profile_text(profile: NurseryProfile, field_key: str, fallback: str) -> str:
    value = profile.text_for(field_key).strip()
    return value or fallback


def _writing_style_sentence(profile: NurseryProfile) -> str:
    sentence = f"文体は {_profile_text(profile, 'sentence_tone', '園の既定トーン')} を保ち、{_profile_text(profile, 'preferred_expressions', '園らしい表現')} を生かす。"
    avoid_expressions = profile.text_for('avoid_expressions').strip()
    if avoid_expressions:
        sentence = f"{sentence} 避けたい表現として {avoid_expressions} に留意する。"
    return sentence


def _profile_source_ref(profile: NurseryProfile) -> SourceRef:
    return SourceRef(kind="nursery_profile", ref=f"profile:v{profile.version}", label=f"園プロファイル v{profile.version}")


def _official_source_ref() -> SourceRef:
    return SourceRef(kind="official_guidance", ref="official:mvp", label="公的根拠")


def _input_source_ref(key: str, label: str) -> SourceRef:
    return SourceRef(kind="user_input", ref=f"input:{key}", label=label)


def _annual_plan_source_ref(annual_plan: GeneratedPlan) -> SourceRef:
    return SourceRef(kind="document", ref="document:annual-plan", label=annual_plan.title)
