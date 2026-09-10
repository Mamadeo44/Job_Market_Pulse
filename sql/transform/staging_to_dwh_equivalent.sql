-- ============================================================
-- ÉQUIVALENT SQL PUR de src/transform/load_dwh.py
-- ------------------------------------------------------------
-- Ce script N'EST PAS exécuté par le pipeline (qui utilise la
-- version Python pour bénéficier de la lisibilité du texte
-- parsing en code). Il est fourni à titre de démonstration :
-- preuve qu'on maîtrise la même logique en SQL déclaratif pur,
-- et alternative utilisable telle quelle par quelqu'un qui
-- préfère un pipeline 100% SQL (ex: via dbt).
-- ============================================================

-- 1. Table de référence des compétences à détecter
--    (équivalent de SKILL_KEYWORDS en Python)
CREATE TEMP TABLE skill_keywords (skill_name TEXT);
INSERT INTO skill_keywords (skill_name) VALUES
    ('python'), ('sql'), ('talend'), ('docker'), ('airflow'),
    ('excel'), ('power bi'), ('tableau'), ('aws'), ('azure'),
    ('gcp'), ('spark'), ('dbt'), ('snowflake'), ('etl'),
    ('postgresql'), ('mysql'), ('nosql'), ('mongodb'),
    ('kafka'), ('looker');

-- 2. Filtrage des offres pertinentes
--    (équivalent de is_relevant_job())
CREATE TEMP TABLE relevant_staging AS
SELECT *
FROM staging.job_postings_raw
WHERE extracted_at = (SELECT MAX(extracted_at) FROM staging.job_postings_raw)
  AND (
        LOWER(title) LIKE '%data engineer%'
     OR LOWER(title) LIKE '%data analyst%'
     OR LOWER(title) LIKE '%analytics engineer%'
     OR LOWER(title) LIKE '%bi analyst%'
     OR LOWER(title) LIKE '%business intelligence%'
      )
  AND NOT (
        LOWER(title) LIKE '%sales%'
     OR LOWER(title) LIKE '%copywriter%'
     OR LOWER(title) LIKE '%writer%'
     OR LOWER(title) LIKE '%marketing%'
     OR LOWER(title) LIKE '%support%'
     OR LOWER(title) LIKE '%developer%'
     OR LOWER(title) LIKE '%devops%'
     OR LOWER(title) LIKE '%sre%'
      );

-- 3. Calcul de la séniorité
--    (équivalent de compute_seniority())
CREATE TEMP TABLE relevant_with_seniority AS
SELECT
    *,
    CASE
        WHEN LOWER(title) ~ '(senior|sr\.|sr |lead|principal|head of|staff)' THEN 'senior'
        WHEN LOWER(title) ~ '(junior|jr\.|jr |entry level|graduate|intern)' THEN 'junior'
        ELSE 'unknown'
    END AS seniority_level
FROM relevant_staging;

-- 4. Upsert des dimensions géographiques
INSERT INTO dwh.dim_country (country_code, country_name)
SELECT DISTINCT UPPER(country), UPPER(country)
FROM relevant_with_seniority
WHERE country IS NOT NULL
ON CONFLICT (country_code) DO NOTHING;

INSERT INTO dwh.dim_city (city_name, country_id)
SELECT DISTINCT
    SPLIT_PART(r.location, ',', 1),
    c.country_id
FROM relevant_with_seniority r
JOIN dwh.dim_country c ON UPPER(r.country) = c.country_code
WHERE r.country IS NOT NULL AND r.location LIKE '%,%'
ON CONFLICT (city_name, country_id) DO NOTHING;

-- 5. Upsert de la dimension entreprise
INSERT INTO dwh.dim_company (company_name)
SELECT DISTINCT COALESCE(company_name, 'Unknown')
FROM relevant_with_seniority
ON CONFLICT (company_name) DO NOTHING;

-- 6. Upsert de la dimension compétence
INSERT INTO dwh.dim_skill (skill_name)
SELECT skill_name FROM skill_keywords
ON CONFLICT (skill_name) DO NOTHING;

-- 7. Upsert dans la table de faits
--    (équivalent du bloc INSERT ... ON CONFLICT du script Python)
INSERT INTO dwh.fact_job_posting (
    source, external_id, title, company_id, city_id, work_mode,
    salary_min, salary_max, job_type, seniority_level,
    date_first_seen, date_last_seen, url, description
)
SELECT
    r.source,
    r.external_id,
    r.title,
    co.company_id,
    ci.city_id,
    r.work_mode,
    NULLIF(r.salary_min, 'None')::NUMERIC,
    NULLIF(r.salary_max, 'None')::NUMERIC,
    r.job_type,
    r.seniority_level,
    CURRENT_DATE,
    CURRENT_DATE,
    r.url,
    r.description
FROM relevant_with_seniority r
JOIN dwh.dim_company co ON COALESCE(r.company_name, 'Unknown') = co.company_name
LEFT JOIN dwh.dim_country cnt ON UPPER(r.country) = cnt.country_code
LEFT JOIN dwh.dim_city ci ON SPLIT_PART(r.location, ',', 1) = ci.city_name AND cnt.country_id = ci.country_id
ON CONFLICT (source, external_id) DO UPDATE SET
    date_last_seen = EXCLUDED.date_last_seen,
    title = EXCLUDED.title;

-- 8. Peuplement de la table de liaison offre-compétence
--    (équivalent de detect_skills() + insertion dans bridge_job_skill)
INSERT INTO dwh.bridge_job_skill (job_posting_id, skill_id)
SELECT DISTINCT
    f.job_posting_id,
    sk.skill_id
FROM relevant_with_seniority r
JOIN dwh.fact_job_posting f ON r.source = f.source AND r.external_id = f.external_id
CROSS JOIN dwh.dim_skill sk
WHERE LOWER(r.title || ' ' || COALESCE(r.description, '')) LIKE '%' || sk.skill_name || '%'
ON CONFLICT DO NOTHING;

-- Nettoyage des tables temporaires
DROP TABLE skill_keywords;
DROP TABLE relevant_staging;
DROP TABLE relevant_with_seniority;