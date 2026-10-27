import csv
import io
import os
import time

from flask import Flask, Response, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from functools import wraps

import db
import services

COOKIE_NAME = "sid"
SESSION_SECONDS = services.SESSION_HOURS * 3600
HOMES = {"teacher": "teacher", "staff": "staff", "admin": "admin"}


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE") == "true"
    app.jinja_env.filters["pretty"] = lambda value: str(value).lower()

    def load_user():
        g.user = services.user_for_token(request.cookies.get(COOKIE_NAME))

    app.before_request(load_user)

    def secured(*roles):
        def decorator(view):
            @wraps(view)
            def wrapper(*args, **kwargs):
                if g.user is None:
                    return redirect(url_for("index"))
                if roles and g.user["role"] not in roles:
                    flash("You do not have access to that page", "bad")
                    return redirect(url_for(HOMES[g.user["role"]]))
                return view(*args, **kwargs)
            return wrapper
        return decorator

    def notify(result):
        ok, message = result
        flash(message, "ok" if ok else "bad")
        return ok

    @app.errorhandler(Exception)
    def failure(error):
        if hasattr(error, "code") and hasattr(error, "get_response"):
            return error
        app.logger.exception(error)
        return Response("Something went wrong on the server", status=500)

    @app.get("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")

    @app.get("/")
    def index():
        if g.user:
            return redirect(url_for(HOMES[g.user["role"]]))
        mode = "signup" if request.args.get("mode") == "signup" else "login"
        return render_template("login.html", mode=mode)

    @app.post("/login")
    def login():
        role = request.form.get("role", "")
        token, error = services.login(role, request.form.get("email", ""), request.form.get("password", ""))
        if error:
            flash(error, "bad")
            return redirect(url_for("index"))
        response = redirect(url_for(HOMES[role]))
        response.set_cookie(
            COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True, samesite="Strict",
            secure=app.config["SESSION_COOKIE_SECURE"],
        )
        return response

    @app.post("/register")
    def register():
        form = request.form
        ok, message = services.register(
            form.get("role", ""), form.get("first_name", ""), form.get("last_name", ""),
            form.get("employee_no", ""), form.get("email", ""), form.get("password", ""),
        )
        flash(message, "ok" if ok else "bad")
        return redirect(url_for("index", mode="login" if ok else "signup"))

    @app.post("/logout")
    def logout():
        services.logout(request.cookies.get(COOKIE_NAME))
        session.clear()
        response = redirect(url_for("index"))
        response.delete_cookie(COOKIE_NAME)
        return response

    def filters():
        return {
            "q": request.args.get("q", "").strip(),
            "status": request.args.get("status", ""),
            "date": request.args.get("date", ""),
        }

    @app.get("/teacher")
    @secured("teacher")
    def teacher():
        active = db.one("SELECT id FROM attendance WHERE teacher_id = ? AND status = 'ACTIVE'", g.user["id"])
        pending = session.get("qr")
        qr = None
        if pending and not active and pending["expires_at"] > time.time():
            qr = {
                "image": services.qr_png(pending["token"]),
                "token": pending["token"],
                "seconds": int(pending["expires_at"] - time.time()),
            }
        else:
            session.pop("qr", None)
        return render_template(
            "teacher.html",
            rooms=services.available_rooms(),
            history=services.attendance(g.user),
            qr=qr,
            active=active is not None,
        )

    @app.post("/teacher/qr")
    @secured("teacher")
    def teacher_qr():
        data, error = services.generate_qr(g.user["id"], request.form.get("room_id", ""))
        if error:
            flash(error, "bad")
        else:
            session["qr"] = {"token": data["token"], "expires_at": data["expires_at"]}
        return redirect(url_for("teacher"))

    @app.post("/teacher/timeout")
    @secured("teacher")
    def teacher_timeout():
        notify(services.time_out(g.user["id"]))
        return redirect(url_for("teacher"))

    @app.get("/staff")
    @secured("staff")
    def staff():
        return render_template(
            "staff.html",
            in_use=services.attendance(g.user, status="ACTIVE"),
            history=services.attendance(g.user, **filters()),
            filters=filters(),
            scanner=services.cv2 is not None,
        )

    @app.post("/staff/scan")
    @secured("staff")
    def staff_scan():
        notify(services.scan(request.form.get("token", ""), g.user["id"]))
        return redirect(url_for("staff"))

    @app.post("/staff/scan-image")
    @secured("staff")
    def staff_scan_image():
        upload = request.files.get("photo")
        text = services.decode_qr_image(upload.read()) if upload and upload.filename else None
        if text is None:
            flash("No QR code could be read from that image. Try a sharper photo or type the code.", "bad")
        else:
            notify(services.scan(text, g.user["id"]))
        return redirect(url_for("staff"))

    @app.get("/admin")
    @secured("admin")
    def admin():
        return render_template(
            "admin.html",
            stats=services.stats(),
            users=services.users(),
            rooms=services.rooms(),
            history=services.attendance(g.user, **filters()),
            filters=filters(),
        )

    @app.post("/admin/users/<int:user_id>/status")
    @secured("admin")
    def admin_status(user_id):
        notify(services.set_status(user_id, request.form.get("status", "")))
        return redirect(url_for("admin"))

    @app.post("/admin/rooms")
    @secured("admin")
    def admin_room():
        form = request.form
        notify(services.add_room(
            form.get("code", ""), form.get("name", ""), form.get("building", ""),
            form.get("floor", ""), form.get("capacity", ""),
        ))
        return redirect(url_for("admin"))

    @app.get("/report.csv")
    @secured("admin", "staff")
    def report():
        rows = services.attendance(g.user, **filters())
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Teacher", "Room", "Time in", "Time out", "Duration (min)", "Status"])
        for row in rows:
            writer.writerow([
                row["teacher_name"], row["room_name"], row["time_in_text"], row["time_out_text"],
                row["duration_minutes"] if row["duration_minutes"] is not None else "", row["status"],
            ])
        return Response(
            buffer.getvalue(), mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=attendance-report.csv"},
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
