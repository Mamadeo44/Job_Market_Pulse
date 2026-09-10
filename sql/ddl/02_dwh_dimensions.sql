CREATE SCHEMA IF NOT EXISTS dwh;

-- Dimension pays (racine du flocon géographique)
CREATE TABLE IF NOT EXISTS dwh.dim_country (
    country_id      SERIAL PRIMARY KEY,
    country_code    VARCHAR(10) UNIQUE,
    country_name    VARCHAR(100)
);

-- Dimension ville, normalisée : référence dim_country plutôt que
-- de répéter le nom du pays sur chaque ligne (c'est ça, le flocon)
CREATE TABLE IF NOT EXISTS dwh.dim_city (
    city_id         SERIAL PRIMARY KEY,
    city_name       VARCHAR(200),
    country_id      INTEGER REFERENCES dwh.dim_country(country_id),
    UNIQUE (city_name, country_id)
);

-- Dimension entreprise
CREATE TABLE IF NOT EXISTS dwh.dim_company (
    company_id      SERIAL PRIMARY KEY,
    company_name    VARCHAR(255) UNIQUE NOT NULL
);

-- Dimension compétence (référentiel des outils/skills recherchés)
CREATE TABLE IF NOT EXISTS dwh.dim_skill (
    skill_id        SERIAL PRIMARY KEY,
    skill_name      VARCHAR(100) UNIQUE NOT NULL
);

-- Dimension date, calendrier explicite (standard en modélisation
-- dimensionnelle : permet des jointures rapides et des attributs
-- calendaires prêts à l'emploi, ex: nom du jour, semaine ISO)
CREATE TABLE IF NOT EXISTS dwh.dim_date (
    date_id         DATE PRIMARY KEY,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    day             INTEGER NOT NULL,
    week_of_year    INTEGER NOT NULL,
    day_name        VARCHAR(20) NOT NULL
);