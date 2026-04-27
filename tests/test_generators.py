import unittest

from hoiku_plan_writer.sample_data import (
    sample_annual_input,
    sample_monthly_input,
    sample_profile,
)
from hoiku_plan_writer.domain.profile_fields import review_profile_completeness
from hoiku_plan_writer.services.generators import generate_annual_plan, generate_monthly_plan


class GeneratorTests(unittest.TestCase):
    def test_generate_annual_plan_creates_four_terms(self) -> None:
        annual_plan = generate_annual_plan(sample_profile(), sample_annual_input())

        term_outlook_keys = {
            block.section_key
            for block in annual_plan.blocks
            if block.section_key.endswith("_outlook")
        }

        self.assertEqual(len(annual_plan.blocks), 21)
        self.assertSetEqual(
            term_outlook_keys,
            {
                "term_1_outlook",
                "term_2_outlook",
                "term_3_outlook",
                "term_4_outlook",
            },
        )
        self.assertTrue(all(block.evidence_tags for block in annual_plan.blocks))
        self.assertEqual(annual_plan.missing_inputs, [])

    def test_profile_review_reports_required_recommended_and_privacy_warnings(self) -> None:
        profile = sample_profile()
        profile.philosophy = ""
        profile.document_format_notes = ""
        profile.local_context = "山田さんの自宅近くの公園を使う。"

        review = review_profile_completeness(profile)

        self.assertFalse(review.can_activate)
        self.assertIn("理念", [issue.label for issue in review.missing_required])
        self.assertIn("文書書式メモ", [issue.label for issue in review.missing_recommended])
        self.assertIn("地域特性", [issue.label for issue in review.privacy_warnings])

    def test_generate_annual_plan_uses_profile_v2_fields(self) -> None:
        annual_plan = generate_annual_plan(sample_profile(), sample_annual_input())
        annual_goal = next(block for block in annual_plan.blocks if block.section_key == "annual_goal")
        reflection = next(
            block for block in annual_plan.blocks if block.section_key == "term_1_reflection_viewpoint"
        )

        self.assertIn("全体的な計画との接続", annual_goal.body)
        self.assertIn("書式は", annual_goal.body)
        self.assertIn("振り返りの観点", reflection.body)

    def test_generate_annual_plan_marks_missing_required_inputs(self) -> None:
        profile = sample_profile()
        plan_input = sample_annual_input()
        plan_input.focus_growth = ""

        annual_plan = generate_annual_plan(profile, plan_input)

        self.assertIn("今年特に大切にしたい育ち", annual_plan.missing_inputs)
        self.assertTrue(all(block.needs_confirmation for block in annual_plan.blocks))
        self.assertTrue(all("要確認" in block.body for block in annual_plan.blocks))

    def test_generate_annual_plan_ignores_disabled_optional_profile_fields(self) -> None:
        profile = sample_profile()
        profile.indoor_environment = "使わない室内環境の説明"
        profile.enabled_field_keys = tuple(
            key for key in profile.enabled_field_keys if key != "indoor_environment"
        )

        annual_plan = generate_annual_plan(profile, sample_annual_input())
        term_environment = next(
            block for block in annual_plan.blocks if block.section_key == "term_1_environment"
        )

        self.assertIn("落ち着いて選べる環境", term_environment.body)
        self.assertNotIn("使わない室内環境の説明", term_environment.body)

    def test_generate_monthly_plan_uses_annual_context(self) -> None:
        profile = sample_profile()
        annual_plan = generate_annual_plan(profile, sample_annual_input())

        monthly_plan = generate_monthly_plan(profile, annual_plan, sample_monthly_input())
        monthly_goal = next(
            block for block in monthly_plan.blocks if block.section_key == "monthly_goal"
        )

        self.assertIn("年間計画の関連文脈", monthly_goal.body)
        self.assertIn("前月の反省", monthly_goal.body)
        self.assertEqual(monthly_plan.missing_inputs, [])

    def test_generate_monthly_plan_marks_missing_related_term(self) -> None:
        profile = sample_profile()
        annual_plan = generate_annual_plan(profile, sample_annual_input())
        plan_input = sample_monthly_input()
        plan_input.related_term_key = "term_99"

        monthly_plan = generate_monthly_plan(profile, annual_plan, plan_input)

        self.assertIn("年間計画の関連文脈", monthly_plan.missing_inputs)
        self.assertTrue(all(block.needs_confirmation for block in monthly_plan.blocks))


if __name__ == "__main__":
    unittest.main()
