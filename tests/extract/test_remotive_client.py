"""
Tests unitaires pour la logique de filtrage de src/extract/remotive_client.py.
"""
from src.extract.remotive_client import filter_data_jobs


def test_filter_data_jobs_excludes_devops():
    jobs = [
        {"id": 1, "title": "Senior DevOps Engineer"},
        {"id": 2, "title": "Data Engineer"},
    ]
    result = filter_data_jobs(jobs)
    assert len(result) == 1
    assert result[0]["title"] == "Data Engineer"


def test_filter_data_jobs_keeps_everything_else():
    jobs = [
        {"id": 1, "title": "Random Marketing Role"},
        {"id": 2, "title": "Data Analyst"},
    ]
    result = filter_data_jobs(jobs)
    # Rappel : filter_data_jobs ne fait qu'exclure devops/sre,
    # le vrai filtre de pertinence est fait plus tard par is_relevant_job()
    assert len(result) == 2