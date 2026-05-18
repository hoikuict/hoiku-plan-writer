from __future__ import annotations

from datetime import date
from typing import Iterable

from ..domain.models import NurseryProfile, SectionBlock, SourceRef
from ..domain.safety import (
    FacilityType,
    SafetyActionItem,
    SafetyAxisStatus,
    SafetyComplianceResult,
    SafetyComplianceStandard,
    SafetyFacilityProfile,
    SafetyLogType,
    SafetyPlanDraft,
    SafetyPlanStatus,
    SafetyRiskStatus,
    safety_evidence_tags,
    safety_official_source_ref,
)


REQUIRED_SECTION_KEYS = (
    "safety_basic_policy",
    "safety_facility_profile",
    "safety_annual_schedule",
    "safety_inspection",
    "safety_manuals",
    "safety_child_guidance",
    "safety_staff_training",
    "safety_parent_notice",
    "safety_incident_prevention",
    "safety_review",
    "safety_evidence",
)


SAFETY_LOG_TYPE_LABELS = {
    SafetyLogType.TRAINING_DRILL: "研修・訓練",
    SafetyLogType.PARENT_NOTICE: "保護者周知",
    SafetyLogType.REVIEW: "見直し",
    SafetyLogType.SCHOOL_SAFETY_ACTION: "学校安全計画の取組",
}


