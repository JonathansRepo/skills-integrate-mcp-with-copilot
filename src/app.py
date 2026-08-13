"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from contextlib import closing
import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DATABASE_PATH = Path(
    os.getenv("ACTIVITIES_DATABASE", current_dir / "activities.sqlite")
)

SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    grade_level INTEGER
);
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    schedule TEXT NOT NULL,
    max_participants INTEGER NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0,
    organizer_teacher_id INTEGER REFERENCES teachers(id)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activities(id),
    name TEXT NOT NULL,
    description TEXT,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    location TEXT,
    capacity INTEGER
);
CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    activity_id INTEGER NOT NULL REFERENCES activities(id),
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, activity_id)
);
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    checked_in_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checked_out_at TEXT,
    UNIQUE(student_id, event_id)
);
CREATE TABLE IF NOT EXISTS advisor_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    activity_id INTEGER NOT NULL REFERENCES activities(id),
    position TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    UNIQUE(student_id, activity_id)
);
"""


def connect_database(database_path=None):
    if database_path is None:
        database_path = DATABASE_PATH
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path=None):
    with closing(connect_database(database_path)) as connection:
        connection.executescript(SCHEMA)
        activity_count = connection.execute(
            "SELECT COUNT(*) FROM activities"
        ).fetchone()[0]
        if activity_count == 0:
            for name, activity in SEED_ACTIVITIES.items():
                cursor = connection.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        name,
                        activity["description"],
                        activity["schedule"],
                        activity["max_participants"],
                    ),
                )
                activity_id = cursor.lastrowid
                for email in activity["participants"]:
                    student_id = connection.execute(
                        "INSERT OR IGNORE INTO students (email) VALUES (?) RETURNING id",
                        (email,),
                    ).fetchone()
                    if student_id is None:
                        student_id = connection.execute(
                            "SELECT id FROM students WHERE email = ?", (email,)
                        ).fetchone()
                    connection.execute(
                        "INSERT INTO memberships (student_id, activity_id) VALUES (?, ?)",
                        (student_id[0], activity_id),
                    )
        connection.commit()


initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with closing(connect_database()) as connection:
        rows = connection.execute(
            """
            SELECT activities.name, activities.description, activities.schedule,
                   activities.max_participants,
                   GROUP_CONCAT(students.email) AS participant_emails
            FROM activities
            LEFT JOIN memberships ON memberships.activity_id = activities.id
            LEFT JOIN students ON students.id = memberships.student_id
            WHERE activities.archived = 0
            GROUP BY activities.id
            ORDER BY activities.name
            """
        ).fetchall()

    return {
        row["name"]: {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": (
                row["participant_emails"].split(",")
                if row["participant_emails"]
                else []
            ),
        }
        for row in rows
    }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with closing(connect_database()) as connection:
        activity = connection.execute(
            "SELECT id FROM activities WHERE name = ? AND archived = 0",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        student = connection.execute(
            "INSERT OR IGNORE INTO students (email) VALUES (?) RETURNING id",
            (email,),
        ).fetchone()
        if student is None:
            student = connection.execute(
                "SELECT id FROM students WHERE email = ?", (email,)
            ).fetchone()

        try:
            connection.execute(
                "INSERT INTO memberships (student_id, activity_id) VALUES (?, ?)",
                (student[0], activity[0]),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up",
            )
        connection.commit()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with closing(connect_database()) as connection:
        membership = connection.execute(
            """
            SELECT memberships.id
            FROM memberships
            JOIN activities ON activities.id = memberships.activity_id
            JOIN students ON students.id = memberships.student_id
            WHERE activities.name = ? AND activities.archived = 0 AND students.email = ?
            """,
            (activity_name, email),
        ).fetchone()
        if membership is None:
            activity = connection.execute(
                "SELECT id FROM activities WHERE name = ? AND archived = 0",
                (activity_name,),
            ).fetchone()
            if activity is None:
                raise HTTPException(status_code=404, detail="Activity not found")
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity",
            )

        connection.execute(
            "DELETE FROM memberships WHERE id = ?", (membership[0],)
        )
        connection.commit()
    return {"message": f"Unregistered {email} from {activity_name}"}
