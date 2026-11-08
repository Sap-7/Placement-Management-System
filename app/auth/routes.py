from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import or_
from .. import db
from ..models import Admin, Student, Company, Course, Stream
from ..utils import fill_student

bp = Blueprint("auth", __name__)


def home_for(user):
    return url_for({"admin": "admin.dashboard", "student": "student.dashboard",
                    "company": "company.dashboard"}[user.role])


@bp.route("/")
def index():
    return redirect(home_for(current_user)) if current_user.is_authenticated else redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(home_for(current_user))
    if request.method == "POST":
        role = request.form.get("role")
        ident = request.form.get("identifier", "").strip()
        pw = request.form.get("password", "")
        user = None
        if role == "admin":
            user = Admin.query.filter_by(username=ident).first()
        elif role == "student":
            user = Student.query.filter(or_(Student.roll == ident, Student.personalemail == ident.lower(),
                                            Student.collegeemail == ident.lower())).first()
        elif role == "company":
            user = Company.query.filter_by(companymail=ident.lower()).first()
        if user and user.check_password(pw):
            if role == "student" and not user.is_approved:
                flash("Your registration is still pending admin approval.", "warning")
                return render_template("auth/login.html")
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(home_for(user))
        flash("Invalid credentials.", "danger")
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        try:
            roll = f["roll"].strip()
            if len(f.get("password", "")) < 6:
                raise ValueError("Password must be at least 6 characters")
            if db.session.get(Student, roll):
                raise ValueError("Roll number already registered")
            s = Student(roll=roll, is_approved=False)
            fill_student(s, f)
            if Student.query.filter_by(personalemail=s.personalemail).first():
                raise ValueError("Email already registered")
            s.set_password(f["password"])
            db.session.add(s)
            db.session.commit()
            flash("Registered! You can log in once an admin approves your account.", "success")
            return redirect(url_for("auth.login"))
        except (ValueError, KeyError) as e:
            db.session.rollback()
            flash(f"Could not register: {e}", "danger")
    return render_template("auth/register.html", streams=Stream.query.all(), courses=Course.query.all(), s=None)
