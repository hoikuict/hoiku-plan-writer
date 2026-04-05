import shutil
import time
import unittest
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session, select

from hoiku_plan_writer.demo_runtime import DemoSessionManager, DemoSettings
from hoiku_plan_writer.demo_seed import DEMO_NURSERY_REF, initialize_demo_template_database
from hoiku_plan_writer.persistence.models import NurseryProfileRecord, PlanDocumentRecord


class DemoRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = Path.cwd() / f"hoiku-plan-demo-runtime-{uuid4().hex}"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.settings = DemoSettings(
            enabled=True,
            runtime_dir=self.runtime_dir,
            base_db_path=self.runtime_dir / "demo-template.sqlite3",
            sessions_dir=self.runtime_dir / "sessions",
            session_ttl_seconds=1,
            session_input_limit_bytes=1024,
            max_request_body_bytes=512,
            secure_cookies=False,
            cleanup_interval_seconds=1,
        )
        self.manager = DemoSessionManager(self.settings)
        self.manager.prepare_base_database(initialize_demo_template_database)

    def tearDown(self) -> None:
        self.manager.close()
        shutil.rmtree(self.runtime_dir, ignore_errors=True)

    def test_session_databases_are_isolated(self) -> None:
        first_engine = self.manager.get_engine("a" * 32)
        second_engine = self.manager.get_engine("b" * 32)

        with Session(first_engine) as session:
            profile = session.exec(
                select(NurseryProfileRecord).where(NurseryProfileRecord.nursery_ref == DEMO_NURSERY_REF)
            ).first()
            self.assertIsNotNone(profile)
            profile.nursery_name = "セッションA園"
            session.add(profile)
            session.commit()

        with Session(second_engine) as session:
            untouched_profile = session.exec(
                select(NurseryProfileRecord).where(NurseryProfileRecord.nursery_ref == DEMO_NURSERY_REF)
            ).first()
            self.assertIsNotNone(untouched_profile)
            self.assertNotEqual(untouched_profile.nursery_name, "セッションA園")

    def test_template_database_contains_seeded_documents(self) -> None:
        first_engine = self.manager.get_engine("c" * 32)

        with Session(first_engine) as session:
            documents = session.exec(select(PlanDocumentRecord).order_by(PlanDocumentRecord.id)).all()

        self.assertGreaterEqual(len(documents), 2)
        self.assertEqual(documents[0].document_type, "annual")
        self.assertEqual(documents[1].document_type, "monthly")

    def test_cleanup_removes_expired_sessions(self) -> None:
        session_id = "d" * 32
        self.manager.ensure_session_database(session_id)
        touch_path = self.settings.sessions_dir / session_id / ".last_seen"
        self.assertTrue(touch_path.exists())
        time.sleep(1.1)

        self.manager.cleanup_expired_sessions(force=True)

        self.assertFalse((self.settings.sessions_dir / session_id).exists())