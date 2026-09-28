import os
from pathlib import Path

# Base directory of the backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Optionally load .env file if it exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://kote@localhost:5432/creator_marketplace"
)

SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)

ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8000"
    ).split(",")
    if origin.strip()
]
