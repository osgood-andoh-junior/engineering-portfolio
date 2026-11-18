import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database_path: Path
    artifact_dir: Path
    frontend_origin: str

    @classmethod
    def from_env(cls):
        def local_path(name, default):
            value = Path(os.getenv(name, default))
            return value if value.is_absolute() else ROOT / value

        return cls(
            database_path=local_path("DATABASE_PATH", "backend/storage/support.db"),
            artifact_dir=local_path("ARTIFACT_DIR", "ml/artifacts"),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        )
