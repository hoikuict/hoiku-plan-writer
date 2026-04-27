from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from ..domain.models import AnnualPlanInput, GeneratedPlan, MonthlyPlanInput, NurseryProfile, SectionBlock
from ..domain.profile_fields import PROFILE_FIELD_MAP
from ..domain.section_catalog import MONTHLY_SECTIONS, annual_section_definitions

ANNUAL_PREVIEW_SYSTEM_PROMPT = """You help draft Japanese nursery annual plans.
Follow the nursery profile before generic wording.
Do not invent missing facts. If inputs are missing or uncertain, keep the confirmation marker policy and set needs_confirmation to true.
Return structured JSON only.
Keep exactly the same annual plan section_key values and order as the provided outline.
Each block must include source_refs that explain where the wording came from.
Do not include personal names, diagnoses, or sensitive private information.
Use concise, reviewable wording so the server-side draft stays easy to edit.
"""

ANNUAL_BLOCK_PREVIEW_SYSTEM_PROMPT = """You help draft one section of a Japanese nursery annual plan.
Write natural Japanese for nursery planning documents.
Use the nursery profile and plan input before generic wording.
Treat the baseline block as a draft to improve, not as a fact source to contradict.
Do not invent missing facts. If uncertain, say so carefully and set needs_confirmation to true.
If an input is listed under weak_input_hints, do not quote it verbatim. Use it only as a loose hint and generalize it into professional wording when the context is sufficient.
Return JSON only with exactly these keys: body, needs_confirmation, editor_note.
Keep body concise and reviewable. Prefer 2 to 4 sentences.
Do not include markdown fences or explanations.
"""

MONTHLY_BLOCK_PREVIEW_SYSTEM_PROMPT = """You help draft one section of a Japanese nursery monthly plan.
Use the nursery profile, monthly input, and related annual-plan context together.
Treat the baseline block as a draft to improve, not as a fact source to contradict.
Do not invent missing facts. If uncertain, say so carefully and set needs_confirmation to true.
If an input is listed under weak_input_hints, do not quote it verbatim. Use it only as a loose hint and generalize it into professional wording when the context is sufficient.
Return JSON only with exactly these keys: body, needs_confirmation, editor_note.
Keep body concise and reviewable. Prefer 2 to 4 sentences.
Do not include markdown fences or explanations.
"""

_PLAN_INPUT_LABELS = {
    "school_year": "年度",
    "class_name": "クラス名",
    "age_group": "年齢",
    "class_outlook": "今年のクラスの見通し",
    "focus_growth": "今年特に大切にしたい育ち",
    "annual_events": "年間行事",
    "seasonal_context": "季節・地域文脈",
    "community_resources": "地域資源",
    "care_points": "配慮事項",
    "handover_notes": "引継ぎ事項",
}

_MONTHLY_PLAN_INPUT_LABELS = {
    "target_month": "対象月",
    "class_name": "クラス名",
    "owner_name": "担当者",
    "related_term_key": "該当期",
    "previous_reflection": "前月の反省",
    "current_children_snapshot": "今の子どもの姿",
    "play_interests": "興味のある遊び・生活",
    "seasonal_context": "季節の文脈",
    "family_context": "家庭の状況",
    "class_notes": "クラス全体の留意事項",
}

_PROFILE_META_FIELDS = {
    "nursery_name",
    "missing_input_policy",
    "confirmation_marker",
    "evidence_tag_policy",
    "privacy_policy",
    "version",
    "approved",
    "enabled_field_keys",
}

_PLAN_META_FIELDS = {
    "school_year",
    "class_name",
    "age_group",
}

_MONTHLY_PLAN_META_FIELDS = {
    "target_month",
    "class_name",
    "owner_name",
    "related_term_key",
}

_SECTION_DEFINITIONS = {definition.key: definition for definition in annual_section_definitions()}
_MONTHLY_SECTION_DEFINITIONS = {definition.key: definition for definition in MONTHLY_SECTIONS}

