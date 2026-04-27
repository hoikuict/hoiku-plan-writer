import html
import os
import re
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from hoiku_plan_writer.ai.service import AnnualPlanPreviewService
from hoiku_plan_writer.config import Settings
from hoiku_plan_writer.domain.models import GeneratedPlan, SectionBlock
from hoiku_plan_writer.main import create_app
from hoiku_plan_writer.sample_data import sample_annual_input, sample_profile
from hoiku_plan_writer.services.generators import generate_annual_plan


class FakeAnnualPreviewProvider:
    provider_name = "fake-llm"
    model_name = "fake-model"

    def generate_annual_plan_preview(self, *, profile, plan_input, fallback_plan, model_name=None):
        return _plan_with_marker(fallback_plan, section_key="annual_goal", marker="LLM-ANNUAL-MARKER")

    def generate_monthly_plan_preview(self, *, profile, annual_plan, plan_input, fallback_plan, model_name=None):
        return _plan_with_marker(fallback_plan, section_key="monthly_goal", marker="LLM-MONTHLY-MARKER")

    def list_model_names(self):
        return ["fake-model", "fake-bigger-model"]


class AnnualPlanPreviewServiceTests(unittest.TestCase):
    def test_enabled_service_uses_provider_output(self) -> None:
        service = AnnualPlanPreviewService(
            provider=FakeAnnualPreviewProvider(),
            annual_preview_enabled=True,
        )

        result = service.preview(profile=sample_profile(), plan_input=sample_annual_input())

        self.assertTrue(result.is_llm)
        self.assertIn("LLM-ANNUAL-MARKER", result.plan.blocks[0].body)

    def test_monthly_preview_uses_provider_output(self) -> None:
        profile = sample_profile()
        annual_plan = generate_annual_plan(profile, sample_annual_input())
        service = AnnualPlanPreviewService(
            provider=FakeAnnualPreviewProvider(),
            monthly_preview_enabled=True,
        )

        result = service.preview_monthly(
            profile=profile,
            annual_plan=annual_plan,
            plan_input=_monthly_domain_input(),
        )

        self.assertTrue(result.is_llm)
        self.assertIn("LLM-MONTHLY-MARKER", result.plan.blocks[0].body)


class AnnualPlanPreviewWebTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, db_path = tempfile.mkstemp(dir=Path.cwd(), prefix="hoiku-plan-ai-test-", suffix=".db")
        os.close(fd)
        self.db_path = Path(db_path)
        settings = Settings(database_url=f"sqlite:///./{self.db_path.name}")
        preview_service = AnnualPlanPreviewService(
            provider=FakeAnnualPreviewProvider(),
            annual_preview_enabled=True,
            monthly_preview_enabled=True,
        )
        self.app = create_app(settings, annual_preview_service=preview_service)
        self.client_cm = TestClient(self.app)
        self.client = self.client_cm.__enter__()

    def tearDown(self) -> None:
        self.client_cm.__exit__(None, None, None)
        self.app.state.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()

    def test_annual_and_monthly_forms_show_llm_toggle(self) -> None:
        self._login_as_admin()

        annual_response = self.client.get("/annual-plans/new")
        monthly_response = self.client.get("/monthly-plans/new")

        self.assertEqual(annual_response.status_code, 200)
        self.assertEqual(monthly_response.status_code, 200)
        self.assertIn('name="use_llm_preview"', annual_response.text)
        self.assertIn('name="use_llm_preview"', monthly_response.text)
        self.assertIn('name="ai_model"', annual_response.text)
        self.assertIn('name="ai_model"', monthly_response.text)
        self.assertIn("fake-bigger-model", annual_response.text)
        self.assertIn("fake-bigger-model", monthly_response.text)
        self.assertIn("fake-llm / fake-model", annual_response.text)
        self.assertIn("fake-llm / fake-model", monthly_response.text)

    def test_annual_preview_can_be_adopted_on_save(self) -> None:
        self._login_as_admin()
        self._activate_profile()

        preview = self.client.post(
            "/annual-plans/preview",
            data={**self._annual_plan_payload(), "use_llm_preview": "on"},
        )

        self.assertEqual(preview.status_code, 200)
        self.assertIn("LLM-ANNUAL-MARKER", preview.text)
        preview_plan_json = _extract_preview_plan_json(preview.text)

        create_response = self.client.post(
            "/annual-plans/",
            data={
                **self._annual_plan_payload(),
                "action": "adopt_preview",
                "preview_plan_json": preview_plan_json,
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 303)

        detail = self.client.get("/documents/1")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("LLM-ANNUAL-MARKER", detail.text)

    def test_rule_based_save_still_available_after_preview(self) -> None:
        self._login_as_admin()
        self._activate_profile()

        self.client.post(
            "/annual-plans/preview",
            data={**self._annual_plan_payload(), "use_llm_preview": "on"},
        )
        create_response = self.client.post(
            "/annual-plans/",
            data={**self._annual_plan_payload(), "action": "save_rule_based"},
            follow_redirects=False,
        )

        self.assertEqual(create_response.status_code, 303)
        detail = self.client.get("/documents/1")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("LLM-ANNUAL-MARKER", detail.text)

    def test_monthly_preview_uses_ai_service_and_can_be_adopted(self) -> None:
        self._login_as_admin()
        self._activate_profile()
        self._create_annual_document()

        preview = self.client.post(
            "/monthly-plans/preview",
            data={**self._monthly_plan_payload(), "use_llm_preview": "on"},
        )

        self.assertEqual(preview.status_code, 200)
        self.assertIn("LLM-MONTHLY-MARKER", preview.text)
        preview_plan_json = _extract_preview_plan_json(preview.text)

        create_response = self.client.post(
            "/monthly-plans/",
            data={
                **self._monthly_plan_payload(),
                "action": "adopt_preview",
                "preview_plan_json": preview_plan_json,
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 303)

        detail = self.client.get("/documents/2")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("LLM-MONTHLY-MARKER", detail.text)

    def _login_as_admin(self) -> None:
        response = self.client.post(
            "/staff/login",
            data={
                "role": "admin",
                "actor_ref": "staff:test-admin",
                "nursery_ref": "nursery:test",
                "classroom_refs_raw": "classroom:5yo-a",
                "name": "テスト管理者",
                "redirect_to": "/documents/",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def _activate_profile(self) -> None:
        response = self.client.post(
            "/nursery-profile/",
            data={**_profile_payload(), "action": "activate"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def _create_annual_document(self) -> None:
        response = self.client.post(
            "/annual-plans/",
            data=self._annual_plan_payload(),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/documents/1")

    @staticmethod
    def _annual_plan_payload() -> dict[str, str]:
        return {
            "classroom_ref": "classroom:5yo-a",
            "school_year": "2026",
            "class_name": "5歳児",
            "age_group": "5歳児",
            "class_outlook": "友だちと相談しながら遊びを進めたい。",
            "focus_growth": "協力しながら主体的に活動をつくる力。",
            "annual_events": "運動会、発表会",
            "seasonal_context": "春夏秋冬の変化",
            "community_resources": "公園、図書館",
            "care_points": "安全と対話の両立",
            "handover_notes": "前年度から話し合いへの関心が高い。",
        }

    @staticmethod
    def _monthly_plan_payload() -> dict[str, str]:
        return {
            "classroom_ref": "classroom:5yo-a",
            "target_month": "2026-05",
            "class_name": "5歳児",
            "owner_name": "テスト管理者",
            "related_annual_plan_id_raw": "1",
            "related_term_key": "term_1",
            "previous_reflection": "新年度に慣れてきた。",
            "current_children_snapshot": "友だちとのやり取りが増えている。",
            "play_interests": "ごっこ遊び、制作",
            "seasonal_context": "春から初夏への変化",
            "family_context": "家庭でも友だちの話題が増えた。",
            "class_notes": "安心して発言できる話し合いを意識する。",
        }


def _plan_with_marker(fallback_plan: GeneratedPlan, *, section_key: str, marker: str) -> GeneratedPlan:
    blocks: list[SectionBlock] = []
    for block in fallback_plan.blocks:
        body = block.body
        if block.section_key == section_key:
            body = f"{marker}\n{body}"
        blocks.append(
            SectionBlock(
                section_key=block.section_key,
                title=block.title,
                body=body,
                evidence_tags=list(block.evidence_tags),
                source_refs=list(block.source_refs),
                needs_confirmation=block.needs_confirmation,
                editor_note=block.editor_note,
            )
        )
    return GeneratedPlan(
        document_type=fallback_plan.document_type,
        title=f"{marker} preview",
        status=fallback_plan.status,
        blocks=blocks,
        missing_inputs=list(fallback_plan.missing_inputs),
    )


def _profile_payload() -> dict[str, str]:
    return {
        "nursery_name": "テスト保育園",
        "target_age_group": "3〜5歳児",
        "class_configuration": "年長1クラス",
        "local_context": "住宅地にあり、公園と図書館が近い。",
        "philosophy": "子どもの主体性を大切にする。",
        "childcare_goal": "遊びを通して考える力を育む。",
        "desired_child_image": "友だちと協力して遊びを進める子ども。",
        "child_view": "一人ひとりの思いを尊重する。",
        "play_view": "探究が続く遊びを支える。",
        "support_policy": "見守りを基調に必要な援助を行う。",
        "curriculum_focus": "全体的な計画の重点と年間の育ちをつなげる。",
        "assessment_policy": "子どもの選択と友だちとの相談を振り返りの観点にする。",
        "indoor_environment": "落ち着いて選べる室内環境を整える。",
        "outdoor_environment": "季節を感じられる園庭活動を取り入れる。",
        "family_collaboration_policy": "家庭と日々の姿を共有する。",
        "health_and_safety_policy": "安心安全を日常的に確認する。",
        "inclusive_policy": "違いを受け止め合える集団づくりを行う。",
        "sentence_tone": "やわらかく丁寧",
        "document_format_notes": "一文を短めにする。",
    }


def _monthly_domain_input():
    from hoiku_plan_writer.domain.models import MonthlyPlanInput

    return MonthlyPlanInput(
        target_month="2026-05",
        class_name="5歳児",
        owner_name="テスト管理者",
        related_term_key="term_1",
        previous_reflection="新年度に慣れてきた。",
        current_children_snapshot="友だちとのやり取りが増えている。",
        play_interests="ごっこ遊び、制作",
        seasonal_context="春から初夏への変化",
        family_context="家庭でも友だちの話題が増えた。",
        class_notes="安心して発言できる話し合いを意識する。",
    )


def _extract_preview_plan_json(text: str) -> str:
    match = re.search(r'<textarea name="preview_plan_json" class="hidden">(.*?)</textarea>', text, re.S)
    if not match:
        raise AssertionError("preview_plan_json textarea was not rendered")
    return html.unescape(match.group(1))


if __name__ == "__main__":
    unittest.main()
