"""
Tests unitaires pour la logique métier de src/transform/load_dwh.py.
Ces fonctions sont testées isolément (pas de vraie connexion DB),
ce qui les rend rapides et fiables à exécuter à tout moment.
"""
from src.transform.load_dwh import (
    is_relevant_job,
    detect_skills,
    compute_seniority,
    parse_geography,
)


# --- Tests de is_relevant_job() ---

def test_is_relevant_job_accepts_data_engineer():
    assert is_relevant_job("Senior Data Engineer") is True


def test_is_relevant_job_accepts_data_analyst():
    assert is_relevant_job("Data Analyst") is True


def test_is_relevant_job_rejects_sales():
    assert is_relevant_job("Sales Jedi") is False


def test_is_relevant_job_rejects_developer_even_with_data_word():
    # Cas piège : contient "data" mais aussi "developer" (exclu)
    assert is_relevant_job("Data Platform Developer") is False


def test_is_relevant_job_handles_none_title():
    assert is_relevant_job(None) is False


# --- Tests de detect_skills() ---

def test_detect_skills_finds_python_and_sql():
    skills = detect_skills("Data Engineer", "We use Python and SQL daily")
    assert "python" in skills
    assert "sql" in skills


def test_detect_skills_returns_empty_list_when_no_match():
    skills = detect_skills("Sales Manager", "No tech skills mentioned here")
    assert skills == []


def test_detect_skills_is_case_insensitive():
    skills = detect_skills("PYTHON Developer", "We need PYTHON expertise")
    assert "python" in skills


# --- Tests de compute_seniority() ---

def test_compute_seniority_detects_senior():
    assert compute_seniority("Senior Data Engineer") == "senior"


def test_compute_seniority_detects_junior():
    assert compute_seniority("Junior Data Analyst") == "junior"


def test_compute_seniority_defaults_to_unknown():
    assert compute_seniority("Data Engineer") == "unknown"


def test_compute_seniority_prioritizes_senior_pattern():
    # Cas piège : "lead" est un pattern senior
    assert compute_seniority("Lead Data Engineer") == "senior"


# --- Tests de parse_geography() ---

def test_parse_geography_extracts_city_and_country():
    row = {"country": "ch", "location": "Zürich, Switzerland"}
    country, city = parse_geography(row)
    assert country == "CH"
    assert city == "Zürich"


def test_parse_geography_returns_none_when_no_country():
    row = {"country": None, "location": "Worldwide"}
    country, city = parse_geography(row)
    assert country is None
    assert city is None