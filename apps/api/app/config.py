import json
import logging
from functools import lru_cache
from typing import Literal

import boto3
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    environment: Literal["development", "mvp", "production"] = "development"
    log_level: str = "INFO"

    # Database — set directly for local dev, assembled from Secrets Manager in production
    database_url: str = ""
    db_secret_name: str = "/metabookly/database/master-credentials"

    # Connection pool sizing — conservative for Aurora Serverless v2 at 0.5 ACU min
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # AWS
    aws_region: str = "eu-west-2"
    aws_account_id: str = "562675430068"

    # S3
    onix_bucket_name: str = "metabookly-onix-feeds-562675430068"
    assets_bucket_name: str = "metabookly-assets-562675430068"

    # Cognito
    cognito_user_pool_id: str = "eu-west-2_Hb5mR6Ugo"
    cognito_client_id: str = "7khfisn3jq5iv9r1k27sgm5clt"
    cognito_region: str = "eu-west-2"

    def resolve_database_url(self) -> str:
        """
        Returns the database URL.
        - Local dev: reads DATABASE_URL directly from env/.env
        - Production: fetches credentials from Secrets Manager and assembles the URL
        """
        if self.database_url:
            return self.database_url

        logger.info("Fetching database credentials from Secrets Manager: %s", self.db_secret_name)
        try:
            client = boto3.client("secretsmanager", region_name=self.aws_region)
            response = client.get_secret_value(SecretId=self.db_secret_name)
            secret = json.loads(response["SecretString"])
            url = (
                f"postgresql+asyncpg://{secret['username']}:{secret['password']}"
                f"@{secret['host']}:{secret['port']}/{secret['dbname']}"
            )
            logger.info("Database credentials resolved from Secrets Manager")
            return url
        except ClientError as e:
            raise RuntimeError(
                f"Failed to fetch database credentials from Secrets Manager: {e}"
            ) from e


@lru_cache
def get_settings() -> Settings:
    return Settings()
