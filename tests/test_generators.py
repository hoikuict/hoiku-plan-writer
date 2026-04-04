import unittest

from hoiku_plan_writer.sample_data import (
    sample_annual_input,
    sample_monthly_input,
    sample_profile,
)
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

    def test_generate_annual_plan_marks_missing_required_inputs(self) -> None:
        profile = sample_profile()
        plan_input = sample_annual_input()
        plan_input.focus_growth = ""

        annual_plan = generate_annual_plan(profile, plan_input)

        self.assertIn("今年特に大切にしたい育ち", annual_plan.missing_inputs)
        self.assertTrue(all(block.needs_confirmation for block in annual_plan.blocks))
        self.assertTrue(all("要確認" in block.body for block in annual_plan.blocks))

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
