"""
Client d'extraction pour l'API Adzuna.
Récupère les offres Data Analyst/Engineer pour une liste de pays,
remote, hybride et présentiel confondus.
"""
import logging
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
ADZUNA_COUNTRIES = ["ch", "es", "gb"]
SEARCH_TERMS = ["data engineer", "data analyst"]
RESULTS_PER_PAGE = 50

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def fetch_adzuna_jobs(app_id: str, app_key: str) -> list[dict]:
    """
    Interroge Adzuna pour chaque pays et chaque terme.
    Ajoute manuellement le code pays à chaque offre (l'API ne le renvoie pas).
    """
    all_jobs = []

    for country in ADZUNA_COUNTRIES:
        for term in SEARCH_TERMS:
            url = f"{ADZUNA_BASE_URL}/{country}/search/1"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": term,
                "results_per_page": RESULTS_PER_PAGE,
            }

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(f"Adzuna [{country}] '{term}' (tentative {attempt}/{MAX_RETRIES})")
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    results = response.json().get("results", [])
                    for job in results:
                        job["_country"] = country
                    all_jobs.extend(results)
                    logger.info(f"Adzuna [{country}] '{term}' → {len(results)} offres")
                    break
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Échec Adzuna [{country}] '{term}' : {e}")
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                    else:
                        logger.error(f"Échec définitif Adzuna [{country}] '{term}'")

    logger.info(f"{len(all_jobs)} offres brutes récupérées depuis Adzuna")
    return all_jobs