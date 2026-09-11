CREATE SCHEMA IF NOT EXISTS datamart;

-- Vue 1 : demande par compétence, avec pourcentage du total des offres
-- Utile pour un graphique en barres "top compétences demandées"
CREATE OR REPLACE VIEW datamart.mart_skill_demand AS
SELECT
    s.skill_name,
    COUNT(DISTINCT b.job_posting_id) AS job_count,
    ROUND(
        100.0 * COUNT(DISTINCT b.job_posting_id) / (SELECT COUNT(*) FROM dwh.fact_job_posting),
        1
    ) AS pct_du_total
FROM dwh.bridge_job_skill b
JOIN dwh.dim_skill s ON b.skill_id = s.skill_id
GROUP BY s.skill_name
ORDER BY job_count DESC;

-- Vue 2 : répartition par séniorité, globale
-- Utile pour un graphique en camembert/donut
CREATE OR REPLACE VIEW datamart.mart_seniority_distribution AS
SELECT
    seniority_level,
    COUNT(*) AS job_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_du_total
FROM dwh.fact_job_posting
GROUP BY seniority_level
ORDER BY job_count DESC;

-- Vue 3 : répartition géographique (pays + ville), avec source
-- Utile pour une carte ou un graphique empilé par pays
CREATE OR REPLACE VIEW datamart.mart_geography_demand AS
SELECT
    COALESCE(co.country_name, 'Remote / Not specified')::VARCHAR(100) AS country_name,
    COALESCE(ci.city_name, 'Not specified')::VARCHAR(200) AS city_name,
    f.source,
    COUNT(*) AS job_count
FROM dwh.fact_job_posting f
LEFT JOIN dwh.dim_city ci ON f.city_id = ci.city_id
LEFT JOIN dwh.dim_country co ON ci.country_id = co.country_id
GROUP BY country_name, city_name, f.source
ORDER BY job_count DESC;

-- Bonus : croisement compétence x séniorité, pour répondre à
-- "quels outils sont plus demandés chez les seniors vs les autres ?"
CREATE OR REPLACE VIEW datamart.mart_skill_by_seniority AS
SELECT
    s.skill_name,
    f.seniority_level,
    COUNT(*) AS job_count
FROM dwh.bridge_job_skill b
JOIN dwh.dim_skill s ON b.skill_id = s.skill_id
JOIN dwh.fact_job_posting f ON b.job_posting_id = f.job_posting_id
GROUP BY s.skill_name, f.seniority_level
ORDER BY s.skill_name, job_count DESC;

-- Vue KPI : une seule ligne, chaque colonne = un indicateur de synthèse
-- Alimente les cartes "Number" en haut du dashboard
CREATE OR REPLACE VIEW datamart.mart_kpi_summary AS
SELECT
    (SELECT COUNT(*) FROM dwh.fact_job_posting) AS total_job_postings,
    (SELECT COUNT(DISTINCT company_id) FROM dwh.fact_job_posting) AS total_companies,
    (SELECT ROUND(
        100.0 * COUNT(*) FILTER (WHERE work_mode = 'remote') / NULLIF(COUNT(*), 0), 1
     ) FROM dwh.fact_job_posting) AS pct_remote,
    (SELECT COUNT(*) FROM dwh.dim_skill) AS total_skills,
    (SELECT MAX(date_last_seen) FROM dwh.fact_job_posting) AS last_update;