import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    # PostgreSQL example: postgresql://user:pass@localhost/placement
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///placement.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
