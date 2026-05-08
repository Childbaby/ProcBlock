from .settings import *  # noqa: F401,F403

# Dedicated local/CI database for backend task-path dry-runs.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "task-dry-run.sqlite3",
    }
}
