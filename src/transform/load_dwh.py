"""
Transforme les données de staging vers le modèle en flocon (dwh) :
- filtre les offres pertinentes (rôle data)
- détecte les compétences mentionnées
- calcule le niveau de séniorité
- résout la géographie (pays/ville)
- upsert dans fact_job_posting avec historisation (first_seen/last_seen)
"""
import logging
import os
import re
from datetime import datetime, date, timedelta

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

# --- Référentiels métier ---

INCLUDE_ROLE_PATTERNS = [
    "data engineer", "data analyst", "analytics engineer",
    "bi analyst", "business intelligence"
]
EXCLUDE_ROLE_PATTERNS = [
    "sales", "copywriter", "writer", "marketing",
    "support", "developer", "devops", "sre"
]

SKILL_KEYWORDS = [
    "python", "sql", "talend", "docker", "airflow", "excel", "power bi",
    "tableau", "aws", "azure", "gcp", "spark", "dbt", "snowflake",
    "etl", "postgresql", "mysql", "nosql", "mongodb", "kafka", "looker"
]

SENIOR_PATTERNS = ["senior", "sr.", "sr ", "lead", "principal", "head of", "staff"]
JUNIOR_PATTERNS = ["junior", "jr.", "jr ", "entry level", "graduate", "intern"]
COUNTRY_NAMES = {
    "ch": "Switzerland", "fr": "France", "de": "Germany", "es": "Spain",
    "it": "Italy", "nl": "Netherlands", "at": "Austria", "be": "Belgium",
    "gb": "United Kingdom", "au": "Australia",
}

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# --- Logique métier ---

def is_relevant_job(title: str) -> bool:
    title_lower = (title or "").lower()
    has_role = any(p in title_lower for p in INCLUDE_ROLE_PATTERNS)
    has_excluded = any(p in title_lower for p in EXCLUDE_ROLE_PATTERNS)
    return has_role and not has_excluded


def detect_skills(title: str, description: str) -> list[str]:
    text = f"{title or ''} {description or ''}".lower()
    return [skill for skill in SKILL_KEYWORDS if skill in text]


def compute_seniority(title: str) -> str:
    title_lower = (title or "").lower()
    if any(p in title_lower for p in SENIOR_PATTERNS):
        return "senior"
    if any(p in title_lower for p in JUNIOR_PATTERNS):
        return "junior"
    return "unknown"


def parse_geography(row: dict) -> tuple[str | None, str | None]:
    """
    Retourne (country_name, city_name). Simplifié : on utilise le code
    pays quand disponible (Adzuna), sinon on marque Remote/Unknown.
    """
    country = row.get("country")
    location = row.get("location") or ""

    if country:
        city = location.split(",")[0].strip() if "," in location else None
        return country.upper(), city

    return None, None


# --- Upserts dimensions (retournent l'id, créent si besoin) ---

def get_or_create_country(cur, country_code: str | None) -> int | None:
    if not country_code:
        return None
    country_name = COUNTRY_NAMES.get(country_code.lower(), country_code.upper())
    cur.execute(
        """
        INSERT INTO dwh.dim_country (country_code, country_name)
        VALUES (%s, %s)
        ON CONFLICT (country_code) DO UPDATE SET country_name = EXCLUDED.country_name
        RETURNING country_id
        """,
        (country_code.upper(), country_name)
    )
    return cur.fetchone()["country_id"]


def get_or_create_city(cur, city_name: str | None, country_id: int | None) -> int | None:
    if not city_name or not country_id:
        return None
    cur.execute(
        """
        INSERT INTO dwh.dim_city (city_name, country_id)
        VALUES (%s, %s)
        ON CONFLICT (city_name, country_id) DO UPDATE SET city_name = EXCLUDED.city_name
        RETURNING city_id
        """,
        (city_name, country_id)
    )
    return cur.fetchone()["city_id"]


def get_or_create_company(cur, company_name: str) -> int:
    cur.execute(
        """
        INSERT INTO dwh.dim_company (company_name)
        VALUES (%s)
        ON CONFLICT (company_name) DO UPDATE SET company_name = EXCLUDED.company_name
        RETURNING company_id
        """,
        (company_name,)
    )
    return cur.fetchone()["company_id"]


def get_or_create_skill(cur, skill_name: str) -> int:
    cur.execute(
        """
        INSERT INTO dwh.dim_skill (skill_name)
        VALUES (%s)
        ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
        RETURNING skill_id
        """,
        (skill_name,)
    )
    return cur.fetchone()["skill_id"]


def ensure_date_exists(cur, d: date):
    cur.execute(
        """
        INSERT INTO dwh.dim_date (date_id, year, month, day, week_of_year, day_name)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (date_id) DO NOTHING
        """,
        (d, d.year, d.month, d.day, d.isocalendar()[1], d.strftime("%A"))
    )


# --- Pipeline principal ---

def run():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # On ne retraite que le run le plus récent (déjà chargé en staging)
    cur.execute("""
        SELECT * FROM staging.job_postings_raw
        WHERE extracted_at = (SELECT MAX(extracted_at) FROM staging.job_postings_raw)
    """)
    rows = cur.fetchall()
    logger.info(f"{len(rows)} lignes récupérées depuis staging (dernier run)")

    today = date.today()
    ensure_date_exists(cur, today)

    inserted, updated, skipped = 0, 0, 0

    for row in rows:
        if not is_relevant_job(row["title"]):
            skipped += 1
            continue

        company_id = get_or_create_company(cur, row["company_name"] or "Unknown")
        country_name, city_name = parse_geography(row)
        country_id = get_or_create_country(cur, country_name)
        city_id = get_or_create_city(cur, city_name, country_id)
        seniority = compute_seniority(row["title"])

        cur.execute(
            """
            INSERT INTO dwh.fact_job_posting (
                source, external_id, title, company_id, city_id, work_mode,
                salary_min, salary_max, job_type, seniority_level,
                publication_date_id, date_first_seen, date_last_seen, url, description
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, external_id) DO UPDATE SET
                date_last_seen = EXCLUDED.date_last_seen,
                title = EXCLUDED.title
            RETURNING job_posting_id, (xmax = 0) AS was_inserted
            """,
            (
                row["source"], row["external_id"], row["title"], company_id, city_id,
                row["work_mode"],
                float(row["salary_min"]) if row["salary_min"] and row["salary_min"] != "None" else None,
                float(row["salary_max"]) if row["salary_max"] and row["salary_max"] != "None" else None,
                row["job_type"], seniority,
                None,  # publication_date_id simplifié pour l'instant (None accepté)
                today, today, row["url"], row["description"],
            )
        )
        result = cur.fetchone()
        job_posting_id = result["job_posting_id"]
        if result["was_inserted"]:
            inserted += 1
        else:
            updated += 1

        skills = detect_skills(row["title"], row["description"])
        for skill in skills:
            skill_id = get_or_create_skill(cur, skill)
            cur.execute(
                """
                INSERT INTO dwh.bridge_job_skill (job_posting_id, skill_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (job_posting_id, skill_id)
            )

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Transform terminé : {inserted} insérées, {updated} mises à jour, {skipped} ignorées (hors scope)")


if __name__ == "__main__":
    run()