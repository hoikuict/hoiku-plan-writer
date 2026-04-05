from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ProfileFieldDefinition:
    key: str
    label: str
    section_key: str
    help_text: str
    example_text: str
    input_kind: str = "textarea"
    rows: int = 3
    always_enabled: bool = False
    default_enabled: bool = True


@dataclass(frozen=True, slots=True)
class ProfileFieldSection:
    key: str
    title: str
    description: str
    fields: tuple[ProfileFieldDefinition, ...]


PROFILE_FIELD_SECTIONS: tuple[ProfileFieldSection, ...] = (
    ProfileFieldSection(
        key="basic",
        title="基本情報",
        description="生成する文書の前提になる、園や対象年齢の基本情報です。",
        fields=(
            ProfileFieldDefinition(
                key="nursery_name",
                label="園名",
                section_key="basic",
                help_text="文書の見出しや根拠表示に使う正式な園名です。",
                example_text="みどりの風吹く保育園",
                input_kind="input",
                rows=1,
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="target_age_group",
                label="対象年齢",
                section_key="basic",
                help_text="主にこのアプリで扱う計画の対象年齢帯を記入します。",
                example_text="現在のところ３～５歳児を対象としています。０～２歳の個別の指導計画は作成中",
                input_kind="input",
                rows=1,
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="class_configuration",
                label="クラス編成",
                section_key="basic",
                help_text="クラス数や年齢混合の有無など、編成の特徴を書きます。",
                example_text="0歳1クラス、1歳1クラス、3〜5歳は異年齢1クラス",
                input_kind="input",
                rows=1,
                always_enabled=True,
            ),
        ),
    ),
    ProfileFieldSection(
        key="policy",
        title="保育の軸",
        description="園の理念や子ども観など、文章全体の判断軸になる内容です。",
        fields=(
            ProfileFieldDefinition(
                key="philosophy",
                label="理念",
                section_key="policy",
                help_text="園として大切にしている保育観や運営の基本姿勢を簡潔に書きます。",
                example_text="一人ひとりの思いを受け止め、安心の中で主体性が育つ保育を大切にする。",
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="childcare_goal",
                label="保育目標",
                section_key="policy",
                help_text="年間や月案に通底する、育てたい力や目標を書きます。",
                example_text="遊びや生活を通して、自分で考え、友だちと関わりながら表現する力を育む。",
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="desired_child_image",
                label="育てたい子ども像",
                section_key="policy",
                help_text="卒園時や年度末に目指す姿を、園らしい言葉で表します。",
                example_text="自分の思いを言葉や行動で表し、仲間と折り合いをつけながら遊びを進める子ども。",
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="child_view",
                label="子ども観",
                section_key="policy",
                help_text="子どもをどう捉えて関わるか、保育者の見方を書きます。",
                example_text="子どもは周囲との関わりの中で自ら学びを広げる存在として捉える。",
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="play_view",
                label="遊びの考え方",
                section_key="policy",
                help_text="遊びを学びや育ちとどう結びつけて考えるかを示します。",
                example_text="遊びは探究や対話の積み重ねであり、生活全体の学びにつながるものと考える。",
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="support_policy",
                label="援助方針",
                section_key="policy",
                help_text="保育者がどのような関わり方を基本にするかを書きます。",
                example_text="見守りを基調としつつ、必要な場面では言葉を添えて関係づくりを支える。",
                always_enabled=True,
            ),
        ),
    ),
    ProfileFieldSection(
        key="environment",
        title="環境と連携",
        description="園の特徴に応じて使う任意項目です。必要なものだけオンにできます。",
        fields=(
            ProfileFieldDefinition(
                key="indoor_environment",
                label="室内環境",
                section_key="environment",
                help_text="保育室のレイアウトや素材配置など、室内の環境構成を書きます。",
                example_text="子どもが自分で選べるよう、制作・ごっこ・絵本の場をゆるやかに分けて配置する。",
            ),
            ProfileFieldDefinition(
                key="outdoor_environment",
                label="戸外環境",
                section_key="environment",
                help_text="園庭や散歩先の活用方針など、戸外の環境づくりを書きます。",
                example_text="園庭では季節の変化に気づける自然物を取り入れ、散歩先の公園とつなげて遊びを広げる。",
            ),
            ProfileFieldDefinition(
                key="corner_play",
                label="コーナー保育",
                section_key="environment",
                help_text="継続的に置いているコーナーやそのねらいを書きます。",
                example_text="制作コーナーとごっこ遊びコーナーを常設し、子どもの発想に応じて素材を入れ替える。",
            ),
            ProfileFieldDefinition(
                key="community_resources",
                label="地域資源",
                section_key="environment",
                help_text="近隣施設や自然環境など、保育に活かす地域資源を書きます。",
                example_text="近隣の公園、図書館、商店街、畑を活動内容に応じて取り入れる。",
            ),
            ProfileFieldDefinition(
                key="family_collaboration_policy",
                label="家庭連携方針",
                section_key="environment",
                help_text="家庭との共有の仕方や連携で大切にしていることを書きます。",
                example_text="日々の姿を具体的に伝え、家庭での様子も受け取りながら育ちを一緒に見ていく。",
            ),
            ProfileFieldDefinition(
                key="local_collaboration_policy",
                label="地域との関わり",
                section_key="environment",
                help_text="地域との交流や外部とのつながり方針を書きます。",
                example_text="地域行事や公共施設との関わりを通して、子どもが地域に親しめる機会をつくる。",
            ),
            ProfileFieldDefinition(
                key="health_and_safety_policy",
                label="健康・安全方針",
                section_key="environment",
                help_text="安全配慮や健康管理で特に大切にしていることを書きます。",
                example_text="見通しを持って行動できる流れを整え、危険箇所や体調変化を日常的に確認する。",
            ),
            ProfileFieldDefinition(
                key="inclusive_policy",
                label="インクルーシブ方針",
                section_key="environment",
                help_text="多様な子ども同士が育ち合うための考え方を書きます。",
                example_text="違いを自然に受け止め合える関係づくりを大切にし、一人ひとりに応じた参加の形を支える。",
            ),
        ),
    ),
    ProfileFieldSection(
        key="writing_style",
        title="文体ルール",
        description="AI が出力する文体や注意表現を整える任意項目です。",
        fields=(
            ProfileFieldDefinition(
                key="preferred_expressions",
                label="よく使う表現",
                section_key="writing_style",
                help_text="園として使いたい言い回しやキーワードを書きます。",
                example_text="自ら気づく、確かめ合う、安心して表す",
            ),
            ProfileFieldDefinition(
                key="avoid_expressions",
                label="避けたい表現",
                section_key="writing_style",
                help_text="園として避けたい言い回しや強すぎる表現を書きます。",
                example_text="一律にさせる、できていないから促す",
            ),
            ProfileFieldDefinition(
                key="sentence_tone",
                label="文末トーン",
                section_key="writing_style",
                help_text="文章全体のトーンを短く指定します。",
                example_text="やわらかく丁寧、断定しすぎない",
                input_kind="input",
                rows=1,
            ),
            ProfileFieldDefinition(
                key="missing_input_policy",
                label="未入力時の扱い",
                section_key="writing_style",
                help_text="不足情報があるときに、生成文でどう扱うかを決めます。",
                example_text="未入力は要確認として扱い、断定表現を避ける。",
                input_kind="input",
                rows=1,
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="confirmation_marker",
                label="要確認表示",
                section_key="writing_style",
                help_text="未確定箇所に付ける短いラベルです。",
                example_text="要確認",
                input_kind="input",
                rows=1,
                always_enabled=True,
            ),
            ProfileFieldDefinition(
                key="evidence_tag_policy",
                label="根拠タグ表示方針",
                section_key="writing_style",
                help_text="根拠タグをどう扱うかのルールを書きます。",
                example_text="根拠タグを表示し、確認時に参照できるようにする。",
                input_kind="input",
                rows=1,
                always_enabled=True,
            ),
        ),
    ),
)

PROFILE_FIELD_MAP: dict[str, ProfileFieldDefinition] = {
    field.key: field
    for section in PROFILE_FIELD_SECTIONS
    for field in section.fields
}

PROFILE_ALWAYS_ENABLED_KEYS: tuple[str, ...] = tuple(
    field.key for field in PROFILE_FIELD_MAP.values() if field.always_enabled
)

PROFILE_DEFAULT_ENABLED_KEYS: tuple[str, ...] = tuple(
    field.key
    for field in PROFILE_FIELD_MAP.values()
    if field.always_enabled or field.default_enabled
)


def normalize_enabled_field_keys(field_keys: Iterable[str] | None) -> tuple[str, ...]:
    requested = set(field_keys or ())
    normalized: list[str] = []
    for field in PROFILE_FIELD_MAP.values():
        if field.always_enabled or field.key in requested:
            normalized.append(field.key)
    return tuple(normalized)