_SECTION_POLICY = {
    "annual_goal": {
        "section_kind": "annual_goal",
        "focus": "年度全体のねらいを一段落でまとめ、園の方針とクラスの育ちをつなぐ。",
        "must_include": [
            "クラスの一年間の育ちの方向",
            "園の保育目標や子ども観とのつながり",
            "入力された見通しと重点の反映",
        ],
        "avoid": ["短いスローガンだけで終えること", "未確定な断定"],
    },
    "outlook": {
        "section_kind": "outlook",
        "focus": "その期に期待する姿と育ちの流れを示す。",
        "must_include": ["期のテーマに沿った子どもの姿", "年間の軸につながる育ち"],
        "avoid": ["全期で同じ文の反復"],
    },
    "environment": {
        "section_kind": "environment",
        "focus": "場所、素材、活動の流れを具体的に描き、環境構成が見える文にする。",
        "must_include": ["室内・戸外環境の整え方", "継続する遊びや素材の扱い"],
        "avoid": ["抽象語だけで終えること"],
    },
    "support": {
        "section_kind": "support",
        "focus": "保育者の具体的な援助行為を中心に書く。",
        "must_include": ["見守り、声かけ、環境調整などの具体的な援助", "一人ひとりへの配慮"],
        "avoid": ["援助方針の丸写し"],
    },
    "family_collaboration": {
        "section_kind": "family_collaboration",
        "focus": "家庭との共有方法や地域とのつながりを、園での実践が見える文にする。",
        "must_include": ["日々の共有や伝え方", "行事や生活との接続"],
        "avoid": ["家庭連携という語だけの反復"],
    },
    "reflection_viewpoint": {
        "section_kind": "reflection_viewpoint",
        "focus": "保育者が振り返りに使える観点を整理する。",
        "must_include": ["子どもの姿に関する観点", "環境構成と援助に関する観点"],
        "avoid": ["長い説明文だけにすること"],
    },
}

_MONTHLY_SECTION_POLICY = {
    "monthly_goal": {
        "section_kind": "monthly_goal",
        "focus": "年間計画の該当期と今月の子どもの姿をつなぎ、今月のねらいをまとめる。",
        "must_include": ["対象月の文脈", "前月の反省からのつながり", "今の子どもの姿"],
        "avoid": ["年間計画の文をそのまま写すこと"],
    },
    "children_snapshot": {
        "section_kind": "children_snapshot",
        "focus": "現在の子どもの姿を専門的かつ具体的に捉え直す。",
        "must_include": ["前月からの変化", "遊びや生活の中の関わり"],
        "avoid": ["短いメモをそのまま引用すること"],
    },
    "monthly_environment": {
        "section_kind": "monthly_environment",
        "focus": "今月の遊びや生活が続く環境構成を具体的に書く。",
        "must_include": ["素材や場の整え方", "季節や生活リズムの反映"],
        "avoid": ["抽象語のみの列挙"],
    },
    "monthly_support": {
        "section_kind": "monthly_support",
        "focus": "今月必要な保育者の援助を具体的な動きとして書く。",
        "must_include": ["声かけ、見守り、関係調整", "クラス全体の留意事項"],
        "avoid": ["園の方針の丸写し"],
    },
    "monthly_family_collaboration": {
        "section_kind": "monthly_family_collaboration",
        "focus": "家庭との共有や生活の連続性を具体的に書く。",
        "must_include": ["家庭状況への配慮", "日々の伝え合い"],
        "avoid": ["個人情報や家庭の詳細事情の記述"],
    },
    "monthly_reflection_viewpoint": {
        "section_kind": "monthly_reflection_viewpoint",
        "focus": "月末に確認できる振り返り観点を整理する。",
        "must_include": ["年間計画とのつながり", "次月への確認観点"],
        "avoid": ["評価項目の羅列だけにすること"],
    },
}

_SECTION_PROFILE_FIELDS = {
    "annual_goal": (
        "philosophy",
        "childcare_goal",
        "desired_child_image",
        "child_view",
        "play_view",
        "sentence_tone",
        "preferred_expressions",
        "avoid_expressions",
    ),
    "outlook": ("target_age_group", "class_configuration", "desired_child_image", "childcare_goal"),
    "environment": ("indoor_environment", "outdoor_environment", "corner_play", "community_resources"),
    "support": (
        "support_policy",
        "child_view",
        "play_view",
        "health_and_safety_policy",
        "inclusive_policy",
    ),
    "family_collaboration": (
        "family_collaboration_policy",
        "local_collaboration_policy",
        "community_resources",
    ),
    "reflection_viewpoint": ("childcare_goal", "desired_child_image", "child_view", "play_view"),
}

