import sqlite3

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, now_iso


@pytest.fixture()
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"),
                      "FRONTEND_DIST": str(tmp_path / "no-dist")})
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute(
        "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?,?,?,?,?)",
        ("Warden", "warden@t.test", generate_password_hash("Warden@123"), "warden", now_iso()))
    db.commit()
    db.close()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, email="stu@t.test", pw="Student@123", name="Stu", room="A-1"):
    return client.post("/api/auth/register", json={
        "name": name, "email": email, "room": room, "password": pw})


def login(client, email="stu@t.test", pw="Student@123"):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    return r, {"Authorization": f"Bearer {r.get_json().get('token', '')}"}


def student(client, email="stu@t.test"):
    register(client, email=email)
    return login(client, email)[1]


def warden(client):
    return login(client, "warden@t.test", "Warden@123")[1]


COMPLAINT = {"title": "Fan is making noise", "description": "The ceiling fan wobbles and grinds.",
             "category": "Electrical", "priority": "High", "room": "A-1"}


def file_complaint(client, h, **over):
    return client.post("/api/complaints", json={**COMPLAINT, **over}, headers=h)


def test_register_validation(client):
    assert register(client, pw="short").status_code == 400
    assert register(client, email="nope").status_code == 400
    assert register(client).status_code == 201
    assert register(client).status_code == 409


def test_login_and_me(client):
    register(client)
    r, h = login(client, pw="wrong")
    assert r.status_code == 401
    r, h = login(client)
    assert r.status_code == 200 and r.get_json()["user"]["role"] == "student"
    assert "password_hash" not in r.get_json()["user"]
    assert client.get("/api/auth/me", headers=h).get_json()["user"]["email"] == "stu@t.test"


def test_auth_required_and_bad_tokens(client):
    assert client.get("/api/complaints").status_code == 401
    bad = {"Authorization": "Bearer not.a.token"}
    assert client.get("/api/complaints", headers=bad).status_code == 401


