from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from sqlalchemy import func
from statistics import mean, median
import csv
import io
from .. import db
from ..models import (Student, Company, Course, Stream, StreamGroup, CompanyGroup, JobPosting, Application)
from ..utils import role_required, fill_student, refresh_stream_counts

bp = Blueprint("admin", __name__)



@bp.route("/")
@role_required("admin")
def dashboard():
    stats = {
        "students": Student.query.filter_by(is_approved=True).count(),
        "pending": Student.query.filter_by(is_approved=False).count(),
        "companies": Company.query.count(),
        "jobs": JobPosting.query.count(),
        "applications": Application.query.count(),
        "applicants": db.session.query(func.count(func.distinct(Application.roll))).scalar(),
        "placed": Student.query.filter_by(is_placed=True).count(),
    }
    per_company = (db.session.query(Company.companyname, func.count(Application.applicationid))
                   .outerjoin(JobPosting, JobPosting.companyid == Company.companyid)
                   .outerjoin(Application, Application.jobid == JobPosting.jobid)
                   .group_by(Company.companyid).all())
    per_stream = (db.session.query(Stream.name, func.count(func.distinct(Application.roll)))
                  .outerjoin(Student, Student.streamid == Stream.deptid)
                  .outerjoin(Application, Application.roll == Student.roll)
                  .group_by(Stream.deptid).all())
    placed_students = Student.query.filter_by(is_placed=True).order_by(Student.placed_at.desc()).all()
    return render_template("admin/dashboard.html", stats=stats, per_company=per_company, per_stream=per_stream, placed_students=placed_students)


# ---------- students ----------
@bp.route("/students")
@role_required("admin")
def students():
    pending = Student.query.filter_by(is_approved=False).all()
    approved = Student.query.filter_by(is_approved=True).order_by(Student.roll).all()
    return render_template("admin/students.html", pending=pending, approved=approved)


@bp.route("/students/<roll>/<action>", methods=["POST"])
@role_required("admin")
def student_action(roll, action):
    s = db.get_or_404(Student, roll)
    if action == "approve":
        s.is_approved = True
        flash(f"{s.name} approved.", "success")
    elif action in ("reject", "delete"):
        db.session.delete(s)
        flash(f"{s.name} removed.", "info")
    db.session.commit()
    refresh_stream_counts()
    return redirect(url_for("admin.students"))


@bp.route("/students/new", methods=["GET", "POST"])
@bp.route("/students/<roll>/edit", methods=["GET", "POST"])
@role_required("admin")
def student_form(roll=None):
    s = db.get_or_404(Student, roll) if roll else None
    if request.method == "POST":
        f = request.form
        try:
            if not s:
                new_roll = f["roll"].strip()
                if db.session.get(Student, new_roll):
                    raise ValueError("Roll number already exists")
                s = Student(roll=new_roll, is_approved=True)  # admin-added => auto-approved
                if len(f.get("password", "")) < 6:
                    raise ValueError("Password must be at least 6 characters")
                s.set_password(f["password"])
                db.session.add(s)
            elif f.get("password"):
                s.set_password(f["password"])
            fill_student(s, f)
            s.groupid = int(f["groupid"]) if f.get("groupid") else None
            db.session.commit()
            refresh_stream_counts()
            flash("Student saved.", "success")
            return redirect(url_for("admin.students"))
        except (ValueError, KeyError) as e:
            db.session.rollback()
            flash(f"Could not save: {e}", "danger")
    return render_template("admin/student_form.html", s=s, streams=Stream.query.all(),
                           courses=Course.query.all(), groups=StreamGroup.query.all())


# ---------- courses & streams ----------
@bp.route("/courses", methods=["GET", "POST"])
@role_required("admin")
def courses():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name and not Course.query.filter_by(name=name).first():
            db.session.add(Course(name=name))
            db.session.commit()
            flash("Course added.", "success")
        else:
            flash("Course name is empty or already exists.", "danger")
        return redirect(url_for("admin.courses"))
    return render_template("admin/courses.html", courses=Course.query.all())


@bp.route("/courses/<int:cid>/delete", methods=["POST"])
@role_required("admin")
def course_delete(cid):
    c = db.get_or_404(Course, cid)
    if c.streams:
        flash("Remove this course's streams first.", "danger")
    else:
        db.session.delete(c)
        db.session.commit()
        flash("Course deleted.", "info")
    return redirect(url_for("admin.courses"))


@bp.route("/streams", methods=["GET", "POST"])
@role_required("admin")
def streams():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        cid = request.form.get("courseid", type=int)
        if name and cid and db.session.get(Course, cid):
            db.session.add(Stream(name=name, courseid=cid))
            db.session.commit()
            flash("Stream added.", "success")
        else:
            flash("Provide a name and a valid course.", "danger")
        return redirect(url_for("admin.streams"))
    return render_template("admin/streams.html", streams=Stream.query.all(), courses=Course.query.all())


