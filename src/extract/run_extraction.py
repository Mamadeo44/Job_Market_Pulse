"""
Point d'entrée de l'extraction : appelle Remotive + Adzuna, normalise,
fusionne (dédupliqué par source+id), et sauvegarde le résultat en JSON.
"""

import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.extract.remotive_client import fetch_remote_jobs, filter_data_jobs, DATA_ROLE_KEYWORDS
from src.extract.adzuna_client import fetch_adzuna_jobs
from src.extract.normalize import normalize_remotive_job, normalize_adzuna_job
from src.load.upload_to_s3 import upload_json_to_s3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def run() -> dict:
    raw_remotive = fetch_remote_jobs(search_terms=DATA_ROLE_KEYWORDS, limit=100)
    filtered_remotive = filter_data_jobs(raw_remotive)
    normalized_remotive = [normalize_remotive_job(j) for j in filtered_remotive]

    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    raw_adzuna = fetch_adzuna_jobs(app_id=app_id, app_key=app_key)
    normalized_adzuna = [normalize_adzuna_job(j) for j in raw_adzuna]

    all_jobs = {}
    for job in normalized_remotive + normalized_adzuna:
        key = (job["source"], job["external_id"])
        all_jobs[key] = job
    jobs = list(all_jobs.values())

    payload = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "sources": ["remotive", "adzuna"],
        "job_count": len(jobs),
        "job_count_by_source": {
            "remotive": len(normalized_remotive),
            "adzuna": len(normalized_adzuna),
        },
        "jobs": jobs,
    }
    logger.info(f"Total fusionné : {len(jobs)} offres ({payload['job_count_by_source']})")
    return payload


if __name__ == "__main__":
    result = run()

    # Copie locale pour debug
    with open("extracted_jobs_test.json", "w") as f:
        json.dump(result, f, indent=2)
    logger.info("Copie locale sauvegardée : extracted_jobs_test.json")

    # Upload vers S3 (la vraie destination du pipeline)
    run_date = datetime.now(timezone.utc)
    s3_path = upload_json_to_s3(result, run_date)
    logger.info(f"Pipeline terminé. Donnée disponible sur : {s3_path}")