def test_expired_token_rejected(client, app):
    import jwt
    from datetime import datetime, timedelta, timezone
    register(client)
    token = jwt.encode({"sub": "2", "role": "student",
                        "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                       app.config["SECRET_KEY"], algorithm="HS256")
    r = client.get("/api/complaints", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and "expired" in r.get_json()["error"].lower()


def test_forged_role_in_token_is_ignored(client, app):
    import jwt
    from datetime import datetime, timedelta, timezone
    register(client)
    # valid signature but claims warden; server must use the DB role (student)
    token = jwt.encode({"sub": "2", "role": "warden",
                        "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                       app.config["SECRET_KEY"], algorithm="HS256")
    r = client.get("/api/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_create_and_list_complaint(client):
    h = student(client)
    r = file_complaint(client, h)
    assert r.status_code == 201 and r.get_json()["complaint"]["status"] == "Open"
    rows = client.get("/api/complaints", headers=h).get_json()["complaints"]
    assert len(rows) == 1 and rows[0]["title"] == "Fan is making noise"


def test_complaint_validation(client):
    h = student(client)
    assert file_complaint(client, h, title="hey").status_code == 400
    assert file_complaint(client, h, description="short").status_code == 400
    assert file_complaint(client, h, category="Bogus").status_code == 400
    assert file_complaint(client, h, title=123).status_code == 400
    assert client.post("/api/complaints", data="notjson", headers=h).status_code == 400


def test_isolation_between_students(client):
    a = student(client, "a@t.test")
    file_complaint(client, a)
    b = student(client, "b@t.test")
    assert client.get("/api/complaints/1", headers=b).status_code == 403
    assert client.get("/api/complaints", headers=b).get_json()["complaints"] == []
    assert client.get("/api/stats", headers=b).status_code == 403


def test_warden_workflow_and_rating(client):
    s = student(client)
    file_complaint(client, s)
    assert client.post("/api/complaints/1/rating", json={"rating": 5}, headers=s).status_code == 400
    assert client.post("/api/complaints/1/status", json={"status": "Resolved"},
                       headers=s).status_code == 403
    w = warden(client)
    r = client.post("/api/complaints/1/status",
                    json={"status": "In Progress", "note": "Electrician called."}, headers=w)
    assert r.get_json()["complaint"]["status"] == "In Progress"
    r = client.post("/api/complaints/1/status", json={"status": "Resolved"}, headers=w)
    assert r.get_json()["complaint"]["resolved_at"]
    assert client.post("/api/complaints/1/status", json={"status": "Nope"}, headers=w).status_code == 400
    stats = client.get("/api/stats", headers=w).get_json()
    assert stats["by_status"]["Resolved"] == 1 and stats["resolution_rate"] == 100.0
    assert client.post("/api/complaints/1/rating", json={"rating": 9}, headers=s).status_code == 400
    assert client.post("/api/complaints/1/rating", json={"rating": True}, headers=s).status_code == 400
    assert client.post("/api/complaints/1/rating", json={"rating": 4}, headers=s).status_code == 200
    assert client.get("/api/stats", headers=w).get_json()["avg_rating"] == 4.0
    tl = client.get("/api/complaints/1", headers=s).get_json()["timeline"]
    assert [t["status_change"] for t in tl] == ["Open", "In Progress", "Resolved"]
    assert tl[1]["message"] == "Electrician called."


def test_reopening_clears_resolved_time(client):
    s = student(client)
    file_complaint(client, s)
    w = warden(client)
    client.post("/api/complaints/1/status", json={"status": "Resolved"}, headers=w)
    r = client.post("/api/complaints/1/status", json={"status": "Open"}, headers=w)
    assert r.get_json()["complaint"]["resolved_at"] is None


def test_warden_filters_and_priority_order(client):
    s = student(client)
    file_complaint(client, s, title="Tap leaking badly", priority="Low", category="Plumbing")
    file_complaint(client, s, title="Fan is making noise", priority="High")
    w = warden(client)
    rows = client.get("/api/complaints", headers=w).get_json()["complaints"]
    assert [r["priority"] for r in rows] == ["High", "Low"]
    rows = client.get("/api/complaints?q=Tap", headers=w).get_json()["complaints"]
    assert [r["title"] for r in rows] == ["Tap leaking badly"]
    assert client.get("/api/complaints?status=Resolved", headers=w).get_json()["complaints"] == []
    assert len(client.get("/api/complaints?category=Plumbing", headers=w).get_json()["complaints"]) == 1


def test_warden_cannot_file_complaints(client):
    assert file_complaint(client, warden(client)).status_code == 403


def test_comments(client):
    s = student(client)
    file_complaint(client, s)
    assert client.post("/api/complaints/1/comments", json={"message": "  "}, headers=s).status_code == 400
    assert client.post("/api/complaints/1/comments", json={"message": "Still broken"}, headers=s).status_code == 201
    tl = client.get("/api/complaints/1", headers=s).get_json()["timeline"]
    assert tl[-1]["message"] == "Still broken" and tl[-1]["name"] == "Stu"


def test_sql_injection_attempt_in_search(client):
    w = warden(client)
    r = client.get("/api/complaints?q=' OR 1=1 --", headers=w)
    assert r.status_code == 200 and r.get_json()["complaints"] == []


def test_not_found_is_json(client):
    s = student(client)
    r = client.get("/api/complaints/999", headers=s)
    assert r.status_code == 404 and "error" in r.get_json()
    assert client.get("/api/nothing").status_code == 404
    # wrong method on a POST-only route is rejected with a JSON error (never HTML)
    wrong = client.get("/api/auth/login")
    assert wrong.status_code in (404, 405) and "error" in wrong.get_json()


def test_meta_is_public(client):
    assert "Electrical" in client.get("/api/meta").get_json()["categories"]
