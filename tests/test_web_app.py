import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from hoiku_plan_writer.config import Settings
from hoiku_plan_writer.domain.profile_fields import PROFILE_ALWAYS_ENABLED_KEYS, PROFILE_DEFAULT_ENABLED_KEYS
from hoiku_plan_writer.main import create_app
from hoiku_plan_writer.persistence.repositories import get_document


class WebAppTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, db_path = tempfile.mkstemp(dir=Path.cwd(), prefix="hoiku-plan-test-", suffix=".db")
        os.close(fd)
        self.db_path = Path(db_path)
        settings = Settings(database_url=f"sqlite:///./{self.db_path.name}")
        self.app = create_app(settings)
        self.client_cm = TestClient(self.app)
        self.client = self.client_cm.__enter__()

    def tearDown(self) -> None:
        self.client_cm.__exit__(None, None, None)
        self.app.state.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()

    def _login(self, *, role: str, actor_ref: str, name: str) -> None:
        response = self.client.post(
            "/staff/login",
            data={
                "role": role,
                "actor_ref": actor_ref,
                "nursery_ref": "nursery:test",
                "classroom_refs_raw": "classroom:5yo-a",
                "name": name,
                "redirect_to": "/documents/",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def _login_as_admin(self) -> None:
        self._login(role="admin", actor_ref="staff:test-admin", name="テスト管理者")

    def _login_as_editor(self) -> None:
        self._login(role="can_edit", actor_ref="staff:test-editor", name="テスト職員")

    def _profile_payload(self, *, enabled_optional_fields: set[str] | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "nursery_name": "テスト保育園",
            "target_age_group": "3〜5歳児",
            "class_configuration": "年長1クラス",
            "philosophy": "子どもの主体性を大切にする。",
            "childcare_goal": "遊びを通して考える力を育む。",
            "desired_child_image": "友だちと協力して遊びを進める子ども。",
            "child_view": "一人ひとりの思いを尊重する。",
            "play_view": "探究が続く遊びを支える。",
            "support_policy": "見守りを基調に必要な援助を行う。",
            "indoor_environment": "落ち着いて選べる室内環境を整える。",
            "outdoor_environment": "季節を感じられる園庭活動を取り入れる。",
            "corner_play": "制作とごっこ遊びのコーナーを継続する。",
            "community_resources": "公園と図書館を活用する。",
            "family_collaboration_policy": "家庭と日々の姿を共有する。",
            "local_collaboration_policy": "地域との関わりを保育に生かす。",
            "health_and_safety_policy": "安心安全を日常的に確認する。",
            "inclusive_policy": "違いを受け止め合える集団づくりを行う。",
            "preferred_expressions": "自ら気づく、確かめ合う",
            "avoid_expressions": "一律にさせる",
            "sentence_tone": "やわらかく丁寧",
            "missing_input_policy": "未入力は要確認とする。",
            "confirmation_marker": "要確認",
            "evidence_tag_policy": "根拠タグを表示する。",
        }

        default_optional_fields = set(PROFILE_DEFAULT_ENABLED_KEYS) - set(PROFILE_ALWAYS_ENABLED_KEYS)
        enabled_fields = enabled_optional_fields if enabled_optional_fields is not None else default_optional_fields
        payload["enabled_field_keys"] = sorted(enabled_fields)
        return payload

    def _document_edit_payload(
        self,
        document_id: int,
        *,
        title: str | None = None,
        comment: str = "",
        updates: dict[str, str] | None = None,
    ) -> dict[str, str]:
        with Session(self.app.state.engine) as session:
            document = get_document(session, document_id, nursery_ref="nursery:test")
            assert document is not None
            payload = {
                "title": title or document.title,
                "comment": comment,
            }
            for block in document.blocks:
                payload[f"block_body_{block.id}"] = updates.get(block.section_key, block.body) if updates else block.body
            return payload

    def test_document_dashboard_renders_empty_state(self) -> None:
        response = self.client.get("/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("まだ文書はありません", response.text)

    def test_profile_form_shows_toggle_and_examples(self) -> None:
        self._login_as_admin()

        response = self.client.get("/nursery-profile/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("この項目を使用", response.text)
        self.assertIn("記入例", response.text)
        self.assertIn("子どもが自分で選べるよう、制作・ごっこ・絵本の場をゆるやかに分けて配置する。", response.text)

    def test_classroom_ref_is_hidden_from_annual_form(self) -> None:
        self._login_as_admin()

        response = self.client.get("/annual-plans/new")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(">classroom_ref<", response.text)
        self.assertNotIn(">classroom:5yo-a<", response.text)

    def test_saved_profile_requires_activation_and_can_be_activated_later(self) -> None:
        self._login_as_editor()

        payload = self._profile_payload()
        payload["action"] = "save"
        save_response = self.client.post(
            "/nursery-profile/",
            data=payload,
            follow_redirects=False,
        )
        self.assertEqual(save_response.status_code, 303)

        annual_form = self.client.get("/annual-plans/new")
        self.assertEqual(annual_form.status_code, 200)
        self.assertIn("保存済みの園プロフィール: v1 / テスト保育園", annual_form.text)
        self.assertIn("まだ下書きのため年間指導計画には反映されません", annual_form.text)

        self._login_as_admin()
        activate_response = self.client.post(
            "/nursery-profile/1/activate",
            follow_redirects=False,
        )
        self.assertEqual(activate_response.status_code, 303)

        annual_form_after_activate = self.client.get("/annual-plans/new")
        self.assertEqual(annual_form_after_activate.status_code, 200)
        self.assertIn("有効な園プロファイル: v1 / テスト保育園", annual_form_after_activate.text)

    def test_annual_preview_reflects_profile_content(self) -> None:
        self._login_as_admin()

        payload = self._profile_payload()
        payload["philosophy"] = "対話から育ちを編む園である。"
        payload["childcare_goal"] = "協同して考える力を育てる。"
        payload["desired_child_image"] = "友だちと折り合いをつけて遊びを深める子ども。"
        payload["local_collaboration_policy"] = "地域の人との関わりを保育に取り入れる。"
        payload["action"] = "activate"
        profile_response = self.client.post(
            "/nursery-profile/",
            data=payload,
            follow_redirects=False,
        )
        self.assertEqual(profile_response.status_code, 303)

        annual_preview = self.client.post(
            "/annual-plans/preview",
            data={
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
            },
        )
        self.assertEqual(annual_preview.status_code, 200)
        self.assertIn("対話から育ちを編む園である。", annual_preview.text)
        self.assertIn("協同して考える力を育てる。", annual_preview.text)
        self.assertIn("友だちと折り合いをつけて遊びを深める子ども。", annual_preview.text)
        self.assertIn("地域の人との関わりを保育に取り入れる。", annual_preview.text)

    def test_disabled_profile_field_is_ignored_in_generation(self) -> None:
        self._login_as_admin()

        enabled_optional_fields = set(PROFILE_DEFAULT_ENABLED_KEYS) - set(PROFILE_ALWAYS_ENABLED_KEYS)
        enabled_optional_fields.discard("indoor_environment")
        payload = self._profile_payload(enabled_optional_fields=enabled_optional_fields)
        payload["indoor_environment"] = "生成に使いたくない室内環境"
        payload["action"] = "activate"
        profile_response = self.client.post(
            "/nursery-profile/",
            data=payload,
            follow_redirects=False,
        )
        self.assertEqual(profile_response.status_code, 303)

        annual_preview = self.client.post(
            "/annual-plans/preview",
            data={
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
            },
        )
        self.assertEqual(annual_preview.status_code, 200)
        self.assertIn("落ち着いて選べる環境", annual_preview.text)
        self.assertNotIn("生成に使いたくない室内環境", annual_preview.text)

    def test_draft_document_can_be_edited_and_resubmitted(self) -> None:
        self._login_as_admin()

        payload = self._profile_payload()
        payload["action"] = "activate"
        self.client.post("/nursery-profile/", data=payload, follow_redirects=False)

        annual_create = self.client.post(
            "/annual-plans/",
            data={
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
            },
            follow_redirects=False,
        )
        self.assertEqual(annual_create.status_code, 303)

        first_send_payload = self._document_edit_payload(
            1,
            comment="初回送信です。",
            updates={"annual_goal": "手動で整えた年間の大きなねらい"},
        )
        first_send_payload["action"] = "submit"
        first_send = self.client.post("/documents/1/edit", data=first_send_payload, follow_redirects=False)
        self.assertEqual(first_send.status_code, 303)

        sent_detail = self.client.get("/documents/1")
        self.assertIn("送信済み", sent_detail.text)
        self.assertIn("手動で整えた年間の大きなねらい", sent_detail.text)
        self.assertIn("送信", sent_detail.text)
        self.assertNotIn("クラス: classroom:5yo-a", sent_detail.text)

        resend_payload = self._document_edit_payload(
            1,
            comment="表現を調整して再送信します。",
            updates={"annual_goal": "再送信後の年間の大きなねらい"},
        )
        resend_payload["action"] = "submit"
        resend = self.client.post("/documents/1/edit", data=resend_payload, follow_redirects=False)
        self.assertEqual(resend.status_code, 303)

        resent_detail = self.client.get("/documents/1")
        self.assertIn("再送信後の年間の大きなねらい", resent_detail.text)
        self.assertIn("再送信", resent_detail.text)

    def test_profile_annual_and_monthly_workflow(self) -> None:
        self._login_as_admin()

        payload = self._profile_payload()
        payload["action"] = "activate"
        profile_response = self.client.post(
            "/nursery-profile/",
            data=payload,
            follow_redirects=False,
        )
        self.assertEqual(profile_response.status_code, 303)

        annual_preview = self.client.post(
            "/annual-plans/preview",
            data={
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
            },
        )
        self.assertEqual(annual_preview.status_code, 200)
        self.assertIn("年間の大きなねらい", annual_preview.text)
        self.assertIn("園プロファイル v1", annual_preview.text)

        annual_create = self.client.post(
            "/annual-plans/",
            data={
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
            },
            follow_redirects=False,
        )
        self.assertEqual(annual_create.status_code, 303)
        self.assertEqual(annual_create.headers["location"], "/documents/1")

        monthly_create = self.client.post(
            "/monthly-plans/",
            data={
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
            },
            follow_redirects=False,
        )
        self.assertEqual(monthly_create.status_code, 303)
        self.assertEqual(monthly_create.headers["location"], "/documents/2")

        detail = self.client.get("/documents/2")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("月末の振り返り観点", detail.text)
        self.assertIn("document:annual-plan", detail.text)
        self.assertIn("下書き", detail.text)
        self.assertNotIn("クラス: classroom:5yo-a", detail.text)

        submit_payload = self._document_edit_payload(2, comment="確認をお願いします。")
        submit_payload["action"] = "submit"
        submit = self.client.post("/documents/2/edit", data=submit_payload, follow_redirects=False)
        self.assertEqual(submit.status_code, 303)

        submitted_detail = self.client.get("/documents/2")
        self.assertIn("送信済み", submitted_detail.text)
        self.assertIn("確認をお願いします。", submitted_detail.text)

        approve = self.client.post(
            "/documents/2/status",
            data={"action": "approve", "comment": "確認完了"},
            follow_redirects=False,
        )
        self.assertEqual(approve.status_code, 303)

        approved_detail = self.client.get("/documents/2")
        self.assertIn("承認済み", approved_detail.text)
        self.assertIn("確認完了", approved_detail.text)


if __name__ == "__main__":
    unittest.main()
