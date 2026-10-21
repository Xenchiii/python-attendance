import base64
import io
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import qrcode

import db
import security

try:
    import cv2
    import numpy
except ImportError:
    cv2 = None
    numpy = None

EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
LOCAL_TZ = ZoneInfo(os.environ.get("APP_TZ", "Asia/Manila"))
QR_LIFETIME_MINUTES = 5
SESSION_HOURS = 8


def local_time(value):
    if not value:
        return "-"
    parsed = datetime.strptime(db.iso(value)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return parsed.astimezone(LOCAL_TZ).strftime("%b %d, %Y %I:%M %p")


def today_local():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")


def day_range(date_text):
    try:
        start = datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return None
    end = start + timedelta(days=1)
    to_utc = lambda value: value.astimezone(timezone.utc).strftime(db.STAMP)
    return to_utc(start), to_utc(end)


def register(role, first, last, number, email, password):
    first, last, number = first.strip(), last.strip(), number.strip()
    email = email.strip().lower()
    if role not in ("teacher", "staff") or not first or not last or not number:
        return False, "Complete all fields"
    if not EMAIL.match(email):
        return False, "Enter a valid email address"
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    status = "ACTIVE" if role == "teacher" else "INACTIVE"
    try:
        db.execute(
            "INSERT INTO users (role, employee_no, first_name, last_name, email, password_hash, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            role, number, first, last, email, security.hash_password(password), status,
        )
    except db.IntegrityError:
        return False, "That email or ID number is already registered"
    if status == "ACTIVE":
        return True, "Registration successful. You can now log in."
    return True, "Registration successful. An administrator must approve your account before you can log in."


def login(role, email, password):
    user = db.one("SELECT * FROM users WHERE email = ? AND role = ?", email.strip().lower(), role)
    if user is None or not security.verify_password(password, user["password_hash"]):
        return None, "Incorrect email, password or role"
    if user["status"] == "INACTIVE":
        return None, "Your account is waiting for administrator approval"
    if user["status"] != "ACTIVE":
        return None, "Your account is suspended. Contact the administrator"
    token = security.new_token()
    expires = db.stamp(datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS))
    with db.tx() as t:
        t.run("INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)", security.sha256(token), user["id"], expires)
        t.run("UPDATE users SET last_login = ? WHERE id = ?", db.now(), user["id"])
    return token, None


def logout(token):
    if security.valid_sid(token):
        db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", security.sha256(token))


def user_for_token(token):
    if not security.valid_sid(token):
        return None
    return db.one(
        "SELECT u.id, u.role, u.employee_no, u.first_name, u.last_name, u.email FROM auth_sessions s "
        "JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ? AND u.status = 'ACTIVE'",
        security.sha256(token), db.now(),
    )


def rooms():
    return db.query("SELECT id, code, name, building, floor, capacity, status FROM rooms ORDER BY building, name")


def available_rooms():
    return [r for r in rooms() if r["status"] == "AVAILABLE"]


def add_room(code, name, building, floor, capacity):
    code, name, building = code.strip(), name.strip(), building.strip()
    if not code or not name or not building:
        return False, "Code, name and building are required"
    try:
        size = max(0, int(capacity or 0))
    except ValueError:
        size = 0
    try:
        db.execute(
            "INSERT INTO rooms (code, name, building, floor, capacity) VALUES (?, ?, ?, ?, ?)",
            code, name, building, floor.strip(), size,
        )
    except db.IntegrityError:
        return False, "That room code already exists"
    return True, "Room added"


def users():
    return db.query(
        "SELECT id, role, employee_no, first_name, last_name, email, status FROM users WHERE role <> 'admin' ORDER BY status, role, last_name"
    )


def set_status(user_id, status):
    if status not in ("ACTIVE", "INACTIVE", "SUSPENDED"):
        return False, "Invalid status"
    with db.tx() as t:
        t.run("UPDATE users SET status = ? WHERE id = ? AND role <> 'admin'", status, user_id)
        if status != "ACTIVE":
            t.run(
                "DELETE FROM auth_sessions WHERE user_id IN (SELECT id FROM users WHERE id = ? AND role <> 'admin')",
                user_id,
            )
    return True, "Account updated"


def stats():
    bounds = day_range(today_local())
    row = db.one(
        "SELECT (SELECT COUNT(*) FROM users WHERE role = 'teacher' AND status = 'ACTIVE') AS teachers, "
        "(SELECT COUNT(*) FROM users WHERE role = 'staff' AND status = 'ACTIVE') AS staff, "
        "(SELECT COUNT(*) FROM users WHERE status = 'INACTIVE') AS pending, "
        "(SELECT COUNT(*) FROM attendance WHERE status = 'ACTIVE') AS in_use, "
        "(SELECT COUNT(*) FROM attendance WHERE time_in >= ? AND time_in < ?) AS today",
        bounds[0], bounds[1],
    )
    return row


