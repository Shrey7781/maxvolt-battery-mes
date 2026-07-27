from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mes:mes@db:5432/mes"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 120
    environment: str = "production"


settings = Settings()
