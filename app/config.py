import os

# Display name shown on the status page and browser title
EVENT_NAME: str = os.environ.get("EVENT_NAME", "PG Data 2026")

# Required
SECRET_KEY: str = os.environ["SECRET_KEY"]

# Optional
BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")
ADMIN_TOKEN: str = os.environ.get("ADMIN_TOKEN", "")
