from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable


class ProfileFieldLevel(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class ProfileFieldSpec:
    key: str
    label: str
    group: str
    level: ProfileFieldLevel
    use_in_generation: bool = True


@dataclass(frozen=True, slots=True)
class ProfileFieldIssue:
    key: str
    label: str
    group: str
    message: str


@dataclass(frozen=True, slots=True)
class ProfileReview:
    missing_required: list[ProfileFieldIssue]
    missing_recommended: list[ProfileFieldIssue]
    privacy_warnings: list[ProfileFieldIssue]
    required_total: int
    required_completed: int
    recommended_total: int
    recommended_completed: int
    optional_total: int
    optional_completed: int

    @property
    def can_activate(self) -> bool:
        return not self.missing_required

    @property
    def required_summary(self) -> str:
        return f"{self.required_completed}/{self.required_total}"

    @property
    def recommended_summary(self) -> str:
        return f"{self.recommended_completed}/{self.recommended_total}"

    @property
    def optional_summary(self) -> str:
        return f"{self.optional_completed}/{self.optional_total}"


PROFILE_FIELD_SPECS: tuple[ProfileFieldSpec, ...] = (
    ProfileFieldSpec("nursery_name", "園名", "基本情報", ProfileFieldLevel.REQUIRED),
    ProfileFieldSpec("target_age_group", "プロフィール対象範囲", "基本情報", ProfileFieldLevel.REQUIRED),
    ProfileFieldSpec("class_configuration", "標準クラス編成", "基本情報", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("local_context", "地域特性", "基本情報", ProfileFieldLevel.OPTIONAL),
    ProfileFieldSpec("philosophy", "理念", "保育の軸", ProfileFieldLevel.REQUIRED),
    ProfileFieldSpec("childcare_goal", "保育目標", "保育の軸", ProfileFieldLevel.REQUIRED),
    ProfileFieldSpec("desired_child_image", "育てたい子ども像", "保育の軸", ProfileFieldLevel.REQUIRED),
    ProfileFieldSpec("child_view", "子ども観", "保育の軸", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("play_view", "遊びの考え方", "保育の軸", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("support_policy", "援助方針", "保育の軸", ProfileFieldLevel.REQUIRED),
    ProfileFieldSpec("curriculum_focus", "全体的な計画との接続", "保育の軸", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("assessment_policy", "評価、振り返り観点", "保育の軸", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("indoor_environment", "室内環境", "環境と連携", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("outdoor_environment", "戸外環境", "環境と連携", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("corner_play", "コーナー保育", "環境と連携", ProfileFieldLevel.OPTIONAL),
    ProfileFieldSpec("community_resources", "地域資源", "環境と連携", ProfileFieldLevel.OPTIONAL),
    ProfileFieldSpec("family_collaboration_policy", "家庭連携方針", "環境と連携", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("local_collaboration_policy", "地域との関わり", "環境と連携", ProfileFieldLevel.OPTIONAL),
    ProfileFieldSpec("health_and_safety_policy", "健康・安全方針", "環境と連携", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("inclusive_policy", "インクルーシブ方針", "環境と連携", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("daily_rhythm", "生活リズムの基本", "環境と連携", ProfileFieldLevel.OPTIONAL),
    ProfileFieldSpec("preferred_expressions", "よく使う表現", "文体ルール", ProfileFieldLevel.OPTIONAL),
    ProfileFieldSpec("avoid_expressions", "避けたい表現", "文体ルール", ProfileFieldLevel.OPTIONAL),
    ProfileFieldSpec("sentence_tone", "文末トーン", "文体ルール", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("document_format_notes", "文書書式メモ", "文体ルール", ProfileFieldLevel.RECOMMENDED),
    ProfileFieldSpec("missing_input_policy", "未入力時の扱い", "AI 出力ルール", ProfileFieldLevel.ADMIN),
    ProfileFieldSpec("confirmation_marker", "要確認表示", "AI 出力ルール", ProfileFieldLevel.ADMIN),
    ProfileFieldSpec("evidence_tag_policy", "根拠タグ表示方針", "AI 出力ルール", ProfileFieldLevel.ADMIN),
    ProfileFieldSpec("privacy_policy", "個人情報の扱い", "AI 出力ルール", ProfileFieldLevel.ADMIN),
)

PROFILE_FIELD_BY_KEY = {field.key: field for field in PROFILE_FIELD_SPECS}
PROFILE_FIELD_MAP = PROFILE_FIELD_BY_KEY
PROFILE_DEFAULT_ENABLED_KEYS = tuple(
    field.key for field in PROFILE_FIELD_SPECS if field.use_in_generation and field.level != ProfileFieldLevel.ADMIN
)


def normalize_enabled_field_keys(field_keys: Iterable[str] | None) -> tuple[str, ...]:
    requested = set(field_keys or ())
    return tuple(
        field.key
        for field in PROFILE_FIELD_SPECS
        if field.use_in_generation
        and field.level != ProfileFieldLevel.ADMIN
        and (field.level == ProfileFieldLevel.REQUIRED or field.key in requested)
    )

_PHONE_PATTERN = re.compile(r"\d{2,4}[-ー−]\d{2,4}[-ー−]\d{3,4}")
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SENSITIVE_TERMS = (
    "アレルギー",
    "診断",
    "障害",
    "ADHD",
    "ASD",
    "自閉",
    "喘息",
    "てんかん",
    "服薬",
    "通院",
    "住所",
    "電話",
    "連絡先",
    "保護者名",
)
_COMMON_NAME_TERMS = (
    "山田",
    "佐藤",
    "鈴木",
    "高橋",
    "田中",
    "伊藤",
    "渡辺",
    "中村",
    "小林",
    "加藤",
)


def review_profile_completeness(profile: Any) -> ProfileReview:
    missing_required = _missing_fields(profile, ProfileFieldLevel.REQUIRED)
    missing_recommended = _missing_fields(profile, ProfileFieldLevel.RECOMMENDED)
    privacy_warnings = _privacy_warnings(profile)

    required_fields = _fields_by_level(ProfileFieldLevel.REQUIRED)
    recommended_fields = _fields_by_level(ProfileFieldLevel.RECOMMENDED)
    optional_fields = _fields_by_level(ProfileFieldLevel.OPTIONAL)

    return ProfileReview(
        missing_required=missing_required,
        missing_recommended=missing_recommended,
        privacy_warnings=privacy_warnings,
        required_total=len(required_fields),
        required_completed=len(required_fields) - len(missing_required),
        recommended_total=len(recommended_fields),
        recommended_completed=len(recommended_fields) - len(missing_recommended),
        optional_total=len(optional_fields),
        optional_completed=sum(1 for field in optional_fields if _value(profile, field.key)),
    )


def field_label(key: str) -> str:
    return PROFILE_FIELD_BY_KEY.get(key, ProfileFieldSpec(key, key, "", ProfileFieldLevel.OPTIONAL)).label


def _fields_by_level(level: ProfileFieldLevel) -> list[ProfileFieldSpec]:
    return [field for field in PROFILE_FIELD_SPECS if field.level == level]


def _missing_fields(profile: Any, level: ProfileFieldLevel) -> list[ProfileFieldIssue]:
    issues: list[ProfileFieldIssue] = []
    for field in _fields_by_level(level):
        if _value(profile, field.key):
            continue
        issues.append(
            ProfileFieldIssue(
                key=field.key,
                label=field.label,
                group=field.group,
                message=f"{field.label}が未入力です。",
            )
        )
    return issues


def _privacy_warnings(profile: Any) -> list[ProfileFieldIssue]:
    warnings: list[ProfileFieldIssue] = []
    for field in PROFILE_FIELD_SPECS:
        if field.level == ProfileFieldLevel.ADMIN:
            continue
        text = _value(profile, field.key)
        if not text:
            continue
        message = _privacy_message(text)
        if not message:
            continue
        warnings.append(
            ProfileFieldIssue(
                key=field.key,
                label=field.label,
                group=field.group,
                message=message,
            )
        )
    return warnings


def _privacy_message(text: str) -> str:
    if _PHONE_PATTERN.search(text):
        return "電話番号らしい文字列が含まれています。AI コンテキストから除外してください。"
    if _EMAIL_PATTERN.search(text):
        return "メールアドレスらしい文字列が含まれています。AI コンテキストから除外してください。"
    for term in _SENSITIVE_TERMS:
        if term in text:
            return f"「{term}」に近い個人・健康情報が含まれる可能性があります。"
    for term in _COMMON_NAME_TERMS:
        if term in text:
            return "個人名らしい表現が含まれる可能性があります。クラス単位の抽象表現にしてください。"
    return ""


def _value(profile: Any, key: str) -> str:
    if isinstance(profile, dict):
        value = profile.get(key, "")
    else:
        value = getattr(profile, key, "")
    return str(value or "").strip()
