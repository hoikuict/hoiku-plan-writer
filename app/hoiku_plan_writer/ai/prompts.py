from __future__ import annotations

import json
from dataclasses import asdict

from ..domain.models import AnnualPlanInput, GeneratedPlan, NurseryProfile, SectionBlock
from ..domain.profile_fields import PROFILE_FIELD_MAP
from ..domain.section_catalog import annual_section_definitions

ANNUAL_PREVIEW_SYSTEM_PROMPT = """You help draft Japanese nursery planning documents.
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
    "handover_notes": "引き継ぎ事項",
}

_PROFILE_META_FIELDS = {
    "nursery_name",
    "missing_input_policy",
    "confirmation_marker",
    "evidence_tag_policy",
    "version",
    "approved",
    "enabled_field_keys",
}

_PLAN_META_FIELDS = {
    "school_year",
    "class_name",
    "age_group",
}

_SECTION_DEFINITIONS = {definition.key: definition for definition in annual_section_definitions()}
_SECTION_POLICY = {
    "annual_goal": {
        "section_kind": "annual_goal",
        "focus": "年度全体のねらいを一段落でまとめ、園の方針とクラスの育ちをつなぐ。",
        "must_include": [
            "クラスの一年間の育ちの方向",
            "園の保育目標や子ども像とのつながり",
            "理念や子ども観がどう反映されるか",
        ],
        "avoid": [
            "短いスローガンのそのまま引用",
            "理念や方針の単純な羅列",
            "未完成な文の断片",
        ],
    },
    "outlook": {
        "section_kind": "outlook",
        "focus": "その期に期待する姿と育ちの流れを示す。",
        "must_include": [
            "期のテーマに沿った子どもの姿",
            "クラスの実態や見通しとのつながり",
            "年間の軸につながる育ちの方向",
        ],
        "avoid": [
            "年間目標の単純な言い換えだけで終えること",
            "全期で同じ文の反復",
        ],
    },
    "environment": {
        "section_kind": "environment",
        "focus": "場や素材、活動の流れを具体的に描き、環境構成が見える文にする。",
        "must_include": [
            "室内と戸外の環境の整え方",
            "継続する遊びや素材の扱い",
            "必要に応じた地域資源の活かし方",
        ],
        "avoid": [
            "抽象語だけで終えること",
            "『地域の資源』などの一般語の反復",
        ],
    },
    "support": {
        "section_kind": "support",
        "focus": "保育者の具体的な援助行為を中心に書き、観察、待つ、言葉を添える、環境調整するなどの動きを見せる。",
        "must_include": [
            "具体的な保育者の援助行為を2つ以上",
            "安全や参加のしやすさへの配慮",
            "一人ひとりの状況に応じた関わり",
        ],
        "avoid": [
            "援助方針の丸写し",
            "文法が崩れた接続",
            "短い語句をそのまま並べること",
        ],
    },
    "family_collaboration": {
        "section_kind": "family_collaboration",
        "focus": "家庭との共有方法や地域との連携のしかたを、園での実践が見える文にする。",
        "must_include": [
            "日々の共有や伝え方",
            "必要に応じた行事や生活との接続",
            "地域との関わり方の見通し",
        ],
        "avoid": [
            "行事名一語のそのまま引用",
            "家庭連携と地域連携の単調な繰り返し",
        ],
    },
    "reflection_viewpoint": {
        "section_kind": "reflection_viewpoint",
        "focus": "保育者が振り返りに使える観点を、短い問いの形で整理する。",
        "must_include": [
            "3から4項目の振り返り観点",
            "子どもの姿に関する観点",
            "環境と援助に関する観点",
        ],
        "avoid": [
            "長い散文にすること",
            "同じ問いの繰り返し",
        ],
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
    "outlook": (
        "target_age_group",
        "class_configuration",
        "desired_child_image",
        "childcare_goal",
    ),
    "environment": (
        "indoor_environment",
        "outdoor_environment",
        "corner_play",
        "community_resources",
    ),
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
    "reflection_viewpoint": (
        "childcare_goal",
        "desired_child_image",
        "child_view",
        "play_view",
    ),
}
_SECTION_PLAN_FIELDS = {
    "annual_goal": (
        "school_year",
        "class_name",
        "age_group",
        "class_outlook",
        "focus_growth",
    ),
    "outlook": (
        "class_outlook",
        "focus_growth",
    ),
    "environment": (
        "seasonal_context",
        "community_resources",
    ),
    "support": (
        "care_points",
        "handover_notes",
    ),
    "family_collaboration": (
        "annual_events",
        "community_resources",
    ),
    "reflection_viewpoint": (
        "focus_growth",
        "class_outlook",
    ),
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
    definition = _SECTION_DEFINITIONS.get(fallback_block.section_key)
    section_kind = _section_kind(fallback_block.section_key)
    weak_input_hints: list[dict[str, str]] = []

    profile_payload = _select_profile_payload(profile, section_kind=section_kind, weak_input_hints=weak_input_hints)
    plan_payload = _select_plan_input_payload(plan_input, section_kind=section_kind, weak_input_hints=weak_input_hints)
    weak_values = [item["value"] for item in weak_input_hints if item.get("value")]
    baseline_body = _safe_baseline_body(fallback_block.body, weak_values)

    block_payload = {
        "section_key": fallback_block.section_key,
        "title": fallback_block.title,
        "purpose": definition.purpose if definition else "annual plan section",
        "needs_confirmation": fallback_block.needs_confirmation,
        "editor_note": fallback_block.editor_note,
        "source_ref_labels": [source_ref.label for source_ref in fallback_block.source_refs],
        "section_guidance": _SECTION_POLICY[section_kind],
    }
    if baseline_body:
        block_payload["baseline_body"] = baseline_body
    else:
        block_payload["baseline_note"] = "The previous draft included short memo-like inputs that should not be quoted verbatim. Rewrite naturally from the structured inputs and section guidance."

    payload = {
        "task": "annual_plan_block_preview",
        "document_title": fallback_plan.title,
        "nursery_profile": profile_payload,
        "plan_input": plan_payload,
        "weak_input_hints": weak_input_hints,
        "block": block_payload,
        "constraints": {
            "must_output_json_only": True,
            "json_keys": ["body", "needs_confirmation", "editor_note"],
            "body_style": "concise Japanese nursery planning prose",
            "keep_reviewable_length": True,
        },
    }
    return [
        {"role": "system", "content": ANNUAL_BLOCK_PREVIEW_SYSTEM_PROMPT},
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
) -> dict[str, object]:
    requested_fields = set(_SECTION_PROFILE_FIELDS.get(section_kind, ())) | _PROFILE_META_FIELDS
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



def _select_plan_input_payload(
    plan_input: AnnualPlanInput,
    *,
    section_kind: str,
    weak_input_hints: list[dict[str, str]],
) -> dict[str, object]:
    requested_fields = set(_SECTION_PLAN_FIELDS.get(section_kind, ())) | _PLAN_META_FIELDS
    payload: dict[str, object] = {}
    for field_name in requested_fields:
        value = getattr(plan_input, field_name, None)
        if value in (None, "", (), []):
            continue
        if field_name in _PLAN_META_FIELDS:
            payload[field_name] = value
            continue
        if _should_treat_as_weak_hint(field_name, str(value)):
            weak_input_hints.append(_weak_input_hint(field_name, str(value), source="plan_input"))
            continue
        payload[field_name] = value
    return payload



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



def _should_treat_as_weak_hint(field_name: str, value: str) -> bool:
    if field_name in _PROFILE_META_FIELDS or field_name in _PLAN_META_FIELDS:
        return False
    return _is_short_prompt_text(value)



def _is_short_prompt_text(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    compact = text.replace(" ", "").replace("　", "")
    if len(compact) > 12:
        return False
    if any(marker in text for marker in ("。", "、", "\n", "/", "／", ",", "，", ":", "：", ";", "；")):
        return False
    return True



def _weak_input_hint(field_name: str, value: str, *, source: str) -> dict[str, str]:
    return {
        "field": field_name,
        "label": _field_label(field_name),
        "source": source,
        "value": value.strip(),
        "instruction": "This input is too short for verbatim quotation. Use it only as a loose hint and paraphrase it into natural nursery-planning language if the surrounding context supports it.",
    }



def _field_label(field_name: str) -> str:
    if field_name in PROFILE_FIELD_MAP:
        return PROFILE_FIELD_MAP[field_name].label
    return _PLAN_INPUT_LABELS.get(field_name, field_name)



def _safe_baseline_body(text: str, weak_values: list[str]) -> str:
    if not text.strip():
        return ""
    if any(value and value in text for value in weak_values):
        return ""
    return text