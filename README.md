# University Placement Portal (Flask + SQLite)

## Run locally

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Demo credentials

- Admin: `admin` / `admin123`
- Students: use the student's roll number and password `student123`
- Companies: use the company's placement email and password `company123`

Company emails are demo placeholders under `.example.in`, not real contact addresses.

## Included sample data

The bundled `instance/placement.db` includes 120 students (the original 50 plus the 70 unique names from the supplied lists), 20 companies, 40 sample jobs, stream groups, company groups, and 25 seeded demo placements with annual CTC values. The demo placement cohort is seeded once on a fresh database; it does not overwrite existing placement decisions. Additional supplied student names are assigned across Computer Science, Electronics & Telecommunication, Electrical, Mechanical, Civil, and Information Technology. Passwords are demo-only.

## Workflow updates

- Admin dashboard and **Placed Students** page list every placed student, their company, role, annual CTC (LPA), and placement timestamp.
- Admin **Placement Reports** includes overall placement percentage, average and median annual CTC, group-wise and stream-wise placement rates/CTC statistics, company-wise placement share/CTC statistics, and CSV export.
- Company applicant dashboard shows student profile/academic/contact details, current placement status, application status, and OA/interview schedules.
- Companies can shortlist and schedule OA/interviews, directly reject, or approve a student as placed.
- Rejection and placement are terminal decisions. The server rejects attempts to change a terminal application.
- Marking a student placed locks further applications and changes their other in-process applications to **Withdrawn**, with student notifications.
- Students see placement state and application outcomes/schedules under **My Applications** and receive persistent Bootstrap toast notifications for status updates.
- Application eligibility and placement lock are enforced server-side, not only in the UI.
- Published jobs remain immutable. New deadlines and OA/interview schedule times are validated against the current time.
- Student groups contain streams; company groups contain companies.
- Startup includes a small SQLite migration for the added placement/application columns, so an existing demo database can be upgraded without manually deleting it.

## Important

This is demo software. Before production use, add robust password reset and account management, audit logging, stronger authorization review, secure production configuration, and a formal database migration tool such as Flask-Migrate/Alembic. Do not use the sample credentials in production.
