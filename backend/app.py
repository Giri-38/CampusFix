"""CampusFix API - hostel complaint & maintenance tracker (REST backend).

Flask + SQLite JSON API with JWT bearer authentication and two roles
(student, warden). The React frontend in ../frontend talks to this API.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

CATEGORIES = ["Electrical", "Plumbing", "Furniture", "Internet", "Cleaning", "Other"]
PRIORITIES = ["Low", "Medium", "High"]
STATUSES = ["Open", "In Progress", "Resolved"]
TOKEN_HOURS = 8

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'warden')),
    room TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',
    room TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT NOT NULL,
    status_change TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints(user_id);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("CAMPUSFIX_SECRET", "dev-only-change-me-32-bytes-minimum!"),
        DATABASE=os.environ.get(
            "CAMPUSFIX_DB", os.path.join(app.root_path, "campusfix.db")),
        FRONTEND_DIST=os.path.join(app.root_path, "..", "frontend", "dist"),
    )
    if test_config:
        app.config.update(test_config)
    CORS(app, resources={r"/api/*": {"origins": os.environ.get(
        "CAMPUSFIX_CORS", "http://localhost:5173").split(",")}})

    # ------------------------------------------------------------ database
    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)
        get_db().commit()

    # ---------------------------------------------------------------- auth
    def make_token(user):
        payload = {"sub": str(user["id"]), "role": user["role"],
                   "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)}
        return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

    def public_user(u):
        return {"id": u["id"], "name": u["name"], "email": u["email"],
                "role": u["role"], "room": u["room"]}

    def auth_required(roles=None):
        def deco(view):
            @wraps(view)
            def wrapped(*a, **kw):
                header = request.headers.get("Authorization", "")
                if not header.startswith("Bearer "):
                    raise ApiError("Authentication required.", 401)
                try:
                    data = jwt.decode(header[7:], app.config["SECRET_KEY"],
                                      algorithms=["HS256"])
                except jwt.ExpiredSignatureError:
                    raise ApiError("Session expired. Please log in again.", 401)
                except jwt.InvalidTokenError:
                    raise ApiError("Invalid token.", 401)
                user = get_db().execute(
                    "SELECT * FROM users WHERE id = ?", (data["sub"],)).fetchone()
                if user is None:
                    raise ApiError("Account no longer exists.", 401)
                if roles and user["role"] not in roles:
                    raise ApiError("You do not have access to this resource.", 403)
                g.user = user
                return view(*a, **kw)
            return wrapped
        return deco

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ApiError("Request body must be a JSON object.")
        return data

    def text(data, key, max_len, label=None):
        value = data.get(key, "")
        if not isinstance(value, str):
            raise ApiError(f"{label or key} must be text.")
        value = value.strip()
        if len(value) > max_len:
            raise ApiError(f"{label or key} must be at most {max_len} characters.")
        return value

    @app.post("/api/auth/register")
    def register():
        data = body()
        name = text(data, "name", 80, "Name")
        email = text(data, "email", 120, "Email").lower()
        room = text(data, "room", 20, "Room")
        password = data.get("password", "")
        if not name or not room:
            raise ApiError("Name and room number are required.")
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ApiError("Enter a valid email address.")
        if not isinstance(password, str) or len(password) < 8:
            raise ApiError("Password must be at least 8 characters.")
        try:
            get_db().execute(
                "INSERT INTO users (name, email, password_hash, role, room, created_at)"
                " VALUES (?, ?, ?, 'student', ?, ?)",
                (name, email, generate_password_hash(password), room, now_iso()))
            get_db().commit()
        except sqlite3.IntegrityError:
            raise ApiError("That email is already registered.", 409)
        return jsonify({"message": "Account created."}), 201

    @app.post("/api/auth/login")
    def login():
        data = body()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            raise ApiError("Incorrect email or password.", 401)
        return jsonify({"token": make_token(user), "user": public_user(user)})

    @app.get("/api/auth/me")
    @auth_required()
    def me():
        return jsonify({"user": public_user(g.user)})

    @app.get("/api/meta")
    def meta():
        return jsonify({"categories": CATEGORIES, "priorities": PRIORITIES,
                        "statuses": STATUSES})

    # ---------------------------------------------------------- complaints
    LIST_SQL = ("SELECT c.*, u.name AS student_name FROM complaints c "
                "JOIN users u ON u.id = c.user_id")

    def load_complaint(cid):
        row = get_db().execute(
            LIST_SQL + " WHERE c.id = ?", (cid,)).fetchone()
        if row is None:
            raise ApiError("Complaint not found.", 404)
        if g.user["role"] != "warden" and row["user_id"] != g.user["id"]:
            raise ApiError("You do not have access to this complaint.", 403)
        return row

    @app.get("/api/complaints")
    @auth_required()
    def list_complaints():
        sql, params = LIST_SQL + " WHERE 1=1", []
        if g.user["role"] != "warden":
            sql += " AND c.user_id = ?"
            params.append(g.user["id"])
        status = request.args.get("status", "")
        category = request.args.get("category", "")
        q = request.args.get("q", "").strip()
        if status in STATUSES:
            sql += " AND c.status = ?"
            params.append(status)
        if category in CATEGORIES:
            sql += " AND c.category = ?"
            params.append(category)
        if q:
            like = f"%{q}%"
            sql += " AND (c.title LIKE ? OR c.room LIKE ? OR u.name LIKE ?)"
            params += [like, like, like]
        sql += (" ORDER BY CASE c.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,"
                " c.id DESC" if g.user["role"] == "warden" else " ORDER BY c.id DESC")
        rows = get_db().execute(sql, params).fetchall()
        return jsonify({"complaints": [dict(r) for r in rows]})

    @app.post("/api/complaints")
    @auth_required(roles=["student"])
    def create_complaint():
        data = body()
        title = text(data, "title", 120, "Title")
        description = text(data, "description", 2000, "Description")
        category, priority = data.get("category"), data.get("priority")
        room = text(data, "room", 20, "Room") or (g.user["room"] or "")
        if len(title) < 5:
            raise ApiError("Title must be between 5 and 120 characters.")
        if len(description) < 10:
            raise ApiError("Please describe the problem in at least 10 characters.")
        if category not in CATEGORIES or priority not in PRIORITIES:
            raise ApiError("Choose a valid category and priority.")
        if not room:
            raise ApiError("Room number is required.")
        ts, db = now_iso(), get_db()
        cur = db.execute(
            """INSERT INTO complaints (user_id, title, description, category, priority,
               status, room, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?)""",
            (g.user["id"], title, description, category, priority, room, ts, ts))
        db.execute(
            "INSERT INTO updates (complaint_id, user_id, message, status_change, created_at)"
            " VALUES (?, ?, ?, 'Open', ?)",
            (cur.lastrowid, g.user["id"], "Complaint submitted.", ts))
        db.commit()
        return jsonify({"complaint": dict(load_complaint(cur.lastrowid))}), 201

    @app.get("/api/complaints/<int:cid>")
    @auth_required()
    def get_complaint(cid):
        complaint = load_complaint(cid)
        timeline = get_db().execute(
            """SELECT up.id, up.message, up.status_change, up.created_at,
                      u.name, u.role FROM updates up JOIN users u ON u.id = up.user_id
               WHERE up.complaint_id = ? ORDER BY up.id""", (cid,)).fetchall()
        return jsonify({"complaint": dict(complaint),
                        "timeline": [dict(t) for t in timeline]})

    @app.post("/api/complaints/<int:cid>/comments")
    @auth_required()
    def add_comment(cid):
        load_complaint(cid)
        message = text(body(), "message", 1000, "Message")
        if not message:
            raise ApiError("Write a message before posting.")
        ts, db = now_iso(), get_db()
        db.execute("INSERT INTO updates (complaint_id, user_id, message, created_at)"
                   " VALUES (?, ?, ?, ?)", (cid, g.user["id"], message, ts))
        db.execute("UPDATE complaints SET updated_at = ? WHERE id = ?", (ts, cid))
        db.commit()
        return jsonify({"message": "Comment added."}), 201

    @app.post("/api/complaints/<int:cid>/status")
    @auth_required(roles=["warden"])
    def update_status(cid):
        complaint = load_complaint(cid)
        data = body()
        new_status = data.get("status")
        if new_status not in STATUSES:
            raise ApiError("Invalid status.")
        raw_note = text(data, "note", 500, "Note")
        note = raw_note or f"Status changed to {new_status}."
        ts, db = now_iso(), get_db()
        db.execute(
            "UPDATE complaints SET status = ?, updated_at = ?, resolved_at = ? WHERE id = ?",
            (new_status, ts, ts if new_status == "Resolved" else None, cid))
        if new_status != complaint["status"] or raw_note:
            db.execute(
                "INSERT INTO updates (complaint_id, user_id, message, status_change, created_at)"
                " VALUES (?, ?, ?, ?, ?)", (cid, g.user["id"], note, new_status, ts))
        db.commit()
        return jsonify({"complaint": dict(load_complaint(cid))})

    @app.post("/api/complaints/<int:cid>/rating")
    @auth_required(roles=["student"])
    def rate(cid):
        complaint = load_complaint(cid)
        if complaint["status"] != "Resolved":
            raise ApiError("You can rate a complaint only after it is resolved.")
        rating = body().get("rating")
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ApiError("Rating must be a whole number from 1 to 5.")
        get_db().execute("UPDATE complaints SET rating = ? WHERE id = ?", (rating, cid))
        get_db().commit()
        return jsonify({"complaint": dict(load_complaint(cid))})

    # ----------------------------------------------------------- analytics
    @app.get("/api/stats")
    @auth_required(roles=["warden"])
    def stats():
        db = get_db()
        by_status = {s: 0 for s in STATUSES}
        for r in db.execute("SELECT status, COUNT(*) n FROM complaints GROUP BY status"):
            by_status[r["status"]] = r["n"]
        by_category = {c: 0 for c in CATEGORIES}
        for r in db.execute("SELECT category, COUNT(*) n FROM complaints GROUP BY category"):
            by_category[r["category"]] = r["n"]
        open_by_priority = {p: 0 for p in PRIORITIES}
        for r in db.execute("SELECT priority, COUNT(*) n FROM complaints "
                            "WHERE status != 'Resolved' GROUP BY priority"):
            open_by_priority[r["priority"]] = r["n"]
        hours = []
        for r in db.execute("SELECT created_at, resolved_at FROM complaints "
                            "WHERE resolved_at IS NOT NULL"):
            delta = datetime.fromisoformat(r["resolved_at"]) - datetime.fromisoformat(r["created_at"])
            hours.append(delta.total_seconds() / 3600)
        avg_rating = db.execute(
            "SELECT AVG(rating) a FROM complaints WHERE rating IS NOT NULL").fetchone()["a"]
        total = sum(by_status.values())
        return jsonify({
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "open_by_priority": open_by_priority,
            "avg_resolution_hours": round(sum(hours) / len(hours), 1) if hours else None,
            "avg_rating": round(avg_rating, 2) if avg_rating is not None else None,
            "resolution_rate": round(100 * by_status["Resolved"] / total, 1) if total else 0.0,
        })

    # -------------------------------------------------------------- errors
    @app.errorhandler(ApiError)
    def handle_api_error(e):
        return jsonify({"error": e.message}), e.status

    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        return jsonify({"error": e.description}), e.code

    # ------------------------------------------- optional: serve built UI
    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path):
        dist = os.path.abspath(app.config["FRONTEND_DIST"])
        if path.startswith("api/") or not os.path.isdir(dist):
            raise ApiError("Not found.", 404)
        target = os.path.abspath(os.path.join(dist, path))
        if path and target.startswith(dist + os.sep) and os.path.isfile(target):
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")

    # ----------------------------------------------------------------- CLI
    @app.cli.command("create-warden")
    def create_warden_cmd():
        """Create a warden account: flask --app app create-warden"""
        import getpass
        name = input("Name: ").strip()
        email = input("Email: ").strip().lower()
        pw = getpass.getpass("Password (min 8 chars): ")
        if len(pw) < 8:
            raise SystemExit("Password too short.")
        get_db().execute(
            "INSERT INTO users (name, email, password_hash, role, created_at)"
            " VALUES (?, ?, ?, 'warden', ?)", (name, email, generate_password_hash(pw), now_iso()))
        get_db().commit()
        print("Warden created.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("CAMPUSFIX_DEBUG") == "1")
