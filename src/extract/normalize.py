"""
Normalisation des offres Remotive/Adzuna vers un schéma commun,
et détection du mode de travail (remote / hybrid / on_site / unknown).
"""

ON_SITE_SIGNALS = ["no remote", "on-site only", "not remote", "office-based only"]
HYBRID_SIGNALS = ["hybrid"]
REMOTE_SIGNALS = ["remote", "work from home", "fully distributed"]


def detect_work_mode(title: str, description: str) -> str:
    """
    Hiérarchie de règles pour éviter les faux positifs
    (ex: "no remote work" n'est pas classé comme remote).
    """
    text = f"{title} {description}".lower()

    if any(s in text for s in ON_SITE_SIGNALS):
        return "on_site"
    if any(s in text for s in HYBRID_SIGNALS):
        return "hybrid"
    if any(s in text for s in REMOTE_SIGNALS):
        return "remote"
    return "unknown"


def normalize_remotive_job(job: dict) -> dict:
    title = job.get("title", "")
    description = job.get("description", "")
    return {
        "source": "remotive",
        "external_id": str(job.get("id")),
        "title": title,
        "company_name": job.get("company_name"),
        "location": job.get("candidate_required_location"),
        "country": None,
        "work_mode": detect_work_mode(title, description),
        "salary_min": None,
        "salary_max": None,
        "job_type": job.get("job_type"),
        "publication_date": job.get("publication_date"),
        "description": description,
        "url": job.get("url"),
        "tags": job.get("tags", []),
    }


def normalize_adzuna_job(job: dict) -> dict:
    title = job.get("title", "")
    description = job.get("description", "")
    return {
        "source": "adzuna",
        "external_id": str(job.get("id")),
        "title": title,
        "company_name": job.get("company", {}).get("display_name"),
        "location": job.get("location", {}).get("display_name"),
        "country": job.get("_country"),
        "work_mode": detect_work_mode(title, description),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "job_type": job.get("contract_time"),
        "publication_date": job.get("created"),
        "description": description,
        "url": job.get("redirect_url"),
        "tags": [],
    }