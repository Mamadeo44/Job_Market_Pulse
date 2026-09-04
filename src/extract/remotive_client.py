"""
Client d'extraction pour l'API Remotive.
Récupère les offres brutes liées à la data (aucune normalisation ici,
c'est le rôle de normalize.py).
"""
import logging
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
DATA_ROLE_KEYWORDS = [
    "data engineer", "data analyst", "data scientist",
    "analytics engineer", "business intelligence", "bi analyst",
    "data architect", "etl developer", "data engineering"
]

EXCLUDE_KEYWORDS = ["devops", "sre"]
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def fetch_remote_jobs(search_terms: list[str], limit: int = 100) -> list[dict]:
    """Interroge Remotive pour chaque terme de recherche, fusionne et déduplique par id."""
    all_jobs = {}

    for term in search_terms:
        params = {"search": term, "limit": limit}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Remotive recherche '{term}' (tentative {attempt}/{MAX_RETRIES})")
                response = requests.get(REMOTIVE_API_URL, params=params, timeout=10)
                response.raise_for_status()
                jobs = response.json().get("jobs", [])
                for job in jobs:
                    all_jobs[job["id"]] = job
                logger.info(f"Remotive '{term}' → {len(jobs)} offres")
                break
            except requests.exceptions.RequestException as e:
                logger.warning(f"Échec Remotive '{term}' : {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                else:
                    logger.error(f"Échec définitif Remotive '{term}'")

    logger.info(f"{len(all_jobs)} offres uniques récupérées depuis Remotive")
    return list(all_jobs.values())


def filter_data_jobs(jobs: list[dict]) -> list[dict]:
    """
    Filtre léger : élimine juste le bruit évident (devops/sre),
    garde tout le reste — le filtrage précis (rôle exact, stack)
    se fera au transform, pas ici.
    """
    filtered = [
        job for job in jobs
        if not any(ex in job.get("title", "").lower() for ex in EXCLUDE_KEYWORDS)
    ]
    logger.info(f"{len(filtered)} offres retenues après filtrage léger")
    return filtered