from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Railway injects DATABASE_URL; fall back to local SQLite for dev.
    database_url: str = "sqlite:///./dev.db"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    # 30 days. A 12h token expired in the middle of the working day: every
    # save after that failed, and a contractor logging the day's progress had
    # no idea why. Long sessions are the point here — two known users, one
    # private project.
    access_token_expire_minutes: int = 43200

    # Comma-separated list, or "*" for any origin.
    cors_origins: str = "*"

    # When true, run the idempotent seed on startup. Useful on Railway where
    # there's no shell to run `python -m app.seed`. Turn off after first deploy.
    seed_on_start: bool = False

    @property
    def sqlalchemy_url(self) -> str:
        # Railway sometimes hands out the legacy "postgres://" scheme,
        # which SQLAlchemy doesn't recognize — normalize it.
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
