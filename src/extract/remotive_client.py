"""
Client d'extraction pour l'API Remotive.
Récupère les offres d'emploi liées à la data et les sauvegarde en JSON brut.
"""
import logging
import time
from datetime import datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"

# Mots-clés pour identifier les postes data dans le titre
DATA_ROLE_KEYWORDS = [
    "data engineer", "data analyst", "data scientist",
    "analytics engineer", "business intelligence", "bi analyst",
    "data architect", "etl developer", "data engineering"
]

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def fetch_remote_jobs(limit: int = 200) -> list[dict]:
    """
    Appelle l'API Remotive avec retry/backoff et retourne la liste brute des offres.
    """
    params = {"limit": limit}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Appel API Remotive (tentative {attempt}/{MAX_RETRIES})")
            response = requests.get(REMOTIVE_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            jobs = data.get("jobs", [])
            logger.info(f"{len(jobs)} offres récupérées au total")
            return jobs

        except requests.exceptions.RequestException as e:
            logger.warning(f"Échec de l'appel API : {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * attempt
                logger.info(f"Nouvelle tentative dans {wait}s...")
                time.sleep(wait)
            else:
                logger.error("Échec définitif après plusieurs tentatives")
                raise


def filter_data_jobs(jobs: list[dict]) -> list[dict]:
    """
    Filtre les offres dont le titre correspond à un rôle data.
    """
    filtered = [
        job for job in jobs
        if any(keyword in job.get("title", "").lower() for keyword in DATA_ROLE_KEYWORDS)
    ]
    logger.info(f"{len(filtered)} offres data retenues après filtrage")
    return filtered


def build_extraction_payload(jobs: list[dict]) -> dict:
    """
    Enveloppe les offres avec des métadonnées d'extraction (traçabilité).
    """
    return {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source": "remotive_api",
        "job_count": len(jobs),
        "jobs": jobs
    }


if __name__ == "__main__":
    raw_jobs = fetch_remote_jobs(limit=200)
    data_jobs = filter_data_jobs(raw_jobs)
    payload = build_extraction_payload(data_jobs)

    import json
    with open("extracted_jobs_test.json", "w") as f:
        json.dump(payload, f, indent=2)

    logger.info(f"Sauvegardé localement : extracted_jobs_test.json ({len(data_jobs)} offres)")
