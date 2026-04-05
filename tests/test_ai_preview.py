import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from hoiku_plan_writer.ai.prompts import build_annual_plan_block_messages
from hoiku_plan_writer.ai.providers.ollama_chat import OllamaChatProvider
from hoiku_plan_writer.ai.service import AnnualPlanPreviewService, build_annual_preview_service
from hoiku_plan_writer.config import Settings
from hoiku_plan_writer.domain.models import GeneratedPlan, SectionBlock
from hoiku_plan_writer.domain.profile_fields import PROFILE_DEFAULT_ENABLED_KEYS
from hoiku_plan_writer.main import create_app
from hoiku_plan_writer.sample_data import sample_annual_input, sample_profile
from hoiku_plan_writer.services.generators import generate_annual_plan


class FakeAnnualPreviewProvider:
    provider_name = "fake-llm"
    model_name = "fake-model"

    def generate_annual_plan_preview(self, *, profile, plan_input, fallback_plan):
        blocks: list[SectionBlock] = []
        for block in fallback_plan.blocks:
            body = block.body
            if block.section_key == "annual_goal":
                body = f"LLM-PREVIEW-MARKER\n{body}"
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
            title="LLM preview annual plan",
            status=fallback_plan.status,
            blocks=blocks,
            missing_inputs=list(fallback_plan.missing_inputs),
        )


class FailingAnnualPreviewProvider:
    provider_name = "fake-llm"
    model_name = "fake-model"

    def generate_annual_plan_preview(self, *, profile, plan_input, fallback_plan):
        raise RuntimeError("boom")


class AnnualPlanPromptTests(unittest.TestCase):
    def test_block_prompt_moves_short_inputs_into_weak_hints(self) -> None:
        profile = sample_profile()
        profile.childcare_goal = "考えて遊べる子ども"
        profile.desired_child_image = "かっこいいこども"
        plan_input = sample_annual_input()
        plan_input.class_outlook = "がんばる"
        plan_input.focus_growth = "こころ"
        plan_input.annual_events = "おすもう"
        fallback_plan = generate_annual_plan(profile, plan_input)

        messages = build_annual_plan_block_messages(
            profile=profile,
            plan_input=plan_input,
            fallback_plan=fallback_plan,
            fallback_block=fallback_plan.blocks[0],
        )
        payload = json.loads(messages[1]["content"])

        self.assertNotIn("childcare_goal", payload["nursery_profile"])
        self.assertNotIn("desired_child_image", payload["nursery_profile"])
        self.assertNotIn("class_outlook", payload["plan_input"])
        self.assertNotIn("focus_growth", payload["plan_input"])

        weak_fields = {item["field"] for item in payload["weak_input_hints"]}
        self.assertIn("childcare_goal", weak_fields)
        self.assertIn("desired_child_image", weak_fields)
        self.assertIn("class_outlook", weak_fields)
        self.assertIn("focus_growth", weak_fields)
        self.assertIn("baseline_note", payload["block"])
        self.assertNotIn("baseline_body", payload["block"])

    def test_block_prompt_includes_section_specific_guidance(self) -> None:
        profile = sample_profile()
        plan_input = sample_annual_input()
        fallback_plan = generate_annual_plan(profile, plan_input)
        support_block = next(block for block in fallback_plan.blocks if block.section_key == "term_1_support")

        messages = build_annual_plan_block_messages(
            profile=profile,
            plan_input=plan_input,
            fallback_plan=fallback_plan,
            fallback_block=support_block,
        )
        payload = json.loads(messages[1]["content"])
        guidance = payload["block"]["section_guidance"]

        self.assertEqual(guidance["section_kind"], "support")
        self.assertIn("具体的な保育者の援助行為", " ".join(guidance["must_include"]))
        self.assertIn("短い語句をそのまま", " ".join(guidance["avoid"]))
        self.assertIn("care_points", payload["plan_input"])