def generate_safety_plan(
    profile: NurseryProfile | None,
    facility_profile: SafetyFacilityProfile,
    *,
    school_year: int,
    established_on: date | None,
) -> SafetyPlanDraft:
    missing_inputs = _collect_missing_inputs(facility_profile, school_year, established_on)
    confirmation_note = _confirmation_text(profile, missing_inputs)
    source_refs = _source_refs(profile)
    action_items = _build_action_items(facility_profile)

    blocks = [
        _block(
            "safety_basic_policy",
            "基本方針",
            _with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        f"{facility_profile.facility_name}は、{school_year}年度の{facility_profile.compliance_standard_label}として、児童が安心して生活し遊ぶための安全確保を計画的に実施する。",
                        f"施設類型は{facility_profile.facility_type_label}とし、{_basis_text(facility_profile)}を踏まえて、点検・安全指導・研修訓練・周知・見直しを継続する。",
                        f"園の安全方針: {facility_profile.safety_policy or _profile_text(profile, 'health_and_safety_policy', '日常の保育の中で安全確認を重ね、職員間で共有する。')}",
                    ]
                ),
            ),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_facility_profile",
            "施設・地域の特徴",
            _with_confirmation(
                confirmation_note,
                "\n".join(
                    [
                        f"所在地自治体: {facility_profile.municipality or '要確認'}",
                        f"定員・年齢構成: {facility_profile.capacity_summary or '要確認'} / {facility_profile.age_groups or '要確認'}",
                        f"園外活動: {_yes_no(facility_profile.has_outdoor_activity)}。主要ルート・活動先: {facility_profile.outdoor_routes or _profile_text(profile, 'community_resources', '散歩コース、近隣公園等を確認する。')}",
                        f"立地リスク: {facility_profile.disaster_risks or '地震、風水害等を地域実情に応じて確認する。'}",
                        f"送迎バス: {_yes_no(facility_profile.has_bus)} / プール・水遊び: {_yes_no(facility_profile.has_pool)} / 給食・調理: {_yes_no(facility_profile.has_kitchen)}",
                    ]
                ),
            ),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_annual_schedule",
            "年間スケジュール",
            _with_confirmation(confirmation_note, _annual_schedule_text(action_items)),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_inspection",
            "施設・設備等の安全点検",
            "\n".join(
                [
                    "園舎、保育室、遊具、防火設備、避難経路、門扉、備品を月次又は活動前に点検し、チェックリストに記録する。",
                    "散歩や園外活動を行う場合は、散歩コース、横断箇所、公園、水辺、交通量、緊急時の集合場所を年度初めと活動前に確認する。",
                    "改善が必要な事項は担当者と期限を定め、完了日まで追跡する。",
                ]
            ),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_manuals",
            "マニュアル・役割分担",
            "\n".join(_manual_lines(facility_profile)),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_child_guidance",
            "児童への安全指導",
            "\n".join(
                [
                    "生活の中で、危険な場所、遊具の使い方、廊下や階段での約束、災害時の行動を発達に応じて伝える。",
                    "交通安全について、散歩前の約束、横断時の確認、職員の合図を待つことを繰り返し確認する。",
                    "避難訓練では、音や放送に慣れ、職員のそばに集まること、安全な場所へ移動することを経験できるようにする。",
                ]
            ),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_staff_training",
            "職員研修・訓練",
            "\n".join(_training_lines(facility_profile)),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_parent_notice",
            "保護者への周知・連携",
            "\n".join(
                [
                    "入園時又は年度初めに、安全計画に基づく園の取組、避難訓練、引き渡し、緊急連絡方法を説明する。",
                    "園だより、掲示、保護者アプリ等で安全に関する取組を周知し、家庭でも交通安全や災害時の約束を確認してもらう。",
                    f"家庭との連携方針: {_profile_text(profile, 'family_collaboration_policy', '家庭と安全に関する情報を共有する。')}",
                ]
            ),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_incident_prevention",
            "事故・ヒヤリ・ハット再発防止",
            "\n".join(
                [
                    "ヒヤリ・ハットを日常的に収集し、月次会議等で要因分析と再発防止策を確認する。",
                    "事故が発生した場合は、原因、環境、職員配置、連絡体制を振り返り、必要に応じて点検項目やマニュアルに反映する。",
                    "反映した内容は職員に周知し、次回の研修・訓練又は見直しログに記録する。",
                ]
            ),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_review",
            "見直し・改訂",
            "\n".join(
                [
                    "年度内に少なくとも1回、実施状況、事故・ヒヤリ・ハット、職員体制、地域リスクの変化を踏まえて安全計画を見直す。",
                    "見直しの結果、変更がない場合も、検討日、参加者、判断理由を記録する。",
                    "変更した場合は改訂内容、周知日、次回確認予定を記録する。",
                ]
            ),
            source_refs,
            missing_inputs,
        ),
        _block(
            "safety_evidence",
            "証跡管理",
            "\n".join(
                [
                    "研修・訓練は、実施日、内容、参加対象、参加者、資料又は写真等の保管場所を記録する。",
                    "保護者周知は、周知日、方法、対象、掲示・配信・園だより等の控えを記録する。",
                    "見直しは、検討日、変更有無、改訂内容、議事メモを記録する。",
                    "証跡は年度単位で保管し、自治体確認時に提示できるよう整理する。",
                ]
            ),
            source_refs,
            missing_inputs,
        ),
    ]

    return SafetyPlanDraft(
        title=f"{school_year}年度 {facility_profile.compliance_standard_label}（{facility_profile.facility_name}）",
        status=SafetyPlanStatus.DRAFT,
        school_year=school_year,
        facility_profile=facility_profile,
        established_on=established_on,
        blocks=blocks,
        action_items=action_items,
        missing_inputs=missing_inputs,
    )


