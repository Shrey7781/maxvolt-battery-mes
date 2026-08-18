import json
import logging
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("mes")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mes:mes@db:5432/mes"
    # When set, database_url below is ignored — the connection string is
    # instead assembled from an AWS Secrets Manager secret (RDS's own
    # "manage master credentials in Secrets Manager" format: username,
    # password, host, port; no dbname, hence db_name below). Leave unset
    # for local/dev, where database_url (or docker-compose's DATABASE_URL
    # override) is used directly, same as before.
    db_secret_arn: str | None = None
    db_name: str = "mes"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 120
    environment: str = "production"


def _database_url_from_secret(secret_arn: str, db_name: str) -> str:
    """Fetches RDS master credentials from AWS Secrets Manager and
    assembles a SQLAlchemy connection URL from them.

    Uses boto3's default credential chain (the ECS task role / EC2 instance
    profile, not a static key pair) — the task/instance's IAM role needs
    secretsmanager:GetSecretValue on this ARN. Any failure here (bad ARN,
    missing IAM permission, network) is left to propagate: a container that
    can't resolve its DB credentials should fail to start loudly, not limp
    along on a fallback that would just fail confusingly later.
    """
    import boto3

    client = boto3.client("secretsmanager")
    creds = json.loads(client.get_secret_value(SecretId=secret_arn)["SecretString"])

    username = quote_plus(creds["username"])
    password = quote_plus(creds["password"])
    host = creds["host"]
    port = creds.get("port", 5432)
    dbname = creds.get("dbname", db_name)

    return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{dbname}"


settings = Settings()

if settings.db_secret_arn:
    logger.info("db_secret_arn set — fetching database credentials from AWS Secrets Manager")
    settings.database_url = _database_url_from_secret(settings.db_secret_arn, settings.db_name)
