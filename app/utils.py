from datetime import datetime
from functools import wraps
from flask import abort
from flask_login import current_user, login_required
from . import db
from .models import Stream, Student


def role_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            if getattr(current_user, "role", None) != role:
                abort(403)
            return fn(*a, **k)
        return login_required(wrapper)
    return deco


def num(v):
    v = (v or "").strip()
    return float(v) if v else None


def parse_dt(v):
    return datetime.strptime(v, "%Y-%m-%dT%H:%M")


def refresh_stream_counts():
    for st in Stream.query.all():
        st.noofstudents = Student.query.filter_by(streamid=st.deptid, is_approved=True).count()
    db.session.commit()


def fill_student(s, f):
    """Populate a Student from a form. Raises ValueError/KeyError on bad input."""
    s.name = f["name"].strip()
    s.personalemail = f["personalemail"].strip().lower()
    s.collegeemail = f.get("collegeemail", "").strip().lower() or None
    s.CGPA = float(f["CGPA"])
    if not 0 <= s.CGPA <= 10:
        raise ValueError("CGPA must be between 0 and 10")
    s.marks_10 = float(f["marks_10"])
    s.marks_12 = num(f.get("marks_12"))
    s.diplomamarks = num(f.get("diplomamarks"))
    s.DOB = datetime.strptime(f["DOB"], "%Y-%m-%d").date()
    s.Gender = f["Gender"]
    s.mobileno = f["mobileno"].strip()
    s.streamid = int(f["streamid"])
    s.courseid = int(f["courseid"])
    s.yearofgraduation = int(f["yearofgraduation"])
    stream = db.session.get(Stream, s.streamid)
    if not stream or stream.courseid != s.courseid:
        raise ValueError("Selected stream does not belong to the selected course")
