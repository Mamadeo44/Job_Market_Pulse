"""
Charge le dernier fichier JSON extrait depuis S3 vers la table staging.
Chaque exécution ajoute les offres du run (append-only, pas de dédup ici).
"""
import json
import logging
import os

import boto3
import psycopg2
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def fetch_latest_s3_payload() -> dict:
    """
    Récupère le fichier JSON le plus récent dans la zone raw S3
    (basé sur le tri des clés, qui fonctionne grâce au partitionnement
    year=/month=/day= qui trie naturellement par ordre chronologique).
    """
    bucket = os.getenv("AWS_S3_BUCKET")
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))

    response = s3.list_objects_v2(
        Bucket=bucket,
        Prefix="job_market_pulse/raw/"
    )
    objects = response.get("Contents", [])
    if not objects:
        raise ValueError("Aucun fichier trouvé dans la zone raw S3")

    latest = max(objects, key=lambda obj: obj["Key"])
    logger.info(f"Fichier le plus récent trouvé : {latest['Key']}")

    obj = s3.get_object(Bucket=bucket, Key=latest["Key"])
    payload = json.loads(obj["Body"].read())
    return payload


def insert_into_staging(payload: dict) -> int:
    """
    Insère chaque offre du payload dans staging.job_postings_raw.
    Retourne le nombre de lignes insérées.
    """
    jobs = payload.get("jobs", [])
    extracted_at = payload.get("extracted_at")

    conn = get_db_connection()
    cur = conn.cursor()

    insert_query = """
        INSERT INTO staging.job_postings_raw (
            source, external_id, title, company_name, location,
            country, work_mode, salary_min, salary_max, job_type,
            publication_date, description, url, tags, extracted_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for job in jobs:
        cur.execute(insert_query, (
            job.get("source"),
            job.get("external_id"),
            job.get("title"),
            job.get("company_name"),
            job.get("location"),
            job.get("country"),
            job.get("work_mode"),
            str(job.get("salary_min")) if job.get("salary_min") is not None else None,
            str(job.get("salary_max")) if job.get("salary_max") is not None else None,
            job.get("job_type"),
            job.get("publication_date"),
            job.get("description"),
            job.get("url"),
            json.dumps(job.get("tags", [])),
            extracted_at,
        ))

    conn.commit()
    inserted_count = cur.rowcount
    cur.close()
    conn.close()

    logger.info(f"{len(jobs)} offres insérées en staging")
    return len(jobs)


if __name__ == "__main__":
    payload = fetch_latest_s3_payload()
    insert_into_staging(payload)