from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SectionDefinition:
    key: str
    title: str
    purpose: str


ANNUAL_TERM_ORDER: tuple[tuple[str, str], ...] = (
    ("term_1", "4〜6月"),
    ("term_2", "7〜9月"),
    ("term_3", "10〜12月"),
    ("term_4", "1〜3月"),
)

ANNUAL_BASE_SECTIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition("annual_goal", "年間の大きなねらい", "年間全体の軸"),
)

ANNUAL_TERM_SECTION_SUFFIXES: tuple[tuple[str, str, str], ...] = (
    ("outlook", "見通し", "各期の見通し"),
    ("environment", "環境構成", "各期の環境構成"),
    ("support", "援助", "各期の援助方針"),
    ("family_collaboration", "家庭連携", "各期の家庭との連携"),
    ("reflection_viewpoint", "振り返り観点", "各期の確認観点"),
)

MONTHLY_SECTIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition("monthly_goal", "今月のねらい", "月案の中心目標"),
    SectionDefinition("children_snapshot", "子どもの姿の捉え", "現在の姿の整理"),
    SectionDefinition("monthly_environment", "環境構成", "月の環境構成"),
    SectionDefinition("monthly_support", "援助", "月の援助方針"),
    SectionDefinition("monthly_family_collaboration", "家庭連携", "保護者との連携方針"),
    SectionDefinition("monthly_reflection_viewpoint", "月末の振り返り観点", "次月につなぐ確認観点"),
)


def annual_section_definitions() -> list[SectionDefinition]:
    definitions = list(ANNUAL_BASE_SECTIONS)
    for term_key, term_label in ANNUAL_TERM_ORDER:
        for suffix, short_title, purpose in ANNUAL_TERM_SECTION_SUFFIXES:
            definitions.append(
                SectionDefinition(
                    key=f"{term_key}_{suffix}",
                    title=f"{term_label}の{short_title}",
                    purpose=purpose,
                )
            )
    return definitions