_SECTION_PLAN_FIELDS = {
    "annual_goal": ("school_year", "class_name", "age_group", "class_outlook", "focus_growth"),
    "outlook": ("class_outlook", "focus_growth"),
    "environment": ("seasonal_context", "community_resources"),
    "support": ("care_points", "handover_notes"),
    "family_collaboration": ("annual_events", "community_resources"),
    "reflection_viewpoint": ("focus_growth", "class_outlook"),
}

_MONTHLY_SECTION_PROFILE_FIELDS = {
    "monthly_goal": ("philosophy", "childcare_goal", "curriculum_focus", "sentence_tone"),
    "children_snapshot": ("child_view", "play_view", "desired_child_image"),
    "monthly_environment": ("indoor_environment", "outdoor_environment", "corner_play", "daily_rhythm"),
    "monthly_support": ("support_policy", "play_view", "health_and_safety_policy", "inclusive_policy"),
    "monthly_family_collaboration": ("family_collaboration_policy", "privacy_policy"),
    "monthly_reflection_viewpoint": ("assessment_policy", "childcare_goal", "desired_child_image"),
}

_MONTHLY_SECTION_PLAN_FIELDS = {
    "monthly_goal": (
        "target_month",
        "class_name",
        "related_term_key",
        "previous_reflection",
        "current_children_snapshot",
    ),
    "children_snapshot": ("previous_reflection", "current_children_snapshot", "play_interests"),
    "monthly_environment": ("play_interests", "seasonal_context", "class_notes"),
    "monthly_support": ("current_children_snapshot", "play_interests", "class_notes"),
    "monthly_family_collaboration": ("family_context", "seasonal_context"),
    "monthly_reflection_viewpoint": ("previous_reflection", "current_children_snapshot", "class_notes"),
}


