import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ai_service
import database


class OwnerAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        self.original_get_connection = database.get_connection
        database.DB_PATH = Path(self.temp_dir.name) / "test.db"
        get_connection = self.original_get_connection

        @contextmanager
        def closed_connection():
            conn = get_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        database.get_connection = closed_connection
        database.init_db()
        with database.get_connection() as conn:
            self.meeting_id = conn.execute(
                """
                INSERT INTO meetings (title, meeting_date, raw_notes)
                VALUES (?, ?, ?)
                """,
                ("Owner test", "2026-10-30", "Test notes"),
            ).lastrowid
            self.task_id = conn.execute(
                """
                INSERT INTO action_items
                    (meeting_id, description, owner, due_date, status, outcome)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.meeting_id,
                    "Check for bugs",
                    None,
                    "2026-11-02",
                    "In Progress",
                    "Existing outcome",
                ),
            ).lastrowid

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        database.get_connection = self.original_get_connection
        self.temp_dir.cleanup()

    def test_owner_update_persists_without_changing_other_task_fields(self):
        database.update_task_owner(self.task_id, "  Sarvesh  ")

        with database.get_connection() as conn:
            task = dict(
                conn.execute(
                    "SELECT * FROM action_items WHERE id = ?",
                    (self.task_id,),
                ).fetchone()
            )

        self.assertEqual(task["owner"], "Sarvesh")
        self.assertEqual(task["status"], "In Progress")
        self.assertEqual(task["due_date"], "2026-11-02")
        self.assertEqual(task["outcome"], "Existing outcome")
        self.assertEqual(task["meeting_id"], self.meeting_id)
        self.assertEqual(len(database.get_open_tasks("  sarvesh ")), 1)

        database.update_task_owner(self.task_id, " ")
        with database.get_connection() as conn:
            owner = conn.execute(
                "SELECT owner FROM action_items WHERE id = ?",
                (self.task_id,),
            ).fetchone()["owner"]

        self.assertIsNone(owner)

    def test_extraction_prompt_keeps_structured_output_and_assignment_examples(self):
        analysis = ai_service.MeetingAnalysis(
            summary="Tasks were assigned.",
            decisions=[],
            risks=[],
            action_items=[
                ai_service.ActionItem(
                    description="Check for bugs at an early stage",
                    owner="Sarvesh",
                ),
                ai_service.ActionItem(
                    description="Ensure all files are compiled and tested",
                    owner="Rahul",
                ),
            ],
        )
        generate_content = Mock(
            return_value=SimpleNamespace(parsed=analysis)
        )
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )

        with (
            patch.object(
                ai_service.st,
                "secrets",
                {"GEMINI_API_KEY": "test-key"},
            ),
            patch.object(ai_service.genai, "Client", return_value=client),
        ):
            result = ai_service.analyze_meeting(
                "Owner extraction test",
                "Sarvesh, Rahul",
                (
                    "Sarvesh will check for bugs at an early stage. "
                    "Rahul will ensure all files are compiled and tested. "
                    "The team will review the results in the next meeting."
                ),
            )

        call = generate_content.call_args.kwargs
        self.assertEqual(call["model"], "gemini-2.5-flash")
        self.assertEqual(
            call["config"]["response_mime_type"],
            "application/json",
        )
        self.assertIs(
            call["config"]["response_schema"],
            ai_service.MeetingAnalysis,
        )
        for example in (
            "Sarvesh will check for bugs",
            "Assign bug checking to Sarvesh",
            "Sarvesh is responsible for testing",
            "Rahul will ensure all files are compiled and tested",
        ):
            self.assertIn(example, call["contents"])
        self.assertEqual(
            [(item.description, item.owner) for item in result.action_items],
            [
                ("Check for bugs at an early stage", "Sarvesh"),
                ("Ensure all files are compiled and tested", "Rahul"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
