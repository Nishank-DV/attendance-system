from flask import Blueprint, render_template, session

from routes.auth import faculty_login_required


def create_dashboard_blueprint() -> Blueprint:
    bp = Blueprint("dashboard", __name__)

    @bp.get("/dashboard")
    @faculty_login_required
    def dashboard_page():
        return render_template(
            "dashboard.html",
            username=session.get("faculty_username", "Faculty"),
            is_admin=bool(session.get("faculty_is_admin")),
        )

    @bp.get("/attendance")
    @faculty_login_required
    def attendance_page():
        return render_template(
            "index.html",
            username=session.get("faculty_username", "Faculty"),
            is_admin=bool(session.get("faculty_is_admin")),
        )

    return bp
