CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.job_postings_raw (
    staging_id      BIGSERIAL PRIMARY KEY,
    source          VARCHAR(20),
    external_id     VARCHAR(100),
    title           TEXT,
    company_name    TEXT,
    location        TEXT,
    country         VARCHAR(10),
    work_mode       VARCHAR(20),
    salary_min      TEXT,
    salary_max      TEXT,
    job_type        TEXT,
    publication_date TEXT,
    description     TEXT,
    url             TEXT,
    tags            JSONB,
    extracted_at    TEXT,
    loaded_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_staging_source_external_id
    ON staging.job_postings_raw (source, external_id);