from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager


class PasswordMixin:
    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


class Admin(UserMixin, PasswordMixin, db.Model):
    __tablename__ = "admin"
    role = "admin"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def get_id(self):
        return f"admin:{self.id}"


class Course(db.Model):
    __tablename__ = "course"
    courseid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    streams = db.relationship("Stream", backref="course", lazy=True)


class Stream(db.Model):
    __tablename__ = "stream"
    deptid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    noofstudents = db.Column(db.Integer, default=0)
    courseid = db.Column(db.Integer, db.ForeignKey("course.courseid"), nullable=False)
    groups = db.relationship("StreamGroup", secondary="streamgroup_stream", back_populates="streams", lazy=True)


# Junction table: eligible streams <-> companies
streamcompany = db.Table(
    "streamcompany",
    db.Column("streamid", db.Integer, db.ForeignKey("stream.deptid"), primary_key=True),
    db.Column("companyid", db.Integer, db.ForeignKey("company.companyid"), primary_key=True),
)


streamgroup_stream = db.Table(
    "streamgroup_stream",
    db.Column("groupid", db.Integer, db.ForeignKey("streamgroup.groupid"), primary_key=True),
    db.Column("streamid", db.Integer, db.ForeignKey("stream.deptid"), primary_key=True),
)

companygroup_company = db.Table(
    "companygroup_company",
    db.Column("groupid", db.Integer, db.ForeignKey("companygroup.groupid"), primary_key=True),
    db.Column("companyid", db.Integer, db.ForeignKey("company.companyid"), primary_key=True),
)


class StreamGroup(db.Model):
    """A student eligibility group can contain multiple academic streams."""
    __tablename__ = "streamgroup"
    groupid = db.Column(db.Integer, primary_key=True)
    groupname = db.Column(db.String(100), unique=True, nullable=False)
    streams = db.relationship("Stream", secondary=streamgroup_stream, back_populates="groups")
    students = db.relationship("Student", backref="group", lazy=True)


class CompanyGroup(db.Model):
    """A company group contains one or more companies."""
    __tablename__ = "companygroup"
    groupid = db.Column(db.Integer, primary_key=True)
    groupname = db.Column(db.String(100), unique=True, nullable=False)
    companies = db.relationship("Company", secondary=companygroup_company, backref="company_groups")


class Student(UserMixin, PasswordMixin, db.Model):
    __tablename__ = "student"
    role = "student"
    roll = db.Column(db.String(30), primary_key=True)
    personalemail = db.Column(db.String(120), unique=True, nullable=False)
    collegeemail = db.Column(db.String(120), nullable=True)
    CGPA = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    marks_10 = db.Column("10marks", db.Float, nullable=False)
    marks_12 = db.Column("12marks", db.Float, nullable=True)
    diplomamarks = db.Column(db.Float, nullable=True)
    DOB = db.Column(db.Date, nullable=False)
    Gender = db.Column(db.String(20), nullable=False)
    mobileno = db.Column(db.String(20), nullable=False)
    streamid = db.Column(db.Integer, db.ForeignKey("stream.deptid"), nullable=False)
    courseid = db.Column(db.Integer, db.ForeignKey("course.courseid"), nullable=False)
    yearofgraduation = db.Column(db.Integer, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    # Extra (not in the base spec): which batch/group the admin placed the student in
    groupid = db.Column(db.Integer, db.ForeignKey("streamgroup.groupid"), nullable=True)

    stream = db.relationship("Stream", backref="students")
    course = db.relationship("Course")
    applications = db.relationship("Application", backref="student", cascade="all, delete-orphan")
    is_placed = db.Column(db.Boolean, default=False, nullable=False)
    placed_company_name = db.Column(db.String(120), nullable=True)
    placed_job_title = db.Column(db.String(150), nullable=True)
    placed_at = db.Column(db.DateTime, nullable=True)
    # Annual CTC in lakhs per annum (LPA), captured at placement confirmation.
    placed_ctc = db.Column(db.Float, nullable=True)
    notifications = db.relationship("Notification", backref="student", cascade="all, delete-orphan", order_by="Notification.created_at.desc()")

    def get_id(self):
        return f"student:{self.roll}"


class Company(UserMixin, PasswordMixin, db.Model):
    __tablename__ = "company"
    role = "company"
    companyid = db.Column(db.Integer, primary_key=True)
    companyname = db.Column(db.String(120), nullable=False)
    student_point_of_contact_roll = db.Column(db.String(30), db.ForeignKey("student.roll"), nullable=True)
    companymail = db.Column(db.String(120), unique=True, nullable=False)
    fulltimeCTCannual = db.Column(db.Float, nullable=True)
    sixmonthpaypermonth = db.Column("6monthpaypermonth", db.Float, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)

    poc = db.relationship("Student", foreign_keys=[student_point_of_contact_roll])
    streams = db.relationship("Stream", secondary=streamcompany, backref="companies")
    jobs = db.relationship("JobPosting", backref="company", cascade="all, delete-orphan")

    def get_id(self):
        return f"company:{self.companyid}"


class JobPosting(db.Model):
    __tablename__ = "job_posting"
    jobid = db.Column(db.Integer, primary_key=True)
    companyid = db.Column(db.Integer, db.ForeignKey("company.companyid"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    min_cgpa = db.Column(db.Float, default=0.0, nullable=False)  # extra: CGPA eligibility criterion
    applications = db.relationship("Application", backref="job", cascade="all, delete-orphan")

    @property
    def is_open(self):
        return self.deadline > datetime.now()


class Application(db.Model):
    __tablename__ = "application"
    __table_args__ = (db.UniqueConstraint("jobid", "roll", name="uq_job_student"),)
    applicationid = db.Column(db.Integer, primary_key=True)
    jobid = db.Column(db.Integer, db.ForeignKey("job_posting.jobid"), nullable=False)
    roll = db.Column(db.String(30), db.ForeignKey("student.roll"), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    status = db.Column(db.String(30), default="Applied", nullable=False)
    oa_date = db.Column(db.DateTime, nullable=True)
    interview_date = db.Column(db.DateTime, nullable=True)
    decision_at = db.Column(db.DateTime, nullable=True)


class Notification(db.Model):
    __tablename__ = "notification"
    id = db.Column(db.Integer, primary_key=True)
    roll = db.Column(db.String(30), db.ForeignKey("student.roll"), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)


@login_manager.user_loader
def load_user(user_id):
    try:
        kind, ident = user_id.split(":", 1)
    except ValueError:
        return None
    if kind == "admin":
        return db.session.get(Admin, int(ident))
    if kind == "student":
        s = db.session.get(Student, ident)
        return s if s and s.is_approved else None
    if kind == "company":
        return db.session.get(Company, int(ident))
    return None
