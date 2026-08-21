import json
import logging
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("mes")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mes:mes@db:5432/mes"
    # When set, database_url above is ignored — the connection string is
    # instead assembled from an AWS Secrets Manager secret (username,
    # password, host, port — db_name below always supplies the database
    # name, regardless of what the secret itself carries, see
    # _database_url_from_secret).
    #
    # Defaults to the real production secret/database because there is
    # currently no way to set these as env vars on the ECS task definition
    # (no access to it) — the Jenkins deploy pipeline just builds/ships this
    # image as-is with no per-environment overrides. Local dev stays safe
    # because .env explicitly sets DB_SECRET_ARN= (empty), which overrides
    # this default back off — see the .env comment before changing either
    # side of this. Once real task-definition env var access exists, prefer
    # setting DB_SECRET_ARN/DB_NAME there instead and revert these defaults
    # to None/"mes".
    db_secret_arn: str | None = "arn:aws:secretsmanager:ap-south-1:306372151400:secret:Prod-Backendapi-HK7wGL"
    db_name: str = "maxvolt_mes"
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

    The target database always comes from this app's own DB_NAME setting,
    never from a `dbname` field inside the secret — secrets on this cluster
    are shared/reused across separate applications (e.g. an existing
    Prod-Backendapi secret whose dbname points at a different app's
    database), so the secret's own dbname, if present, is ignored rather
    than trusted.
    """
    import boto3

    client = boto3.client("secretsmanager")
    creds = json.loads(client.get_secret_value(SecretId=secret_arn)["SecretString"])

    username = quote_plus(creds["username"])
    password = quote_plus(creds["password"])
    host = creds["host"]
    port = creds.get("port", 5432)

    return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{db_name}"


settings = Settings()

if settings.db_secret_arn:
    logger.info("db_secret_arn set — fetching database credentials from AWS Secrets Manager")
    settings.database_url = _database_url_from_secret(settings.db_secret_arn, settings.db_name)