@bp.route("/streams/<int:sid>/edit", methods=["POST"])
@role_required("admin")
def stream_edit(sid):
    st = db.get_or_404(Stream, sid)
    st.name = request.form.get("name", st.name).strip() or st.name
    db.session.commit()
    flash("Stream updated.", "success")
    return redirect(url_for("admin.streams"))


@bp.route("/streams/<int:sid>/delete", methods=["POST"])
@role_required("admin")
def stream_delete(sid):
    st = db.get_or_404(Stream, sid)
    if st.students or st.companies:
        flash("Stream still has students or companies attached.", "danger")
    else:
        db.session.delete(st)
        db.session.commit()
        flash("Stream deleted.", "info")
    return redirect(url_for("admin.streams"))


# ---------- groups (admin-exclusive) ----------
@bp.route("/groups", methods=["GET", "POST"])
@role_required("admin")
def groups():
    if request.method == "POST":
        kind = request.form.get("kind", "student")
        name = request.form.get("groupname", "").strip()
        ids = request.form.getlist("members", type=int)
        if not name:
            flash("Provide a group name.", "danger")
        elif kind == "student":
            if StreamGroup.query.filter_by(groupname=name).first():
                flash("Student group name already exists.", "danger")
            elif not ids or not all(db.session.get(Stream, i) for i in ids):
                flash("Select at least one valid stream.", "danger")
            else:
                db.session.add(StreamGroup(groupname=name, streams=[db.session.get(Stream, i) for i in ids]))
                db.session.commit()
                flash("Student stream group created.", "success")
        elif kind == "company":
            if CompanyGroup.query.filter_by(groupname=name).first():
                flash("Company group name already exists.", "danger")
            elif not ids or not all(db.session.get(Company, i) for i in ids):
                flash("Select at least one valid company.", "danger")
            else:
                db.session.add(CompanyGroup(groupname=name, companies=[db.session.get(Company, i) for i in ids]))
                db.session.commit()
                flash("Company group created.", "success")
        return redirect(url_for("admin.groups"))
    return render_template("admin/groups.html", groups=StreamGroup.query.all(),
                           company_groups=CompanyGroup.query.all(), streams=Stream.query.all(),
                           companies=Company.query.order_by(Company.companyname).all())


@bp.route("/groups/<int:gid>/delete", methods=["POST"])
@role_required("admin")
def group_delete(gid):
    g = db.get_or_404(StreamGroup, gid)
    for student in g.students:
        student.groupid = None
    db.session.delete(g)
    db.session.commit()
    flash("Student stream group deleted.", "info")
    return redirect(url_for("admin.groups"))


@bp.route("/company-groups/<int:gid>/delete", methods=["POST"])
@role_required("admin")
def company_group_delete(gid):
    g = db.get_or_404(CompanyGroup, gid)
    db.session.delete(g)
    db.session.commit()
    flash("Company group deleted.", "info")
    return redirect(url_for("admin.groups"))


# ---------- companies ----------
@bp.route("/companies")
@role_required("admin")
def companies():
    return render_template("admin/companies.html", companies=Company.query.all())


@bp.route("/companies/new", methods=["GET", "POST"])
@bp.route("/companies/<int:cid>/edit", methods=["GET", "POST"])
@role_required("admin")
def company_form(cid=None):
    c = db.get_or_404(Company, cid) if cid else None
    if request.method == "POST":
        f = request.form
        try:
            if not c:
                if len(f.get("password", "")) < 6:
                    raise ValueError("Password must be at least 6 characters")
                c = Company()
                c.set_password(f["password"])
                db.session.add(c)
            elif f.get("password"):
                c.set_password(f["password"])
            c.companyname = f["companyname"].strip()
            c.companymail = f["companymail"].strip().lower()
            dup = Company.query.filter_by(companymail=c.companymail).first()
            if dup and dup is not c:
                raise ValueError("Company email already in use")
            ctc, pay = f.get("fulltimeCTCannual", "").strip(), f.get("sixmonthpay", "").strip()
            c.fulltimeCTCannual = float(ctc) if ctc else None
            c.sixmonthpaypermonth = float(pay) if pay else None
            poc = f.get("poc", "").strip()
            if poc and not db.session.get(Student, poc):
                raise ValueError("Point-of-contact roll number not found")
            c.student_point_of_contact_roll = poc or None
            c.streams = [db.session.get(Stream, int(i)) for i in f.getlist("streams")]
            c.company_groups = [db.session.get(CompanyGroup, int(i)) for i in f.getlist("company_groups")
                                if db.session.get(CompanyGroup, int(i))]
            db.session.commit()
            flash("Company saved.", "success")
            return redirect(url_for("admin.companies"))
        except (ValueError, KeyError) as e:
            db.session.rollback()
            flash(f"Could not save: {e}", "danger")
    return render_template("admin/company_form.html", c=c, streams=Stream.query.all(),
                           company_groups=CompanyGroup.query.all(), students=Student.query.filter_by(is_approved=True).order_by(Student.name).all())


