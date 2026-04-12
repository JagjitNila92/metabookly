"""S3 helpers for ONIX feed upload and asset storage."""
import boto3
from app.config import get_settings


def generate_onix_upload_url(
    s3_key: str,
    expires_in: int = 3600,
    content_type: str = "application/xml",
) -> str:
    """
    Generate a pre-signed S3 PUT URL for ONIX feed upload.

    The publisher uploads the file directly to S3 using this URL —
    the file never passes through our API server.

    Args:
        s3_key:       Key to store the file under in the ONIX feeds bucket
        expires_in:   URL validity in seconds (default 1 hour)
        content_type: Expected content-type (enforced by S3)

    Returns:
        Pre-signed PUT URL string
    """
    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    return s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.onix_bucket_name,
            "Key": s3_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )


def download_from_s3(bucket: str, key: str) -> bytes:
    """Download an object from S3 and return its bytes."""
    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def upload_cover_to_s3(isbn13: str, content: bytes, content_type: str) -> str:
    """
    Upload a cover image to the assets bucket.

    Stored at: covers/{isbn13}/original.{ext}

    Returns the public HTTPS URL of the uploaded image.
    """
    settings = get_settings()
    ext = "jpg" if content_type == "image/jpeg" else "png"
    key = f"covers/{isbn13}/original.{ext}"

    s3 = boto3.client("s3", region_name=settings.aws_region)
    s3.put_object(
        Bucket=settings.assets_bucket_name,
        Key=key,
        Body=content,
        ContentType=content_type,
        CacheControl="public, max-age=31536000",
    )

    return f"https://{settings.assets_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"


def delete_cover_from_s3(isbn13: str) -> None:
    """Delete both jpg and png cover variants for an ISBN."""
    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    for ext in ("jpg", "png"):
        key = f"covers/{isbn13}/original.{ext}"
        try:
            s3.delete_object(Bucket=settings.assets_bucket_name, Key=key)
        except Exception:
            pass  # Best-effort — object may not exist
