from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from datetime import datetime
from math import isfinite
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import JobPosting, Application, Student, Notification
from ..utils import role_required, parse_dt

bp = Blueprint("company", __name__)

@bp.route("/")
@role_required("company")
def dashboard():
    jobs = sorted(current_user.jobs, key=lambda j: j.deadline, reverse=True)
    return render_template("company/dashboard.html", jobs=jobs)

@bp.route("/jobs/new", methods=["GET", "POST"])
@role_required("company")
def post_job():
    if request.method == "POST":
        f = request.form
        try:
            deadline = parse_dt(f["deadline"]); min_cgpa = float(f.get("min_cgpa") or 0)
            if deadline <= datetime.now(): raise ValueError("Deadline must be a future date and time.")
            if not 0 <= min_cgpa <= 10: raise ValueError("Minimum CGPA must be between 0 and 10.")
            if not f["title"].strip() or not f["description"].strip(): raise ValueError("Title and description are required")
            db.session.add(JobPosting(companyid=current_user.companyid,title=f["title"].strip(),description=f["description"].strip(),deadline=deadline,min_cgpa=min_cgpa))
            db.session.commit(); flash("Job posted. Published postings are immutable.", "success")
            return redirect(url_for("company.dashboard"))
        except (ValueError, KeyError) as e: flash(f"Invalid input: {e}", "danger")
    return render_template("company/post_job.html", min_deadline=datetime.now().strftime("%Y-%m-%dT%H:%M"))

@bp.route("/applicants")
@role_required("company")
def applicants():
    jobs = sorted(current_user.jobs, key=lambda j: j.deadline, reverse=True)
    return render_template("company/applicants.html", jobs=jobs, now=datetime.now())

@bp.route("/applications/<int:application_id>/update", methods=["POST"])
@role_required("company")
def update_application(application_id):
    app = db.get_or_404(Application, application_id)
    if app.job.companyid != current_user.companyid: abort(403)
    if app.status in ("Placed", "Rejected", "Withdrawn"):
        flash("This application has a final outcome and cannot be changed.", "warning")
        return redirect(url_for("company.applicants"))
    student = app.student
    if student.is_placed and app.status != "Placed":
        app.status = "Withdrawn"
        db.session.commit()
        flash("This student is already placed; no further action is allowed.", "warning")
        return redirect(url_for("company.applicants"))
    action = request.form.get("action")
    if action == "shortlist":
        try:
            oa = request.form.get("oa_date", "").strip()
            interview = request.form.get("interview_date", "").strip()
            app.oa_date = parse_dt(oa) if oa else None
            app.interview_date = parse_dt(interview) if interview else None
            if app.oa_date and app.oa_date < datetime.now(): raise ValueError("OA date/time cannot be in the past.")
            if app.interview_date and app.interview_date < datetime.now(): raise ValueError("Interview date/time cannot be in the past.")
            app.status = "Shortlisted"
            db.session.add(Notification(roll=student.roll,message=f"You have been shortlisted by {current_user.companyname} for {app.job.title}. Check your OA/interview schedule."))
            flash("Student shortlisted; schedule and notification saved.", "success")
        except ValueError as e:
            flash(str(e), "danger"); return redirect(url_for("company.applicants"))
    elif action == "reject":
        app.status = "Rejected"; app.decision_at = datetime.now()
        db.session.add(Notification(roll=student.roll,message=f"Your application for {app.job.title} at {current_user.companyname} was rejected. This decision is final."))
        flash("Application rejected. This final decision cannot be changed.", "info")
    elif action == "approve":
        # CTC is stored in LPA so placement analytics use a consistent unit.
        raw_ctc = request.form.get("placed_ctc", "").strip()
        try:
            ctc = float(raw_ctc) if raw_ctc else current_user.fulltimeCTCannual
            if ctc is None or not isfinite(ctc) or ctc <= 0 or ctc > 1000:
                raise ValueError("Enter a valid annual CTC in LPA (greater than 0 and at most 1000).")
        except ValueError as e:
            flash(str(e) or "Enter a valid annual CTC in LPA.", "danger")
            return redirect(url_for("company.applicants"))
        app.status = "Placed"; app.decision_at = datetime.now()
        student.is_placed = True; student.placed_company_name = current_user.companyname
        student.placed_job_title = app.job.title; student.placed_at = datetime.now()
        student.placed_ctc = round(ctc, 2)
        db.session.add(Notification(roll=student.roll,message=f"Congratulations! You are placed at {current_user.companyname} for {app.job.title}. All other applications are now closed."))
        for other in student.applications:
            if other.applicationid != app.applicationid and other.status not in ("Rejected", "Placed", "Withdrawn"):
                other.status = "Withdrawn"
                db.session.add(Notification(roll=student.roll,message=f"Your application for {other.job.title} at {other.job.company.companyname} was closed because you have been placed."))
        flash("Student marked as placed. All other active applications have been withdrawn.", "success")
    else:
        flash("Choose a valid action.", "danger"); return redirect(url_for("company.applicants"))
    db.session.commit()
    return redirect(url_for("company.applicants"))