class AnnualPlanPreviewServiceTests(unittest.TestCase):
    def test_disabled_service_returns_rule_based_plan(self) -> None:
        service = AnnualPlanPreviewService(annual_preview_enabled=False)

        result = service.preview(profile=sample_profile(), plan_input=sample_annual_input())

        self.assertEqual(result.generation_mode, "fallback")
        self.assertIn("generator", result.note)
        self.assertEqual(result.plan.blocks[0].section_key, "annual_goal")

    def test_enabled_service_uses_provider_output(self) -> None:
        service = AnnualPlanPreviewService(
            provider=FakeAnnualPreviewProvider(),
            annual_preview_enabled=True,
        )

        result = service.preview(profile=sample_profile(), plan_input=sample_annual_input())

        self.assertTrue(result.is_llm)
        self.assertEqual(result.plan.title, "LLM preview annual plan")
        self.assertIn("LLM-PREVIEW-MARKER", result.plan.blocks[0].body)
        self.assertIn("fake-llm / fake-model", result.note)

    def test_enabled_service_can_be_turned_off_per_request(self) -> None:
        service = AnnualPlanPreviewService(
            provider=FakeAnnualPreviewProvider(),
            annual_preview_enabled=True,
        )

        result = service.preview(
            profile=sample_profile(),
            plan_input=sample_annual_input(),
            use_llm=False,
        )

        self.assertEqual(result.generation_mode, "fallback")
        self.assertIn("generator", result.note)
        self.assertNotIn("LLM-PREVIEW-MARKER", result.plan.blocks[0].body)

    def test_provider_failure_falls_back_to_rule_based_plan(self) -> None:
        service = AnnualPlanPreviewService(
            provider=FailingAnnualPreviewProvider(),
            annual_preview_enabled=True,
        )

        result = service.preview(profile=sample_profile(), plan_input=sample_annual_input())

        self.assertEqual(result.generation_mode, "fallback")
        self.assertIn("generator", result.note)
        self.assertNotIn("LLM-PREVIEW-MARKER", result.plan.blocks[0].body)

    def test_build_service_uses_ollama_default_model(self) -> None:
        service = build_annual_preview_service(
            Settings(
                ai_provider="ollama",
                ai_enable_annual_preview=True,
            )
        )

        self.assertTrue(service.can_use_llm)
        self.assertIsInstance(service.provider, OllamaChatProvider)
        assert service.provider is not None
        self.assertEqual(service.provider.model_name, "qwen2.5:0.5b")
        self.assertEqual(service.provider.base_url, "http://127.0.0.1:11434")


class AnnualPlanPreviewWebIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, db_path = tempfile.mkstemp(dir=Path.cwd(), prefix="hoiku-plan-ai-test-", suffix=".db")
        os.close(fd)
        self.db_path = Path(db_path)
        settings = Settings(database_url=f"sqlite:///./{self.db_path.name}")
        preview_service = AnnualPlanPreviewService(
            provider=FakeAnnualPreviewProvider(),
            annual_preview_enabled=True,
        )
        self.app = create_app(settings, annual_preview_service=preview_service)
        self.client_cm = TestClient(self.app)
        self.client = self.client_cm.__enter__()

    def tearDown(self) -> None:
        self.client_cm.__exit__(None, None, None)
        self.app.state.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()

    def test_annual_form_shows_llm_toggle(self) -> None:
        self._login_as_admin()

        response = self.client.get("/annual-plans/new")

        self.assertEqual(response.status_code, 200)
        self.assertIn("name=\"use_llm_preview\"", response.text)
        self.assertIn("fake-llm / fake-model", response.text)

    def test_annual_preview_uses_ai_service_but_save_keeps_rule_based_generator(self) -> None:
        self._login_as_admin()
        self._activate_profile()

        preview = self.client.post(
            "/annual-plans/preview",
            data={**self._annual_plan_payload(), "use_llm_preview": "on"},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertIn("LLM-PREVIEW-MARKER", preview.text)
        self.assertIn("fake-llm / fake-model", preview.text)

        create_response = self.client.post(
            "/annual-plans/",
            data=self._annual_plan_payload(),
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 303)
        self.assertEqual(create_response.headers["location"], "/documents/1")

        detail = self.client.get("/documents/1")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("LLM-PREVIEW-MARKER", detail.text)

    def test_annual_preview_can_be_switched_off(self) -> None:
        self._login_as_admin()
        self._activate_profile()

        preview = self.client.post(
            "/annual-plans/preview",
            data=self._annual_plan_payload(),
        )
        self.assertEqual(preview.status_code, 200)
        self.assertNotIn("LLM-PREVIEW-MARKER", preview.text)
        self.assertIn("generator", preview.text)

    def test_annual_preview_without_htmx_returns_full_form_page(self) -> None:
        self._login_as_admin()
        self._activate_profile()

        preview = self.client.post(
            "/annual-plans/preview",
            data={**self._annual_plan_payload(), "use_llm_preview": "on"},
        )

        self.assertEqual(preview.status_code, 200)
        self.assertIn('id="annual-plan-form"', preview.text)
        self.assertIn("LLM-PREVIEW-MARKER", preview.text)

    def test_annual_preview_with_htmx_returns_preview_partial(self) -> None:
        self._login_as_admin()
        self._activate_profile()

        preview = self.client.post(
            "/annual-plans/preview",
            data={**self._annual_plan_payload(), "use_llm_preview": "on"},
            headers={"HX-Request": "true"},
        )

        self.assertEqual(preview.status_code, 200)
        self.assertNotIn('id="annual-plan-form"', preview.text)
        self.assertIn("LLM-PREVIEW-MARKER", preview.text)

    def test_monthly_preview_without_htmx_returns_full_form_page(self) -> None:
        self._login_as_admin()
        self._activate_profile()
        self._create_annual_plan()

        preview = self.client.post(
            "/monthly-plans/preview",
            data=self._monthly_plan_payload(),
        )

        self.assertEqual(preview.status_code, 200)
        self.assertIn('id="monthly-plan-form"', preview.text)
        self.assertIn("今月のねらい", preview.text)

    def _login_as_admin(self) -> None:
        response = self.client.post(
            "/staff/login",
            data={
                "role": "admin",
                "actor_ref": "staff:test-admin",
                "nursery_ref": "nursery:test",
                "classroom_refs_raw": "classroom:5yo-a",
                "name": "Test Admin",
                "redirect_to": "/documents/",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def _activate_profile(self) -> None:
        payload = {
            "nursery_name": "Test Nursery",
            "target_age_group": "3-5",
            "class_configuration": "One mixed-age class",
            "philosophy": "We protect curiosity and dialogue.",
            "childcare_goal": "Children grow through play and conversation.",
            "desired_child_image": "Children who can express ideas and collaborate.",
            "child_view": "Each child learns in relationship with others.",
            "play_view": "Play is a path for inquiry and meaning-making.",
            "support_policy": "Adults observe first and support when needed.",
            "indoor_environment": "Children can choose materials and spaces on their own.",
            "outdoor_environment": "Outdoor play connects with seasons and nature.",
            "corner_play": "Art and pretend-play corners stay available over time.",
            "community_resources": "Parks and the local library are part of the curriculum.",
            "family_collaboration_policy": "We share daily growth with families in both directions.",
            "local_collaboration_policy": "Children build familiarity with the local community.",
            "health_and_safety_policy": "Safety checks and predictable routines are part of each day.",
            "inclusive_policy": "Different ways of participating are welcomed and supported.",
            "preferred_expressions": "notice, confirm together, express safely",
            "avoid_expressions": "force everyone, push because not enough",
            "sentence_tone": "gentle and clear",
            "missing_input_policy": "Missing information must stay flagged for review.",
            "confirmation_marker": "Needs Review",
            "evidence_tag_policy": "Evidence tags stay visible for review.",
            "enabled_field_keys": list(PROFILE_DEFAULT_ENABLED_KEYS),
            "action": "activate",
        }
        response = self.client.post(
            "/nursery-profile/",
            data=payload,
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def _create_annual_plan(self) -> None:
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
            "class_name": "Five",
            "age_group": "5-year-olds",
            "class_outlook": "Children are starting to plan play together.",
            "focus_growth": "Build collaborative thinking through shared play.",
            "annual_events": "Sports day, performance day",
            "seasonal_context": "Spring to winter transitions",
            "community_resources": "Park and library",
            "care_points": "Balance safety and dialogue",
            "handover_notes": "Children already show interest in group discussion.",
        }

    @staticmethod
    def _monthly_plan_payload() -> dict[str, str]:
        return {
            "classroom_ref": "classroom:5yo-a",
            "target_month": "2026-05",
            "class_name": "Five",
            "owner_name": "Test Admin",
            "related_annual_plan_id_raw": "1",
            "related_term_key": "term_1",
            "previous_reflection": "Children began to coordinate roles in play.",
            "current_children_snapshot": "Small groups are negotiating how to continue shared projects.",
            "play_interests": "Construction, pretend play, drawing maps",
            "seasonal_context": "Early summer weather and outdoor changes",
            "family_context": "Families are talking more about weekend experiences.",
            "class_notes": "Support turn-taking without closing off ideas.",
        }


if __name__ == "__main__":
    unittest.main()