def generate_qr(teacher_id, room_id):
    room = db.one("SELECT id FROM rooms WHERE id = ? AND status = 'AVAILABLE'", room_id)
    if room is None:
        return None, "That room is not available"
    if db.one("SELECT id FROM attendance WHERE teacher_id = ? AND status = 'ACTIVE'", teacher_id):
        return None, "Time out of your current class before generating a new code"
    token = security.new_token()
    created = datetime.now(timezone.utc)
    expires = created + timedelta(minutes=QR_LIFETIME_MINUTES)
    with db.tx() as t:
        t.run("UPDATE qr_sessions SET status = 'CANCELLED' WHERE teacher_id = ? AND status = 'ACTIVE'", teacher_id)
        t.run(
            "INSERT INTO qr_sessions (teacher_id, room_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            teacher_id, room["id"], security.sha256(token), db.stamp(created), db.stamp(expires),
        )
    return {"token": token, "expires_at": expires.timestamp(), "room_id": room["id"]}, None


def qr_png(text):
    image = qrcode.make(text, box_size=8, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def decode_qr_image(data):
    if cv2 is None:
        return None
    array = numpy.frombuffer(data, dtype=numpy.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return None
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return text or None


def attendance(user, status="", date="", q=""):
    where = ["1 = 1"]
    args = []
    if user["role"] == "teacher":
        where.append("a.teacher_id = ?")
        args.append(user["id"])
    if status:
        where.append("a.status = ?")
        args.append(status)
    bounds = day_range(date) if date else None
    if bounds:
        where.append("a.time_in >= ? AND a.time_in < ?")
        args.extend(bounds)
    if q:
        where.append("(" + db.concat("t.first_name", "' '", "t.last_name") + " LIKE ? OR r.name LIKE ?)")
        args.extend(["%" + q + "%", "%" + q + "%"])
    sql = (
        "SELECT a.id, a.time_in, a.time_out, a.duration_minutes, a.status, "
        + db.concat("t.first_name", "' '", "t.last_name")
        + " AS teacher_name, r.name AS room_name FROM attendance a JOIN users t ON t.id = a.teacher_id "
        "JOIN rooms r ON r.id = a.room_id WHERE " + " AND ".join(where) + " ORDER BY a.time_in DESC LIMIT 500"
    )
    rows = db.query(sql, *args)
    for row in rows:
        row["time_in_text"] = local_time(row["time_in"])
        row["time_out_text"] = local_time(row["time_out"])
    return rows


def scan(token, staff_id):
    token = (token or "").strip()
    if not token:
        return False, "No QR code data received"
    session = db.one(
        "SELECT id, teacher_id, room_id, status, expires_at FROM qr_sessions WHERE token_hash = ?",
        security.sha256(token),
    )
    if session is None:
        return False, "This QR code is not recognised"
    if session["status"] != "ACTIVE":
        return False, "This QR code was already used or cancelled"
    if db.stamp(datetime.strptime(db.iso(session["expires_at"])[:19], "%Y-%m-%dT%H:%M:%S")) < db.now():
        db.execute("UPDATE qr_sessions SET status = 'EXPIRED' WHERE id = ?", session["id"])
        return False, "This QR code has expired. Ask the teacher to generate a new one"
    if db.one("SELECT id FROM attendance WHERE teacher_id = ? AND status = 'ACTIVE'", session["teacher_id"]):
        return False, "This teacher already has an active attendance record"
    room = db.one("SELECT name, status FROM rooms WHERE id = ?", session["room_id"])
    if room["status"] != "AVAILABLE":
        return False, room["name"] + " is not available"
    moment = db.now()
    try:
        with db.tx() as t:
            t.run(
                "INSERT INTO attendance (teacher_id, room_id, qr_session_id, scanned_by, time_in) VALUES (?, ?, ?, ?, ?)",
                session["teacher_id"], session["room_id"], session["id"], staff_id, moment,
            )
            t.run("UPDATE qr_sessions SET status = 'USED', used_at = ? WHERE id = ?", moment, session["id"])
            t.run("UPDATE rooms SET status = 'OCCUPIED' WHERE id = ?", session["room_id"])
    except db.IntegrityError:
        return False, "This teacher already has an active attendance record"
    teacher = db.one("SELECT first_name, last_name FROM users WHERE id = ?", session["teacher_id"])
    return True, "Time In recorded for " + teacher["first_name"] + " " + teacher["last_name"] + " in " + room["name"]


def time_out(teacher_id):
    open_row = db.one("SELECT id, room_id, time_in FROM attendance WHERE teacher_id = ? AND status = 'ACTIVE'", teacher_id)
    if open_row is None:
        return False, "You have no active attendance record"
    started = datetime.strptime(db.iso(open_row["time_in"])[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    minutes = max(1, round((datetime.now(timezone.utc) - started).total_seconds() / 60))
    with db.tx() as t:
        t.run(
            "UPDATE attendance SET time_out = ?, duration_minutes = ?, status = 'COMPLETED' WHERE id = ?",
            db.now(), minutes, open_row["id"],
        )
        t.run("UPDATE rooms SET status = 'AVAILABLE' WHERE id = ?", open_row["room_id"])
    return True, "Time Out recorded"
