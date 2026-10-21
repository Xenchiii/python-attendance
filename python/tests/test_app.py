import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy
import qrcode

import db
import seed
import services
from accounts import ACCOUNTS


@pytest.fixture()
def client(tmp_path):
    db.configure(backend="sqlite", sqlite_path=str(tmp_path / "test.db"))
    seed.ensure_schema(True)
    seed.seed_accounts()
    import app as app_module
    app = app_module.create_app()
    app.config["TESTING"] = True
    return app.test_client(), app


def sign_in(client, role):
    account = next(a for a in ACCOUNTS if a["role"] == role)
    return client.post("/login", data={"role": role, "email": account["email"], "password": account["password"]})


def test_seeded_accounts_can_log_in(client):
    c, _ = client
    for role in ("admin", "teacher", "staff"):
        response = sign_in(c, role)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/" + role)
        c.post("/logout")


def test_wrong_password_is_rejected(client):
    c, _ = client
    response = c.post("/login", data={"role": "teacher", "email": "teacher@attendance.ph", "password": "nope"}, follow_redirects=True)
    assert b"Incorrect email, password or role" in response.data


def test_signup_rules(client):
    c, _ = client
    c.post("/register", data={"role": "staff", "first_name": "A", "last_name": "B", "employee_no": "X1", "email": "a@b.ph", "password": "longenough"})
    response = c.post("/login", data={"role": "staff", "email": "a@b.ph", "password": "longenough"}, follow_redirects=True)
    assert b"waiting for administrator approval" in response.data
    short = c.post("/register", data={"role": "teacher", "first_name": "A", "last_name": "B", "employee_no": "X2", "email": "c@d.ph", "password": "short"}, follow_redirects=True)
    assert b"at least 8 characters" in short.data


def test_full_attendance_flow(client):
    c, app = client
    teacher = app.test_client()
    staff = app.test_client()
    sign_in(teacher, "teacher")
    sign_in(staff, "staff")

    room = db.one("SELECT id FROM rooms WHERE code = 'RM-101'")
    teacher.post("/teacher/qr", data={"room_id": room["id"]})
    page = teacher.get("/teacher")
    assert b"data:image/png;base64" in page.data

    with teacher.session_transaction() as s:
        token = s["qr"]["token"]

    image = qrcode.make(token).convert("RGB")
    encoded = cv2.imencode(".png", numpy.array(image)[:, :, ::-1])[1].tobytes()
    assert services.decode_qr_image(encoded) == token

    first = staff.post("/staff/scan", data={"token": token}, follow_redirects=True)
    assert b"Time In recorded for Juan Dela Cruz in Room 101" in first.data
    replay = staff.post("/staff/scan", data={"token": token}, follow_redirects=True)
    assert b"already used or cancelled" in replay.data

    assert db.one("SELECT status FROM rooms WHERE id = ?", room["id"])["status"] == "OCCUPIED"
    assert b"Room 101" in staff.get("/staff").data

    done = teacher.post("/teacher/timeout", follow_redirects=True)
    assert b"Time Out recorded" in done.data
    assert db.one("SELECT status FROM rooms WHERE id = ?", room["id"])["status"] == "AVAILABLE"
    row = db.one("SELECT status, duration_minutes FROM attendance")
    assert row["status"] == "COMPLETED" and row["duration_minutes"] >= 1


def test_expired_code_is_refused(client):
    c, app = client
    teacher = app.test_client()
    staff = app.test_client()
    sign_in(teacher, "teacher")
    sign_in(staff, "staff")
    room = db.one("SELECT id FROM rooms WHERE code = 'RM-102'")
    data, _ = services.generate_qr(db.one("SELECT id FROM users WHERE role = 'teacher'")["id"], room["id"])
    db.execute("UPDATE qr_sessions SET expires_at = '2000-01-01 00:00:00'")
    response = staff.post("/staff/scan", data={"token": data["token"]}, follow_redirects=True)
    assert b"has expired" in response.data


def test_roles_are_enforced(client):
    c, app = client
    teacher = app.test_client()
    sign_in(teacher, "teacher")
    assert teacher.get("/admin").status_code == 302
    assert teacher.post("/staff/scan", data={"token": "x"}).status_code == 302
    anonymous = app.test_client()
    assert anonymous.get("/teacher").status_code == 302


def test_admin_approves_and_suspends(client):
    c, app = client
    c.post("/register", data={"role": "staff", "first_name": "New", "last_name": "Staff", "employee_no": "S9", "email": "new@x.ph", "password": "longenough"})
    admin = app.test_client()
    sign_in(admin, "admin")
    user = db.one("SELECT id FROM users WHERE email = 'new@x.ph'")
    admin.post("/admin/users/%d/status" % user["id"], data={"status": "ACTIVE"})
    assert db.one("SELECT status FROM users WHERE id = ?", user["id"])["status"] == "ACTIVE"
    admin.post("/admin/rooms", data={"code": "RM-9", "name": "Room 9", "building": "Annex", "floor": "1", "capacity": "20"})
    assert db.one("SELECT id FROM rooms WHERE code = 'RM-9'")
    dup = admin.post("/admin/rooms", data={"code": "RM-9", "name": "Room 9", "building": "Annex"}, follow_redirects=True)
    assert b"already exists" in dup.data
    csv_response = admin.get("/report.csv")
    assert csv_response.mimetype == "text/csv"
    assert admin.get("/admin").status_code == 200
