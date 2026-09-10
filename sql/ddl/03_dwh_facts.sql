-- Table de faits : le cœur du modèle, une ligne par offre unique
-- (dédupliquée par source+external_id, contrairement au staging
-- qui garde tous les doublons de chaque run)
CREATE TABLE IF NOT EXISTS dwh.fact_job_posting (
    job_posting_id  BIGSERIAL PRIMARY KEY,
    source          VARCHAR(20) NOT NULL,
    external_id     VARCHAR(100) NOT NULL,
    title           TEXT NOT NULL,
    company_id      INTEGER REFERENCES dwh.dim_company(company_id),
    city_id         INTEGER REFERENCES dwh.dim_city(city_id),
    work_mode       VARCHAR(20),
    salary_min      NUMERIC(10, 2),
    salary_max      NUMERIC(10, 2),
    job_type        VARCHAR(50),
    seniority_level VARCHAR(20),
    publication_date_id DATE REFERENCES dwh.dim_date(date_id),
    date_first_seen DATE NOT NULL,
    date_last_seen  DATE NOT NULL,
    url             TEXT,
    description     TEXT,

    -- Empêche les doublons : une offre Adzuna #12345 ne peut
    -- exister qu'une seule fois dans la table de faits
    UNIQUE (source, external_id)
);

-- Table de liaison many-to-many : une offre peut avoir plusieurs
-- compétences, une compétence peut apparaître dans plusieurs offres
CREATE TABLE IF NOT EXISTS dwh.bridge_job_skill (
    job_posting_id  BIGINT REFERENCES dwh.fact_job_posting(job_posting_id),
    skill_id        INTEGER REFERENCES dwh.dim_skill(skill_id),
    PRIMARY KEY (job_posting_id, skill_id)
);