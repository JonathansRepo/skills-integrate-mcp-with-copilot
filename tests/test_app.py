import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import app


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.database_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.database_directory.name) / "activities.sqlite"
        self.original_database_path = app.DATABASE_PATH
        app.DATABASE_PATH = self.database_path
        app.initialize_database()

    def tearDown(self):
        app.DATABASE_PATH = self.original_database_path
        self.database_directory.cleanup()

    def test_seeded_memberships_survive_reinitialization(self):
        app.signup_for_activity("Chess Club", "persistent@mergington.edu")

        app.initialize_database()

        participants = app.get_activities()["Chess Club"]["participants"]
        self.assertIn("persistent@mergington.edu", participants)

    def test_domain_tables_and_relationships_exist(self):
        with sqlite3.connect(self.database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            membership_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(memberships)")
            }

        self.assertTrue(
            {
                "students",
                "teachers",
                "activities",
                "events",
                "memberships",
                "attendance",
                "advisor_requests",
            }.issubset(tables)
        )
        self.assertEqual(
            {"student_id", "activity_id"}.issubset(membership_columns), True
        )

    def test_duplicate_signup_and_unregister_preserve_api_errors(self):
        with self.assertRaisesRegex(Exception, "Student is already signed up"):
            app.signup_for_activity("Chess Club", "michael@mergington.edu")

        app.signup_for_activity("Chess Club", "new@mergington.edu")
        result = app.unregister_from_activity("Chess Club", "new@mergington.edu")

        self.assertEqual(
            result,
            {"message": "Unregistered new@mergington.edu from Chess Club"},
        )
        self.assertNotIn(
            "new@mergington.edu",
            app.get_activities()["Chess Club"]["participants"],
        )


if __name__ == "__main__":
    unittest.main()
