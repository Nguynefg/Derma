"""HTTP/session settings. Database settings remain in database_config.py."""

import os

COOKIE = "derma_session"
SECURE_COOKIE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
ORIGINS = set(
    os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
)
