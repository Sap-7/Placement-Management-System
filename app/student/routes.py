from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import JobPosting, Application, Company, Notification
from ..utils import role_required, num

bp = Blueprint("student", __name__)


def eligible_jobs(student):
    return (JobPosting.query.join(Company)
            .filter(Company.streams.any(deptid=student.streamid), JobPosting.min_cgpa <= student.CGPA)
            .order_by(JobPosting.deadline).all())


@bp.route("/")
@role_required("student")
def dashboard():
    jobs = eligible_jobs(current_user)
    applied = {a.jobid for a in current_user.applications}
    return render_template("student/dashboard.html", jobs=jobs, applied=applied, now=datetime.now())


@bp.route("/apply/<int:jobid>", methods=["POST"])
@role_required("student")
def apply(jobid):
    job = db.get_or_404(JobPosting, jobid)
    if current_user.is_placed:
        flash(f"You are already placed at {current_user.placed_company_name}; further applications are disabled.", "warning")
    elif job not in eligible_jobs(current_user):
        flash("You are not eligible for this posting.", "danger")
    elif not job.is_open:
        flash("The application deadline has passed.", "danger")
    else:
        try:
            db.session.add(Application(jobid=jobid, roll=current_user.roll))
            db.session.commit()
            flash(f"Applied to {job.title} at {job.company.companyname}.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("You have already applied to this job.", "warning")
    return redirect(url_for("student.dashboard"))


@bp.route("/applications")
@role_required("student")
def my_applications():
    apps = sorted(current_user.applications, key=lambda a: a.applied_at, reverse=True)
    return render_template("student/applications.html", apps=apps)


@bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@role_required("student")
def notification_read(notification_id):
    n = db.get_or_404(Notification, notification_id)
    if n.roll != current_user.roll:
        from flask import abort
        abort(403)
    if not n.read_at:
        n.read_at = datetime.now(); db.session.commit()
    return ("", 204)


@bp.route("/profile", methods=["GET", "POST"])
@role_required("student")
def profile():
    if request.method == "POST":
        f, s = request.form, current_user
        try:
            s.name = f["name"].strip()
            s.personalemail = f["personalemail"].strip().lower()
            s.collegeemail = f.get("collegeemail", "").strip().lower() or None
            s.mobileno = f["mobileno"].strip()
            s.marks_10 = float(f["marks_10"])
            s.marks_12 = num(f.get("marks_12"))
            s.diplomamarks = num(f.get("diplomamarks"))
            if f.get("password"):
                if len(f["password"]) < 6:
                    raise ValueError("Password must be at least 6 characters")
                s.set_password(f["password"])
            db.session.commit()
            flash("Profile updated.", "success")
        except (ValueError, KeyError) as e:
            db.session.rollback()
            flash(f"Could not update: {e}", "danger")
        except IntegrityError:
            db.session.rollback()
            flash("That email is already in use.", "danger")
        return redirect(url_for("student.profile"))
    return render_template("student/profile.html")
