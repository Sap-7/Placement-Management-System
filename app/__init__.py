import secrets
from flask import Flask, abort, request, session
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()  # available if you prefer bcrypt; passwords use werkzeug.security
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    from .auth.routes import bp as auth_bp
    from .admin.routes import bp as admin_bp
    from .student.routes import bp as student_bp
    from .company.routes import bp as company_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(company_bp, url_prefix="/company")

    # --- lightweight CSRF protection for every POST ---
    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            sent = request.form.get("_csrf", "")
            if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
                abort(400, "Invalid or missing CSRF token")

    @app.context_processor
    def inject_csrf():
        def csrf():
            session.setdefault("_csrf", secrets.token_hex(16))
            return Markup(f'<input type="hidden" name="_csrf" value="{session["_csrf"]}">')
        return {"csrf": csrf}

    with app.app_context():
        db.create_all()
        # Lightweight SQLite migration for users upgrading an existing demo database.
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        additions = {
            "student": {
                "is_placed": "BOOLEAN NOT NULL DEFAULT 0",
                "placed_company_name": "VARCHAR(120)",
                "placed_job_title": "VARCHAR(150)",
                "placed_at": "DATETIME",
                "placed_ctc": "FLOAT",
            },
            "application": {
                "status": "VARCHAR(30) NOT NULL DEFAULT 'Applied'",
                "oa_date": "DATETIME",
                "interview_date": "DATETIME",
                "decision_at": "DATETIME",
            },
        }
        for table, columns in additions.items():
            existing = {c["name"] for c in inspect(db.engine).get_columns(table)}
            for col, definition in columns.items():
                if col not in existing:
                    db.session.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {definition}'))
        db.session.commit()
        from .seed import seed
        seed()
    return app
