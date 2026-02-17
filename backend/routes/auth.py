from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

from faculty_db import FacultyDB


def faculty_login_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not session.get("faculty_logged_in"):
            return redirect(url_for("auth.faculty_page"))
        return handler(*args, **kwargs)

    return wrapper


def create_auth_blueprint(faculty_db: FacultyDB, reset_key: str) -> Blueprint:
    bp = Blueprint("auth", __name__)

    @bp.get("/faculty")
    def faculty_page():
        if session.get("faculty_logged_in"):
            return redirect(url_for("dashboard.dashboard_page"))
        return render_template("faculty.html", error=request.args.get("error"))

    @bp.route("/faculty/login", methods=["GET", "POST"])
    def faculty_login():
        if request.method == "GET":
            return redirect(url_for("auth.faculty_page"))

        username = str(request.form.get("username", "")).strip()
        password = str(request.form.get("password", "")).strip()

        if not faculty_db.verify_user(username, password):
            return render_template("faculty.html", error="Invalid credentials."), 401

        user = faculty_db.get_user(username)
        session["faculty_is_admin"] = bool(user.get("is_admin")) if user else False

        session["faculty_logged_in"] = True
        session["faculty_username"] = username
        return redirect(url_for("dashboard.dashboard_page"))

    @bp.route("/faculty/register", methods=["GET", "POST"])
    def faculty_register():
        if not session.get("faculty_logged_in"):
            return redirect(url_for("auth.faculty_page", error="Admin login required."))
        if not session.get("faculty_is_admin"):
            return redirect(url_for("auth.faculty_page", error="Admin access required."))
        if request.method == "GET":
            return render_template("faculty_register.html", error=None, success=None)

        username = str(request.form.get("username", "")).strip()
        password = str(request.form.get("password", "")).strip()
        confirm = str(request.form.get("confirm_password", "")).strip()

        if not username or not password:
            return render_template(
                "faculty_register.html",
                error="Username and password are required.",
                success=None,
            ), 400

        if password != confirm:
            return render_template(
                "faculty_register.html",
                error="Passwords do not match.",
                success=None,
            ), 400

        try:
            faculty_db.create_user(username=username, password=password, is_admin=False)
        except ValueError as exc:
            return render_template("faculty_register.html", error=str(exc), success=None), 409

        return render_template(
            "faculty_register.html",
            error=None,
            success="Account created. You can now log in.",
        )

    @bp.route("/faculty/forgot", methods=["GET", "POST"])
    def faculty_forgot():
        if request.method == "GET":
            return render_template("faculty_forgot.html", error=None, success=None)

        username = str(request.form.get("username", "")).strip()
        reset_code = str(request.form.get("reset_key", "")).strip()
        new_password = str(request.form.get("new_password", "")).strip()
        confirm = str(request.form.get("confirm_password", "")).strip()

        if reset_code != reset_key:
            return render_template("faculty_forgot.html", error="Invalid reset key.", success=None), 401

        if not username or not new_password:
            return render_template(
                "faculty_forgot.html",
                error="Username and new password are required.",
                success=None,
            ), 400

        if new_password != confirm:
            return render_template(
                "faculty_forgot.html",
                error="Passwords do not match.",
                success=None,
            ), 400

        try:
            faculty_db.update_password(username=username, new_password=new_password)
        except ValueError as exc:
            return render_template("faculty_forgot.html", error=str(exc), success=None), 404

        return render_template(
            "faculty_forgot.html",
            error=None,
            success="Password reset successfully. You can now log in.",
        )

    @bp.get("/faculty/logout")
    def faculty_logout():
        session.clear()
        return redirect(url_for("auth.faculty_page"))

    return bp
