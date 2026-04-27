import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from hoiku_plan_writer.config import Settings
from hoiku_plan_writer.main import create_app


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

    def _profile_payload(self) -> dict[str, str]:
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
            "corner_play": "制作とごっこ遊びのコーナーを継続する。",
            "community_resources": "公園と図書館を活用する。",
            "family_collaboration_policy": "家庭と日々の姿を共有する。",
            "local_collaboration_policy": "地域との関わりを保育に生かす。",
            "health_and_safety_policy": "安心安全を日常的に確認する。",
            "inclusive_policy": "違いを受け止め合える集団づくりを行う。",
            "daily_rhythm": "午前の遊びと午後の休息を大切にする。",
            "preferred_expressions": "自ら気づく、確かめ合う",
            "avoid_expressions": "一律にさせる",
            "sentence_tone": "やわらかく丁寧",
            "document_format_notes": "一文を短めにする。",
            "missing_input_policy": "未入力は要確認とする。",
            "confirmation_marker": "要確認",
            "evidence_tag_policy": "根拠タグを表示する。",
            "privacy_policy": "個人名、診断名、健康詳細を含めない。",
        }

    def test_document_dashboard_renders_empty_state(self) -> None:
        response = self.client.get("/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("まだ文書はありません", response.text)

    def test_profile_activation_shows_missing_required_fields(self) -> None:
        self._login_as_admin()
        payload = self._profile_payload()
        payload["philosophy"] = ""

        response = self.client.post(
            "/nursery-profile/",
            data={**payload, "action": "activate"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("有効化には必須項目の入力が必要です", response.text)
        self.assertIn("理念", response.text)

    def test_profile_review_warns_about_personal_information(self) -> None:
        self._login_as_admin()
        payload = self._profile_payload()
        payload["local_context"] = "山田さんの自宅近くの公園を使う。"

        response = self.client.post(
            "/nursery-profile/",
            data={**payload, "action": "review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("個人情報の可能性", response.text)
        self.assertIn("地域特性", response.text)

    def test_profile_annual_and_monthly_workflow(self) -> None:
        self._login_as_admin()

        profile_response = self.client.post(
            "/nursery-profile/",
            data={**self._profile_payload(), "action": "activate"},
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
        self.assertIn("文書を編集", detail.text)

        submit = self.client.post(
            "/documents/2/edit",
            data={"action": "submit", "title": "2026-05 月案（5歳児）", "comment": "確認をお願いします。"},
            follow_redirects=False,
        )
        self.assertEqual(submit.status_code, 303)

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