def evaluate_safety_compliance(
    *,
    compliance_standard: SafetyComplianceStandard,
    status: SafetyPlanStatus,
    established_on: date | None,
    section_keys: Iterable[str],
    logs: Iterable[tuple[SafetyLogType, date]],
    today: date,
) -> SafetyComplianceResult:
    missing_requirements = [key for key in REQUIRED_SECTION_KEYS if key not in set(section_keys)]
    axes = _evaluate_axes(
        compliance_standard=compliance_standard,
        established_on=established_on,
        logs=logs,
        today=today,
    )

    if status != SafetyPlanStatus.APPROVED or not established_on:
        return SafetyComplianceResult(
            status=SafetyRiskStatus.UNKNOWN,
            message="承認済みの策定日が未確定です。",
            axes=axes,
            missing_requirements=missing_requirements,
        )
    if missing_requirements:
        return SafetyComplianceResult(
            status=SafetyRiskStatus.HIGH_RISK,
            message="必須ブロックが不足しており、計画内容不足のリスクがあります。",
            axes=axes,
            missing_requirements=missing_requirements,
        )
    if not axes:
        return SafetyComplianceResult(
            status=SafetyRiskStatus.UNKNOWN,
            message="実施状況の判定軸がありません。",
            axes=[],
            missing_requirements=missing_requirements,
        )

    status_order = {
        SafetyRiskStatus.COMPLIANT: 0,
        SafetyRiskStatus.ATTENTION: 1,
        SafetyRiskStatus.WARNING: 2,
        SafetyRiskStatus.UNKNOWN: 3,
        SafetyRiskStatus.HIGH_RISK: 4,
    }
    worst_axis = max(axes, key=lambda item: status_order[item.status])
    if worst_axis.status == SafetyRiskStatus.UNKNOWN:
        message = "実施ログが不足しており、減算リスクを判定できません。"
    elif worst_axis.status == SafetyRiskStatus.HIGH_RISK:
        message = "1年未実施又は証跡不足の高リスク項目があります。"
    elif worst_axis.status == SafetyRiskStatus.WARNING:
        message = "期限が30日以内の要対応項目があります。"
    elif worst_axis.status == SafetyRiskStatus.ATTENTION:
        message = "期限が近づいている項目があります。"
    else:
        message = "必須計画と主要な実施ログは期限内です。"
    return SafetyComplianceResult(
        status=worst_axis.status,
        message=message,
        axes=axes,
        missing_requirements=missing_requirements,
    )


def _collect_missing_inputs(
    facility_profile: SafetyFacilityProfile,
    school_year: int,
    established_on: date | None,
) -> list[str]:
    fields = {
        "年度": str(school_year),
        "施設名": facility_profile.facility_name,
        "施設類型": facility_profile.facility_type.value,
        "自治体": facility_profile.municipality,
        "定員・年齢構成": facility_profile.capacity_summary or facility_profile.age_groups,
        "策定日": established_on.isoformat() if established_on else "",
    }
    return [label for label, value in fields.items() if not str(value).strip()]


def _confirmation_text(profile: NurseryProfile | None, missing_inputs: list[str]) -> str:
    if not missing_inputs:
        return ""
    marker = profile.confirmation_marker if profile else "要確認"
    policy = profile.missing_input_policy if profile else "未入力は確認してください。"
    return f"{marker}: {', '.join(missing_inputs)} が未入力または未確定です。{policy}"


def _with_confirmation(prefix: str, body: str) -> str:
    if not prefix:
        return body
    return f"{prefix}\n{body}"


def _source_refs(profile: NurseryProfile | None) -> list[SourceRef]:
    refs = [safety_official_source_ref(), SourceRef(kind="user_input", ref="input:safety-wizard", label="安全計画入力")]
    if profile:
        refs.insert(0, SourceRef(kind="nursery_profile", ref=f"profile:v{profile.version}", label=f"園プロファイル v{profile.version}"))
    return refs


def _block(
    section_key: str,
    title: str,
    body: str,
    source_refs: list[SourceRef],
    missing_inputs: list[str],
) -> SectionBlock:
    return SectionBlock(
        section_key=section_key,
        title=title,
        body=body,
        evidence_tags=safety_evidence_tags(),
        source_refs=list(source_refs),
        needs_confirmation=bool(missing_inputs),
        editor_note=_editor_note(missing_inputs),
    )


def _editor_note(missing_inputs: list[str]) -> str:
    if not missing_inputs:
        return "施設実態と年度予定に合わせて確認してください。"
    return f"未入力項目の確認後に見直してください: {', '.join(missing_inputs)}"