def build_annual_plan_preview_messages(
    *,
    profile: NurseryProfile,
    plan_input: AnnualPlanInput,
    fallback_plan: GeneratedPlan,
) -> list[dict[str, str]]:
    payload = {
        "task": "annual_plan_preview",
        "nursery_profile": _profile_payload(profile),
        "plan_input": asdict(plan_input),
        "plan_outline": [
            {
                "section_key": block.section_key,
                "title": block.title,
            }
            for block in fallback_plan.blocks
        ],
        "missing_inputs": list(fallback_plan.missing_inputs),
        "section_definitions": [
            {
                "section_key": section.key,
                "title": section.title,
                "purpose": section.purpose,
            }
            for section in annual_section_definitions()
        ],
        "constraints": {
            "document_type": "annual",
            "must_preserve_section_keys": [block.section_key for block in fallback_plan.blocks],
            "must_output_json_only": True,
            "must_respect_confirmation_policy": True,
            "must_keep_server_side_reviewable_structure": True,
        },
    }
    return [
        {"role": "system", "content": ANNUAL_PREVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def build_annual_plan_block_messages(
    *,
    profile: NurseryProfile,
    plan_input: AnnualPlanInput,
    fallback_plan: GeneratedPlan,
    fallback_block: SectionBlock,
) -> list[dict[str, str]]:
    section_kind = _section_kind(fallback_block.section_key)
    definition = _SECTION_DEFINITIONS.get(fallback_block.section_key)
    weak_input_hints: list[dict[str, str]] = []
    weak_values: list[str] = []

    profile_payload = _select_profile_payload(
        profile,
        section_kind=section_kind,
        weak_input_hints=weak_input_hints,
        field_map=_SECTION_PROFILE_FIELDS,
    )
    plan_payload = _select_input_payload(
        plan_input,
        section_kind=section_kind,
        weak_input_hints=weak_input_hints,
        field_map=_SECTION_PLAN_FIELDS,
        meta_fields=_PLAN_META_FIELDS,
        label_map=_PLAN_INPUT_LABELS,
    )
    weak_values = [item["value"] for item in weak_input_hints if item.get("value")]

    payload = _block_prompt_payload(
        task="annual_plan_block_preview",
        document_title=fallback_plan.title,
        section_kind=section_kind,
        definition_purpose=definition.purpose if definition else "annual plan section",
        section_guidance=_SECTION_POLICY[section_kind],
        profile_payload=profile_payload,
        plan_payload=plan_payload,
        weak_input_hints=weak_input_hints,
        fallback_block=fallback_block,
        weak_values=weak_values,
    )
    return [
        {"role": "system", "content": ANNUAL_BLOCK_PREVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def build_monthly_plan_block_messages(
    *,
    profile: NurseryProfile,
    annual_plan: GeneratedPlan,
    plan_input: MonthlyPlanInput,
    fallback_plan: GeneratedPlan,
    fallback_block: SectionBlock,
) -> list[dict[str, str]]:
    section_kind = _monthly_section_kind(fallback_block.section_key)
    definition = _MONTHLY_SECTION_DEFINITIONS.get(fallback_block.section_key)
    weak_input_hints: list[dict[str, str]] = []

    profile_payload = _select_profile_payload(
        profile,
        section_kind=section_kind,
        weak_input_hints=weak_input_hints,
        field_map=_MONTHLY_SECTION_PROFILE_FIELDS,
    )
    plan_payload = _select_input_payload(
        plan_input,
        section_kind=section_kind,
        weak_input_hints=weak_input_hints,
        field_map=_MONTHLY_SECTION_PLAN_FIELDS,
        meta_fields=_MONTHLY_PLAN_META_FIELDS,
        label_map=_MONTHLY_PLAN_INPUT_LABELS,
    )
    weak_values = [item["value"] for item in weak_input_hints if item.get("value")]

    payload = _block_prompt_payload(
        task="monthly_plan_block_preview",
        document_title=fallback_plan.title,
        section_kind=section_kind,
        definition_purpose=definition.purpose if definition else "monthly plan section",
        section_guidance=_MONTHLY_SECTION_POLICY[section_kind],
        profile_payload=profile_payload,
        plan_payload=plan_payload,
        weak_input_hints=weak_input_hints,
        fallback_block=fallback_block,
        weak_values=weak_values,
    )
    payload["related_annual_context"] = _related_annual_context(
        annual_plan,
        related_term_key=plan_input.related_term_key,
        section_kind=section_kind,
    )
    return [
        {"role": "system", "content": MONTHLY_BLOCK_PREVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def _profile_payload(profile: NurseryProfile) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field_name, value in asdict(profile).items():
        if field_name in _PROFILE_META_FIELDS:
            payload[field_name] = value
            continue
        if field_name in profile.enabled_field_keys and value:
            payload[field_name] = value
    return payload


def _select_profile_payload(
    profile: NurseryProfile,
    *,
    section_kind: str,
    weak_input_hints: list[dict[str, str]],
    field_map: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    requested_fields = set(field_map.get(section_kind, ())) | _PROFILE_META_FIELDS
    payload: dict[str, object] = {}
    for field_name in requested_fields:
        value = getattr(profile, field_name, None)
        if field_name not in _PROFILE_META_FIELDS and field_name not in profile.enabled_field_keys:
            continue
        if value in (None, "", (), []):
            continue
        if field_name in _PROFILE_META_FIELDS:
            payload[field_name] = value
            continue
        if _should_treat_as_weak_hint(field_name, str(value)):
            weak_input_hints.append(_weak_input_hint(field_name, str(value), source="nursery_profile"))
            continue
        payload[field_name] = value
    return payload


def _select_input_payload(
    plan_input: Any,
    *,
    section_kind: str,
    weak_input_hints: list[dict[str, str]],
    field_map: dict[str, tuple[str, ...]],
    meta_fields: set[str],
    label_map: dict[str, str],
) -> dict[str, object]:
    requested_fields = set(field_map.get(section_kind, ())) | meta_fields
    payload: dict[str, object] = {}
    for field_name in requested_fields:
        value = getattr(plan_input, field_name, None)
        if value in (None, "", (), []):
            continue
        if field_name in meta_fields:
            payload[field_name] = value
            continue
        if _should_treat_as_weak_hint(field_name, str(value)):
            weak_input_hints.append(
                _weak_input_hint(field_name, str(value), source="plan_input", label_map=label_map)
            )
            continue
        payload[field_name] = value
    return payload


def _block_prompt_payload(
    *,
    task: str,
    document_title: str,
    section_kind: str,
    definition_purpose: str,
    section_guidance: dict[str, object],
    profile_payload: dict[str, object],
    plan_payload: dict[str, object],
    weak_input_hints: list[dict[str, str]],
    fallback_block: SectionBlock,
    weak_values: list[str],
) -> dict[str, object]:
    block_payload: dict[str, object] = {
        "section_key": fallback_block.section_key,
        "title": fallback_block.title,
        "purpose": definition_purpose,
        "needs_confirmation": fallback_block.needs_confirmation,
        "editor_note": fallback_block.editor_note,
        "source_ref_labels": [source_ref.label for source_ref in fallback_block.source_refs],
        "section_guidance": section_guidance,
    }
    baseline_body = _safe_baseline_body(fallback_block.body, weak_values)
    if baseline_body:
        block_payload["baseline_body"] = baseline_body
    else:
        block_payload["baseline_note"] = (
            "The previous draft included short memo-like inputs that should not be quoted verbatim. "
            "Rewrite naturally from the structured inputs and section guidance."
        )

    return {
        "task": task,
        "document_title": document_title,
        "nursery_profile": profile_payload,
        "plan_input": plan_payload,
        "weak_input_hints": weak_input_hints,
        "block": block_payload,
        "constraints": {
            "section_kind": section_kind,
            "must_output_json_only": True,
            "json_keys": ["body", "needs_confirmation", "editor_note"],
            "body_style": "concise Japanese nursery planning prose",
            "keep_reviewable_length": True,
            "do_not_include_sensitive_personal_information": True,
        },
    }


def _related_annual_context(
    annual_plan: GeneratedPlan,
    *,
    related_term_key: str,
    section_kind: str,
) -> list[dict[str, str]]:
    suffixes_by_section = {
        "monthly_goal": ("outlook", "support", "reflection_viewpoint"),
        "children_snapshot": ("outlook", "reflection_viewpoint"),
        "monthly_environment": ("environment", "outlook"),
        "monthly_support": ("support", "outlook"),
        "monthly_family_collaboration": ("family_collaboration", "outlook"),
        "monthly_reflection_viewpoint": ("reflection_viewpoint", "support"),
    }
    suffixes = suffixes_by_section.get(section_kind, ("outlook", "support"))
    context_blocks: list[SectionBlock] = []
    for block in annual_plan.blocks:
        if block.section_key == "annual_goal":
            context_blocks.append(block)
            continue
        if not block.section_key.startswith(related_term_key):
            continue
        if block.section_key.endswith(suffixes):
            context_blocks.append(block)
    return [
        {
            "section_key": block.section_key,
            "title": block.title,
            "body": block.body[:1000],
        }
        for block in context_blocks[:4]
    ]


def _section_kind(section_key: str) -> str:
    if section_key == "annual_goal":
        return "annual_goal"
    for section_kind in (
        "outlook",
        "environment",
        "support",
        "family_collaboration",
        "reflection_viewpoint",
    ):
        suffix = f"_{section_kind}"
        if section_key.endswith(suffix):
            return section_kind
    return "annual_goal"


def _monthly_section_kind(section_key: str) -> str:
    if section_key in _MONTHLY_SECTION_POLICY:
        return section_key
    return "monthly_goal"


def _should_treat_as_weak_hint(field_name: str, value: str) -> bool:
    if field_name in _PROFILE_META_FIELDS or field_name in _PLAN_META_FIELDS or field_name in _MONTHLY_PLAN_META_FIELDS:
        return False
    return _is_short_prompt_text(value)


def _is_short_prompt_text(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    compact = text.replace(" ", "").replace("　", "")
    if len(compact) > 12:
        return False
    punctuation = ("。", "、", "\n", "/", "・", ",", "，", ":", "：", ";", "；")
    return not any(marker in text for marker in punctuation)


def _weak_input_hint(
    field_name: str,
    value: str,
    *,
    source: str,
    label_map: dict[str, str] | None = None,
) -> dict[str, str]:
    return {
        "field": field_name,
        "label": _field_label(field_name, label_map=label_map),
        "source": source,
        "value": value.strip(),
        "instruction": (
            "This input is too short for verbatim quotation. Use it only as a loose hint and paraphrase it "
            "into natural nursery-planning language if the surrounding context supports it."
        ),
    }


def _field_label(field_name: str, *, label_map: dict[str, str] | None = None) -> str:
    if field_name in PROFILE_FIELD_MAP:
        return PROFILE_FIELD_MAP[field_name].label
    if label_map and field_name in label_map:
        return label_map[field_name]
    return _PLAN_INPUT_LABELS.get(field_name, field_name)


def _safe_baseline_body(text: str, weak_values: list[str]) -> str:
    if not text.strip():
        return ""
    if any(value and value in text for value in weak_values):
        return ""
    return text
