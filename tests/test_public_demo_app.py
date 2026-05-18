import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from hoiku_plan_writer.config import Settings
from hoiku_plan_writer.demo_runtime import DEMO_SESSION_COOKIE_NAME, get_demo_session_manager, reset_demo_runtime_cache
from hoiku_plan_writer.main import create_app
from hoiku_plan_writer.persistence.models import PlanDocumentRecord, SafetyPlanRecord


class PublicDemoAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = Path.cwd() / f"hoiku-plan-demo-app-{uuid4().hex}"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.previous_env = {
            "PUBLIC_DEMO_MODE": os.environ.get("PUBLIC_DEMO_MODE"),
            "DEMO_RUNTIME_DIR": os.environ.get("DEMO_RUNTIME_DIR"),
            "DEMO_SESSION_TTL_MINUTES": os.environ.get("DEMO_SESSION_TTL_MINUTES"),
            "DEMO_SESSION_INPUT_LIMIT_BYTES": os.environ.get("DEMO_SESSION_INPUT_LIMIT_BYTES"),
            "DEMO_MAX_REQUEST_BODY_BYTES": os.environ.get("DEMO_MAX_REQUEST_BODY_BYTES"),
            "DEMO_SECURE_COOKIES": os.environ.get("DEMO_SECURE_COOKIES"),
        }
        self.addCleanup(self._restore_environment)
        self.addCleanup(lambda: shutil.rmtree(self.runtime_dir, ignore_errors=True))

        os.environ["PUBLIC_DEMO_MODE"] = "1"
        os.environ["DEMO_RUNTIME_DIR"] = str(self.runtime_dir.relative_to(Path.cwd()))
        os.environ["DEMO_SESSION_TTL_MINUTES"] = "120"
        os.environ["DEMO_SESSION_INPUT_LIMIT_BYTES"] = "65536"
        os.environ["DEMO_MAX_REQUEST_BODY_BYTES"] = "16384"
        os.environ["DEMO_SECURE_COOKIES"] = "0"
        reset_demo_runtime_cache()
        self.addCleanup(reset_demo_runtime_cache)

        settings = Settings(database_url="sqlite:///./hoiku_plan_writer_public_demo_unused.db")
        self.app = create_app(settings)
        self.client_cm = TestClient(self.app)
        self.client = self.client_cm.__enter__()
        self.addCleanup(self.app.state.engine.dispose)
        self.addCleanup(lambda: self.client_cm.__exit__(None, None, None))

    def _restore_environment(self) -> None:
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _document_count(self, session_id: str) -> int:
        engine = get_demo_session_manager().get_engine(session_id)
        with Session(engine) as session:
            return len(session.exec(select(PlanDocumentRecord)).all())

    def _safety_plan_count(self, session_id: str) -> int:
        engine = get_demo_session_manager().get_engine(session_id)
        with Session(engine) as session:
            return len(session.exec(select(SafetyPlanRecord)).all())

    def test_public_demo_sets_cookie_and_shows_seeded_documents(self) -> None:
        response = self.client.get("/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.client.cookies.get(DEMO_SESSION_COOKIE_NAME))
        self.assertIn("2026年度 年間指導計画", response.text)
        self.assertIn("2026-05 月案", response.text)

        safety_response = self.client.get("/safety-plans/")
        self.assertEqual(safety_response.status_code, 200)
        self.assertIn("2026年度 安全計画", safety_response.text)
        self.assertIn("必須計画と主要な実施ログは期限内です", safety_response.text)

    def test_http_session_isolation_and_reset(self) -> None:
        first_response = self.client.get("/documents/")
        self.assertEqual(first_response.status_code, 200)
        first_session_id = self.client.cookies.get(DEMO_SESSION_COOKIE_NAME)
        self.assertIsNotNone(first_session_id)
        baseline_count = self._document_count(first_session_id)
        baseline_safety_count = self._safety_plan_count(first_session_id)

        create_response = self.client.post(
            "/annual-plans/",
            data={
                "classroom_ref": "classroom:5yo-a",
                "school_year": "2027",
                "class_name": "5歳児",
                "age_group": "5歳児",
                "class_outlook": "年度後半に向けて話し合いの質を高めたい。",
                "focus_growth": "友だちの考えを受け止めながら自分の思いを表す力",
                "annual_events": "運動会、遠足",
                "seasonal_context": "地域の公園を使いやすい。",
                "community_resources": "近隣公園、図書館",
                "care_points": "話し合いに入りにくい子への支援",
                "handover_notes": "昨年度からの遊びの継続を大切にしたい。",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 303)
        self.assertEqual(self._document_count(first_session_id), baseline_count + 1)

        reset_response = self.client.post(
            "/demo/reset",
            data={"redirect_to": "/documents/"},
            follow_redirects=False,
        )
        self.assertEqual(reset_response.status_code, 303)
        self.assertEqual(reset_response.headers["location"], "/documents/")

        self.client.get("/documents/")
        second_session_id = self.client.cookies.get(DEMO_SESSION_COOKIE_NAME)
        self.assertIsNotNone(second_session_id)
        self.assertNotEqual(first_session_id, second_session_id)
        self.assertEqual(self._document_count(second_session_id), baseline_count)
        self.assertEqual(self._safety_plan_count(second_session_id), baseline_safety_count)