def _profile_text(profile: NurseryProfile | None, field_key: str, fallback: str) -> str:
    if not profile:
        return fallback
    value = profile.text_for(field_key).strip()
    return value or fallback


def _basis_text(facility_profile: SafetyFacilityProfile) -> str:
    if facility_profile.compliance_standard == SafetyComplianceStandard.SCHOOL_SAFETY:
        return "学校保健安全法第27条及び関連する基準"
    return "児童福祉施設の設備及び運営に関する基準第6条の3"


def _yes_no(value: bool) -> str:
    return "あり" if value else "なし"


def _manual_lines(facility_profile: SafetyFacilityProfile) -> list[str]:
    lines = [
        "通常保育時、午睡、食事、園外活動、災害、不審者侵入、火災・119番通報の役割分担を定め、常勤・非常勤を含む全職員に共有する。",
        "午睡時は観察、呼吸確認、寝具環境、職員配置を確認し、記録に残す。",
        "食事時は誤嚥・窒息・アレルギー対応、緊急時連絡、救急対応を確認する。",
    ]
    if facility_profile.has_pool:
        lines.append("プール・水遊び時は監視担当、人数確認、熱中症対策、事故発生時の役割を明確にする。")
    if facility_profile.has_outdoor_activity:
        lines.append("園外活動時は経路、危険箇所、引率体制、人数確認、緊急連絡先を事前に確認する。")
    if facility_profile.has_bus:
        lines.append("送迎バスでは乗降時点呼、車内確認、安全装置確認、見落とし防止手順を実施する。")
    if facility_profile.facility_type == FacilityType.HOME_VISIT:
        lines.append("居宅訪問型では訪問先の室内環境、避難経路、緊急連絡方法を訪問前に確認する。")
    return lines


def _training_lines(facility_profile: SafetyFacilityProfile) -> list[str]:
    lines = [
        "避難訓練、救急対応、心肺蘇生、AED、119番通報、不審者対応を年間計画に位置付け、実施日と参加者を記録する。",
        "非常勤職員、保育補助者、新規採用職員も受講対象に含め、未受講者を確認する。",
    ]
    if facility_profile.has_kitchen:
        lines.append("食事・アレルギー対応、誤嚥・窒息時対応を研修に含める。")
    if facility_profile.has_pool:
        lines.append("水遊び開始前に監視体制、救急対応、熱中症対策を確認する。")
    if facility_profile.has_bus:
        lines.append("送迎バスの点呼、車内確認、見落とし防止、安全装置確認を訓練に含める。")
    return lines


def _build_action_items(facility_profile: SafetyFacilityProfile) -> list[SafetyActionItem]:
    items = [
        SafetyActionItem("inspection", "年度初めの施設・園外環境安全点検", "4月", "施設長・主任", "年度初め及び必要時", SafetyLogType.SAFETY_INSPECTION),
        SafetyActionItem("notice", "安全計画の職員周知", "4月", "施設長", "年度初め・採用時", SafetyLogType.TRAINING_DRILL),
        SafetyActionItem("notice", "保護者への安全計画周知", "4月", "施設長・担任", "年度初め・入園時", SafetyLogType.PARENT_NOTICE),
        SafetyActionItem("drill", "不審者対応又は119番通報訓練", "5月", "主任", "年1回以上", SafetyLogType.TRAINING_DRILL),
        SafetyActionItem("drill", "防災・避難訓練", "9月", "施設長・主任", "年1回以上", SafetyLogType.TRAINING_DRILL),
        SafetyActionItem("review", "年度安全計画の見直し", "2月", "施設長・主任", "年1回以上", SafetyLogType.REVIEW),
    ]
    if facility_profile.has_pool:
        items.append(SafetyActionItem("drill", "水遊び・プール前安全確認", "6月", "主任", "水遊び開始前", SafetyLogType.TRAINING_DRILL))
    if facility_profile.has_bus:
        items.append(SafetyActionItem("drill", "送迎バス見落とし防止訓練", "4月", "送迎担当", "年度初め・採用時", SafetyLogType.TRAINING_DRILL))
    if facility_profile.compliance_standard == SafetyComplianceStandard.SCHOOL_SAFETY:
        return [
            SafetyActionItem(
                item.category,
                item.title,
                item.planned_month,
                item.responsible_role,
                item.recurrence,
                SafetyLogType.SCHOOL_SAFETY_ACTION,
            )
            for item in items
        ]
    return items


