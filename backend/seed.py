"""Populate CampusFix with demo data so the admin dashboard has something to show.

Usage:  python seed.py          (adds demo data only if the database has no users)
        python seed.py --reset  (wipes all data first)
"""
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import CATEGORIES, app

WARDEN = ("Mr. Raghavan (Warden)", "warden@campusfix.test", "Warden@123")
STUDENTS = [
    ("Aarav Mehta", "aarav@campusfix.test", "A-101"),
    ("Sneha Iyer", "sneha@campusfix.test", "B-204"),
    ("Rohan Das", "rohan@campusfix.test", "A-310"),
    ("Priya Nair", "priya@campusfix.test", "C-112"),
    ("Kabir Singh", "kabir@campusfix.test", "B-017"),
]
STUDENT_PASSWORD = "Student@123"

SAMPLES = {
    "Electrical": ["Ceiling fan makes grinding noise", "Socket near study table sparks",
                   "Tube light flickers at night"],
    "Plumbing": ["Tap leaking in bathroom", "No hot water in geyser", "Flush tank keeps running"],
    "Furniture": ["Study chair broken armrest", "Wardrobe door off its hinge", "Cot mattress sagging"],
    "Internet": ["Wi-Fi drops every evening", "No LAN signal on 3rd floor", "Router in corridor offline"],
    "Cleaning": ["Corridor not swept for 3 days", "Dustbins overflowing near stairs",
                 "Washroom needs deep cleaning"],
    "Other": ["Main gate light not working", "Water cooler out of order"],
}


def main():
    reset = "--reset" in sys.argv
    random.seed(7)
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        if reset:
            for t in ("updates", "complaints", "users"):
                db.execute(f"DELETE FROM {t}")
            db.commit()
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            print("Database already has users - run with --reset to re-seed.")
            return

        base = datetime.now(timezone.utc) - timedelta(days=21)

        def iso(dt):
            return dt.isoformat(timespec="seconds")

        db.execute(
            "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?,?,?,'warden',?)",
            (WARDEN[0], WARDEN[1], generate_password_hash(WARDEN[2]), iso(base)))
        warden_id = db.execute("SELECT id FROM users WHERE role='warden'").fetchone()[0]

        student_ids = []
        for name, email, room in STUDENTS:
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash, role, room, created_at)"
                " VALUES (?,?,?,'student',?,?)",
                (name, email, generate_password_hash(STUDENT_PASSWORD), room, iso(base)))
            student_ids.append((cur.lastrowid, room))

        for _ in range(28):
            uid, room = random.choice(student_ids)
            cat = random.choice(CATEGORIES)
            title = random.choice(SAMPLES[cat])
            priority = random.choices(["Low", "Medium", "High"], weights=[3, 4, 2])[0]
            created = base + timedelta(days=random.uniform(0, 20), hours=random.uniform(0, 12))
            status = random.choices(["Open", "In Progress", "Resolved"], weights=[3, 3, 5])[0]
            resolved_at = rating = None
            updated = created
            if status == "Resolved":
                resolved = created + timedelta(hours=random.uniform(3, 90))
                resolved_at, updated = iso(resolved), resolved
                rating = random.choice([3, 4, 4, 5, 5, None])
            elif status == "In Progress":
                updated = created + timedelta(hours=random.uniform(1, 24))
            cur = db.execute(
                """INSERT INTO complaints (user_id, title, description, category, priority,
                   status, room, rating, created_at, updated_at, resolved_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (uid, title, f"{title}. Please look into this at the earliest.", cat,
                 priority, status, room, rating, iso(created), iso(updated), resolved_at))
            cid = cur.lastrowid
            db.execute(
                "INSERT INTO updates (complaint_id, user_id, message, status_change, created_at)"
                " VALUES (?,?,?,?,?)", (cid, uid, "Complaint submitted.", "Open", iso(created)))
            if status != "Open":
                db.execute(
                    "INSERT INTO updates (complaint_id, user_id, message, status_change, created_at)"
                    " VALUES (?,?,?,?,?)",
                    (cid, warden_id, "Maintenance staff assigned.", "In Progress",
                     iso(created + timedelta(hours=1))))
            if status == "Resolved":
                db.execute(
                    "INSERT INTO updates (complaint_id, user_id, message, status_change, created_at)"
                    " VALUES (?,?,?,?,?)",
                    (cid, warden_id, "Issue fixed and verified.", "Resolved", resolved_at))
        db.commit()
        db.close()

    print("Demo data created.")
    print(f"  Warden : {WARDEN[1]} / {WARDEN[2]}")
    print(f"  Student: {STUDENTS[0][1]} / {STUDENT_PASSWORD}  (all students share this password)")


if __name__ == "__main__":
    main()
