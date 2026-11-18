from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./data/oracle.db'
    redis_url: str | None = None
    admin_token: str = ''
    cors_origins: str = 'http://localhost:3000,http://127.0.0.1:3000'
    historical_data_permitted: bool = False
    season: str = '2026-27'
    data_dir: Path = Path('data')
    artifact_dir: Path = Path('artifacts')

settings = Settings()
