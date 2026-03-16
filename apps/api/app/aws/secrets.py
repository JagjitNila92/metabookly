import json
import logging
import boto3
from botocore.exceptions import ClientError
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_retailer_distributor_credentials(retailer_id: str, distributor_code: str) -> dict:
    """
    Fetch a retailer's credentials for a specific distributor from Secrets Manager.
    Secret path: /metabookly/retailer/{retailer_id}/distributor/{distributor_code}/credentials
    """
    settings = get_settings()
    secret_name = (
        f"/metabookly/retailer/{retailer_id}/distributor/{distributor_code.lower()}/credentials"
    )
    try:
        client = boto3.client("secretsmanager", region_name=settings.aws_region)
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        logger.error("Failed to fetch credentials for retailer %s / %s: %s",
                     retailer_id, distributor_code, e)
        raise