def _annual_schedule_text(action_items: list[SafetyActionItem]) -> str:
    lines = ["年間予定は次の通りとする。実施後は実施ログに日付、参加者、証跡を記録する。"]
    for item in action_items:
        lines.append(f"- {item.planned_month}: {item.title}（担当: {item.responsible_role} / 頻度: {item.recurrence}）")
    lines.append("- 随時: 新規採用職員研修、事故・ヒヤリ・ハット発生時の再発防止反映")
    return "\n".join(lines)


def _evaluate_axes(
    *,
    compliance_standard: SafetyComplianceStandard,
    established_on: date | None,
    logs: Iterable[tuple[SafetyLogType, date]],
    today: date,
) -> list[SafetyAxisStatus]:
    log_map: dict[SafetyLogType, date] = {}
    for log_type, implemented_on in logs:
        current = log_map.get(log_type)
        if current is None or implemented_on > current:
            log_map[log_type] = implemented_on

    if compliance_standard == SafetyComplianceStandard.SCHOOL_SAFETY:
        axis_types = [SafetyLogType.SCHOOL_SAFETY_ACTION]
    else:
        axis_types = [SafetyLogType.TRAINING_DRILL, SafetyLogType.PARENT_NOTICE, SafetyLogType.REVIEW]

    axes: list[SafetyAxisStatus] = []
    for log_type in axis_types:
        last_implemented_on = log_map.get(log_type)
        if last_implemented_on is None:
            next_due_on = add_one_year(established_on) if established_on else None
            days_until_due = (next_due_on - today).days if next_due_on else None
            if days_until_due is not None and days_until_due < 0:
                status = SafetyRiskStatus.HIGH_RISK
                message = "実施ログが未登録で、策定日から1年を超過しています。"
            else:
                status = SafetyRiskStatus.UNKNOWN
                message = "実施ログが未登録です。"
            axes.append(
                SafetyAxisStatus(
                    log_type=log_type,
                    label=SAFETY_LOG_TYPE_LABELS[log_type],
                    status=status,
                    last_implemented_on=None,
                    next_due_on=next_due_on,
                    days_until_due=days_until_due,
                    message=message,
                )
            )
            continue

        next_due_on = add_one_year(last_implemented_on)
        days_until_due = (next_due_on - today).days
        if days_until_due < 0:
            status = SafetyRiskStatus.HIGH_RISK
            message = "最終実施日から1年を超過しています。"
        elif days_until_due <= 30:
            status = SafetyRiskStatus.WARNING
            message = "期限まで30日以内です。"
        elif days_until_due <= 60:
            status = SafetyRiskStatus.ATTENTION
            message = "期限まで60日以内です。"
        else:
            status = SafetyRiskStatus.COMPLIANT
            message = "期限内です。"
        axes.append(
            SafetyAxisStatus(
                log_type=log_type,
                label=SAFETY_LOG_TYPE_LABELS[log_type],
                status=status,
                last_implemented_on=last_implemented_on,
                next_due_on=next_due_on,
                days_until_due=days_until_due,
                message=message,
            )
        )
    return axes


def add_one_year(value: date | None) -> date | None:
    if value is None:
        return None
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        return value.replace(year=value.year + 1, day=28)
