"""Durable storage on S3 for uploads, built plugins and the knowledge index.

Turned on by setting S3_BUCKET (the AWS instance gets it from its secret). Without it every function reports
"not stored" and the app keeps working with local files, so local development needs no AWS account.
On EC2 the credentials come from the instance's IAM role; nothing is configured by hand.
"""

import base64
import logging
import os
import uuid
from pathlib import Path

log = logging.getLogger("vst")

_client = None
_client_region = None


def enabled() -> bool:
    return bool(os.getenv("S3_BUCKET"))


def _bucket() -> str:
    return os.environ["S3_BUCKET"]


def _s3():
    global _client, _client_region
    region = os.getenv("AWS_REGION", "eu-north-1")
    if _client is None or _client_region != region:
        import boto3
        from botocore.config import Config

        _client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=f"https://s3.{region}.amazonaws.com",  # regional address, so download links never need a redirect
            config=Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=60,
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
            ),
        )
        _client_region = region
    return _client


def uri(key: str) -> str:
    return f"s3://{_bucket()}/{key}"


def is_s3_uri(value: str | None) -> bool:
    return bool(value) and value.startswith("s3://")


def _split(value: str) -> tuple[str, str]:
    bucket, _, key = value.removeprefix("s3://").partition("/")
    return bucket, key


def upload_file(path: str | Path, key: str, content_type: str | None = None) -> str | None:
    """Upload a local file. Returns its s3:// address, or None if storage is off or the upload failed."""
    if not enabled():
        return None
    try:
        extra = {"ContentType": content_type} if content_type else None
        _s3().upload_file(str(path), _bucket(), key, ExtraArgs=extra)
        return uri(key)
    except Exception as exc:  # losing the copy must not break the user's request
        log.warning("S3 upload of %s failed: %r", key, exc)
        return None


def put_bytes(data: bytes, key: str, content_type: str) -> str | None:
    if not enabled():
        return None
    try:
        _s3().put_object(Bucket=_bucket(), Key=key, Body=data, ContentType=content_type)
        return uri(key)
    except Exception as exc:
        log.warning("S3 upload of %s failed: %r", key, exc)
        return None


def store_picture(thread_id: str, data_url: str) -> str | None:
    """Keep an uploaded picture (a data URL). Returns its s3:// address or None."""
    if not enabled():
        return None
    try:
        header, payload = data_url.split(",", 1)
        mime = header.removeprefix("data:").split(";")[0]
        ext = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp"}.get(mime, "bin")
        return put_bytes(base64.b64decode(payload), f"uploads/{thread_id}/{uuid.uuid4().hex}.{ext}", mime)
    except Exception as exc:
        log.warning("could not store the uploaded picture: %r", exc)
        return None


def download_file(key: str, dest: str | Path) -> bool:
    if not enabled():
        return False
    try:
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        _s3().download_file(_bucket(), key, str(dest))
        return True
    except Exception as exc:
        log.warning("S3 download of %s failed: %r", key, exc)
        return False


def download_url(value: str, filename: str, seconds: int = 300) -> str:
    """A short-lived link the browser can use to download an s3:// object."""
    bucket, key = _split(value)
    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key, "ResponseContentDisposition": f'attachment; filename="{filename}"'},
        ExpiresIn=seconds,
    )
