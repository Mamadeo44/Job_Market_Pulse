CREATE SCHEMA IF NOT EXISTS datamart;

-- Vue 1 : demande par compétence, avec pourcentage du total des offres
-- Utile pour un graphique en barres "top compétences demandées"
CREATE OR REPLACE VIEW datamart.mart_skill_demand AS
SELECT
    s.skill_name,
    COUNT(DISTINCT b.job_posting_id) AS nb_offres,
    ROUND(
        100.0 * COUNT(DISTINCT b.job_posting_id) / (SELECT COUNT(*) FROM dwh.fact_job_posting),
        1
    ) AS pct_du_total
FROM dwh.bridge_job_skill b
JOIN dwh.dim_skill s ON b.skill_id = s.skill_id
GROUP BY s.skill_name
ORDER BY nb_offres DESC;

-- Vue 2 : répartition par séniorité, globale
-- Utile pour un graphique en camembert/donut
CREATE OR REPLACE VIEW datamart.mart_seniority_distribution AS
SELECT
    seniority_level,
    COUNT(*) AS nb_offres,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_du_total
FROM dwh.fact_job_posting
GROUP BY seniority_level
ORDER BY nb_offres DESC;

-- Vue 3 : répartition géographique (pays + ville), avec source
-- Utile pour une carte ou un graphique empilé par pays
CREATE OR REPLACE VIEW datamart.mart_geography_demand AS
SELECT
    co.country_name,
    ci.city_name,
    f.source,
    COUNT(*) AS nb_offres
FROM dwh.fact_job_posting f
LEFT JOIN dwh.dim_city ci ON f.city_id = ci.city_id
LEFT JOIN dwh.dim_country co ON ci.country_id = co.country_id
GROUP BY co.country_name, ci.city_name, f.source
ORDER BY nb_offres DESC;

-- Bonus : croisement compétence x séniorité, pour répondre à
-- "quels outils sont plus demandés chez les seniors vs les autres ?"
CREATE OR REPLACE VIEW datamart.mart_skill_by_seniority AS
SELECT
    s.skill_name,
    f.seniority_level,
    COUNT(*) AS nb_offres
FROM dwh.bridge_job_skill b
JOIN dwh.dim_skill s ON b.skill_id = s.skill_id
JOIN dwh.fact_job_posting f ON b.job_posting_id = f.job_posting_id
GROUP BY s.skill_name, f.seniority_level
ORDER BY s.skill_name, nb_offres DESC;