@bp.route("/companies/<int:cid>/delete", methods=["POST"])
@role_required("admin")
def company_delete(cid):
    company = db.get_or_404(Company, cid)
    if company.jobs:
        flash("This company has published immutable job postings and cannot be deleted.", "danger")
    else:
        db.session.delete(company)
        db.session.commit()
        flash("Company deleted.", "info")
    return redirect(url_for("admin.companies"))


# ---------- application log ----------
@bp.route("/applications")
@role_required("admin")
def applications():
    apps = Application.query.order_by(Application.applied_at.desc()).all()
    return render_template("admin/applications.html", apps=apps)


@bp.route("/placed")
@role_required("admin")
def placed():
    students = Student.query.filter_by(is_placed=True).order_by(Student.placed_at.desc()).all()
    return render_template("admin/placed.html", students=students)


# ---------- placement analytics ----------
def _placement_report_data():
    approved = Student.query.filter_by(is_approved=True).all()
    placed = [s for s in approved if s.is_placed]
    ctc_values = [float(s.placed_ctc) for s in placed if s.placed_ctc is not None and s.placed_ctc > 0]

    def metrics(students):
        total = len(students)
        placed_rows = [s for s in students if s.is_placed]
        values = [float(s.placed_ctc) for s in placed_rows if s.placed_ctc is not None and s.placed_ctc > 0]
        return {
            "total": total,
            "placed": len(placed_rows),
            "percentage": round(len(placed_rows) * 100 / total, 2) if total else 0.0,
            "average_ctc": round(mean(values), 2) if values else None,
            "median_ctc": round(median(values), 2) if values else None,
            "ctc_count": len(values),
        }

    group_rows = []
    groups = StreamGroup.query.order_by(StreamGroup.groupname).all()
    grouped_rolls = set()
    for group in groups:
        # Groups define stream eligibility, so membership is derived from the
        # group's streams (not the optional single groupid stored on a student).
        stream_ids = {stream.deptid for stream in group.streams}
        members = [s for s in approved if s.streamid in stream_ids]
        grouped_rolls.update(s.roll for s in members)
        group_rows.append({"name": group.groupname, **metrics(members)})
    unassigned = [s for s in approved if s.roll not in grouped_rolls]
    if unassigned:
        group_rows.append({"name": "Unassigned", **metrics(unassigned)})

    stream_rows = []
    for stream in Stream.query.order_by(Stream.name).all():
        members = [s for s in approved if s.streamid == stream.deptid]
        stream_rows.append({"name": stream.name, **metrics(members)})

    company_rows = []
    all_company_names = {c.companyname for c in Company.query.order_by(Company.companyname).all()}
    all_company_names.update(s.placed_company_name for s in placed if s.placed_company_name)
    for name in sorted(all_company_names):
        company_students = [s for s in placed if s.placed_company_name == name]
        values = [float(s.placed_ctc) for s in company_students if s.placed_ctc is not None and s.placed_ctc > 0]
        company_rows.append({
            "name": name,
            "placed": len(company_students),
            "share": round(len(company_students) * 100 / len(placed), 2) if placed else 0.0,
            "average_ctc": round(mean(values), 2) if values else None,
            "median_ctc": round(median(values), 2) if values else None,
            "ctc_count": len(values),
        })
    company_rows.sort(key=lambda row: (-row["placed"], row["name"].casefold()))
    return {
        "approved_count": len(approved),
        "placed_count": len(placed),
        "placement_percentage": round(len(placed) * 100 / len(approved), 2) if approved else 0.0,
        "unplaced_count": len(approved) - len(placed),
        "average_ctc": round(mean(ctc_values), 2) if ctc_values else None,
        "median_ctc": round(median(ctc_values), 2) if ctc_values else None,
        "ctc_count": len(ctc_values),
        "group_rows": group_rows,
        "stream_rows": stream_rows,
        "company_rows": company_rows,
    }


@bp.route("/reports")
@role_required("admin")
def reports():
    report = _placement_report_data()
    return render_template("admin/reports.html", report=report, placed_students=Student.query.filter_by(is_approved=True, is_placed=True).order_by(Student.name).all())


@bp.route("/reports/export.csv")
@role_required("admin")
def reports_export():
    report = _placement_report_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Name", "Approved students", "Placed students", "Placement %", "Share of placements %", "Average CTC (LPA)", "Median CTC (LPA)", "Students with CTC data"])
    writer.writerow(["Overall", "All approved students", report["approved_count"], report["placed_count"], report["placement_percentage"], 100.0 if report["placed_count"] else 0.0, report["average_ctc"], report["median_ctc"], report["ctc_count"]])
    for category, rows in (("Group", report["group_rows"]), ("Stream", report["stream_rows"])):
        for row in rows:
            writer.writerow([category, row["name"], row["total"], row["placed"], row["percentage"], "", row["average_ctc"], row["median_ctc"], row["ctc_count"]])
    for row in report["company_rows"]:
        writer.writerow(["Company", row["name"], "", row["placed"], "", row["share"], row["average_ctc"], row["median_ctc"], row["ctc_count"]])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=placement_report.csv"})
