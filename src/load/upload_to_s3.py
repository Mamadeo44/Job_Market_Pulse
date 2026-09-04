"""
Upload des données extraites vers la zone raw de S3.
Partitionnement par date pour permettre l'historisation
et le rejeu (idempotence) des runs.
"""
import logging
import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_s3_client():
    return boto3.client("s3", region_name=os.getenv("AWS_REGION"))


def build_s3_key(run_date, prefix: str = "job_market_pulse") -> str:
    """
    Construit le chemin S3 partitionné par date.
    Ex: job_market_pulse/raw/year=2026/month=09/day=04/jobs.json
    """
    return (
        f"{prefix}/raw/"
        f"year={run_date.year:04d}/"
        f"month={run_date.month:02d}/"
        f"day={run_date.day:02d}/"
        f"jobs.json"
    )


def upload_json_to_s3(payload: dict, run_date) -> str:
    """
    Upload le payload JSON vers S3 à l'emplacement partitionné par date.
    Retourne le chemin S3 complet en cas de succès.
    """
    import json

    bucket = os.getenv("AWS_S3_BUCKET")
    key = build_s3_key(run_date)
    body = json.dumps(payload, indent=2)

    s3 = get_s3_client()

    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        s3_path = f"s3://{bucket}/{key}"
        logger.info(f"Upload réussi : {s3_path}")
        return s3_path
    except ClientError as e:
        logger.error(f"Échec de l'upload S3 : {e}")
        raise