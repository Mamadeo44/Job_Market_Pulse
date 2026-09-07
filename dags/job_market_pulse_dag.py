"""
DAG principal du pipeline job-market-pulse.
Vérifie la disponibilité des APIs (HTTP Sensors) avant de lancer
l'extraction, la normalisation et l'upload vers S3.
Schedule : chaque lundi à 6h.
"""
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.http.sensors.http import HttpSensor
from airflow.operators.python import PythonOperator

# Permet d'importer nos modules src/ depuis le DAG
sys.path.insert(0, "/opt/airflow")

from src.extract.remotive_client import fetch_remote_jobs, filter_data_jobs, DATA_ROLE_KEYWORDS
from src.extract.adzuna_client import fetch_adzuna_jobs
from src.extract.normalize import normalize_remotive_job, normalize_adzuna_job
from src.load.upload_to_s3 import upload_json_to_s3

import os
from dotenv import load_dotenv

default_args = {
    "owner": "mamadou",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="job_market_pulse_etl",
    default_args=default_args,
    description="Extraction hebdomadaire des offres data (Remotive + Adzuna) vers S3",
    schedule_interval="0 6 * * 1",  # tous les lundis à 6h
    start_date=datetime(2026, 9, 1),
    catchup=False,
    tags=["job-market-pulse", "etl"],
)

check_remotive_api = HttpSensor(
    task_id="check_remotive_api",
    http_conn_id="remotive_api",
    endpoint="/api/remote-jobs?limit=1",
    poke_interval=10,
    timeout=60,
    dag=dag,
)

check_adzuna_api = HttpSensor(
    task_id="check_adzuna_api",
    http_conn_id="adzuna_api",
    endpoint="/v1/api/jobs/gb/search/1?app_id={{ var.value.adzuna_app_id }}&app_key={{ var.value.adzuna_app_key }}&results_per_page=1",
    poke_interval=10,
    timeout=60,
    dag=dag,
)


def run_extraction_and_upload(**context):
    load_dotenv("/opt/airflow/.env")

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
        "extracted_at": datetime.utcnow().isoformat(),
        "sources": ["remotive", "adzuna"],
        "job_count": len(jobs),
        "job_count_by_source": {
            "remotive": len(normalized_remotive),
            "adzuna": len(normalized_adzuna),
        },
        "jobs": jobs,
    }

    run_date = context["logical_date"]
    s3_path = upload_json_to_s3(payload, run_date)
    print(f"Pipeline terminé : {s3_path}")


extract_and_load = PythonOperator(
    task_id="extract_and_load",
    python_callable=run_extraction_and_upload,
    dag=dag,
)

[check_remotive_api, check_adzuna_api] >> extract_and_load