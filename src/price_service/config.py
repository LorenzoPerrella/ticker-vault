"""Configurazione dell'applicazione, letta da variabili d'ambiente / file .env.secret."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Impostazioni dell'app. In dev vengono lette da `.env.secret` (gitignored);
    lo stesso file alimenta anche il `secretGenerator` di Kustomize in k8s (Fase 6).
    """

    model_config = SettingsConfigDict(
        env_file=".env.secret", env_file_encoding="utf-8", extra="ignore"
    )

    postgres_user: str = "price_service"
    postgres_password: str = "price_service_dev_password"
    postgres_db: str = "price_service"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        """DSN async per SQLAlchemy/asyncpg."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
