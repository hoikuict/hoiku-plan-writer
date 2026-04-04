from __future__ import annotations

import argparse
import json
from typing import Sequence

from .sample_data import sample_annual_input, sample_monthly_input, sample_profile
from .services.generators import generate_annual_plan, generate_monthly_plan
from .services.serializers import plan_to_dict, section_keys_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hoiku-plan",
        description="保育計画文書作成アプリのサンプルCLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("demo-annual", help="年間指導計画のサンプルを出力する")
    subparsers.add_parser("demo-monthly", help="月案のサンプルを出力する")
    subparsers.add_parser("section-keys", help="セクションキー一覧を出力する")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo-annual":
        profile = sample_profile()
        annual_plan = generate_annual_plan(profile, sample_annual_input())
        print(json.dumps(plan_to_dict(annual_plan), ensure_ascii=False, indent=2))
        return

    if args.command == "demo-monthly":
        profile = sample_profile()
        annual_plan = generate_annual_plan(profile, sample_annual_input())
        monthly_plan = generate_monthly_plan(
            profile=profile,
            annual_plan=annual_plan,
            plan_input=sample_monthly_input(),
        )
        print(json.dumps(plan_to_dict(monthly_plan), ensure_ascii=False, indent=2))
        return

    if args.command == "section-keys":
        print(json.dumps(section_keys_to_dict(), ensure_ascii=False, indent=2))
        return

    parser.error("unknown command")
