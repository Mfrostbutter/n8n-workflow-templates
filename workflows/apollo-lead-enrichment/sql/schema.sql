-- Lead Enrichment - Apollo (credit-aware)
-- Postgres schema for the cold-lead pipeline.
--
-- Run this once against your database before importing the workflow. It creates
-- a dedicated `cold_outreach` schema and four tables:
--   gms_runs           - one row per scrape run (you create the row, pass its id as run_pk)
--   seen_leads         - dedup ledger so a business is never enriched or contacted twice
--   gms_leads_raw      - raw normalized rows from the Google Maps scrape
--   gms_leads_enriched - Apollo-enriched contacts + ICP score (this is your cold-lead table)
--
-- Point the workflow's Postgres credential at this database. Every query in the
-- workflow is schema-qualified (cold_outreach.*), so no search_path change is needed.

CREATE SCHEMA IF NOT EXISTS cold_outreach;

-- ---------------------------------------------------------------------------
-- Runs: one row per scrape. Create this row BEFORE you start the Apify actor,
-- then pass its id to the workflow webhook as run_pk. The workflow flips status
-- to 'failed' if the Apify run did not succeed.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cold_outreach.gms_runs (
  id            bigserial PRIMARY KEY,
  vertical      text,                       -- free-form label for what you scraped, e.g. "hvac_nj"
  apify_run_id  text,
  dataset_id    text,
  status        text        NOT NULL DEFAULT 'running',  -- running | succeeded | failed
  error_message text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  completed_at  timestamptz
);

-- ---------------------------------------------------------------------------
-- Seen ledger: the dedup key is (canonical_domain, place_id). The workflow
-- upserts here first; only rows that are new (xmax = 0) continue down the flow.
-- This is what stops you re-enriching and re-emailing the same business.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cold_outreach.seen_leads (
  canonical_domain text        NOT NULL,
  place_id         text        NOT NULL,
  first_run_id     bigint,
  first_seen_at    timestamptz NOT NULL DEFAULT now(),
  last_seen_at     timestamptz NOT NULL DEFAULT now(),
  seen_count       integer     NOT NULL DEFAULT 1,
  PRIMARY KEY (canonical_domain, place_id)
);

-- ---------------------------------------------------------------------------
-- Raw leads: the normalized Google Maps rows. raw_payload keeps the full scrape
-- object so you never lose a field you did not map.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cold_outreach.gms_leads_raw (
  id                bigserial PRIMARY KEY,
  run_id            bigint,
  place_id          text,
  canonical_domain  text,
  firm_name         text,
  firm_short_name   text,
  website           text,
  phone             text,
  email             text,
  address           text,
  city              text,
  state             text,
  postal_code       text,
  category          text,
  rating            numeric,
  reviews_count     integer,
  permanently_closed boolean DEFAULT false,
  raw_payload       jsonb,
  enrichment_status text,        -- null | enriched | skipped
  enrichment_error  text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, place_id)
);

-- ---------------------------------------------------------------------------
-- Enriched leads: THIS is your cold-lead table. One row per Apollo contact.
-- email_status starts as 'unrevealed' and only becomes a real email for the
-- highest-conviction contacts the reveal gate chose to spend a credit on.
--
-- Cold leads are unqualified. Keep this table OUT of your CRM. Run outbound off
-- it, log the sends, and promote a lead into your CRM only when they REPLY.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cold_outreach.gms_leads_enriched (
  id                    bigserial PRIMARY KEY,
  raw_id                bigint,
  run_id                bigint,
  canonical_domain      text,
  firm_name             text,
  firm_short_name       text,
  apollo_org_id         text,
  employee_count        integer,
  industry              text,
  practice_area         text,        -- the business category / focus (any vertical)
  linkedin_url          text,
  apollo_person_id      text,
  first_name            text,
  last_name             text,
  title                 text,
  seniority             text,
  email                 text,
  email_status          text,        -- unrevealed | verified | guessed | no_contact_found | unknown
  phone                 text,
  person_linkedin_url   text,
  icp_score             integer     NOT NULL DEFAULT 0,
  icp_reasons           jsonb       NOT NULL DEFAULT '{}'::jsonb,
  apollo_org_payload    jsonb,
  apollo_person_payload jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (canonical_domain, apollo_person_id)
);

-- The monthly reveal cap is enforced by counting verified reveals in the current
-- calendar month, so this index keeps that count fast.
CREATE INDEX IF NOT EXISTS idx_enriched_status_created
  ON cold_outreach.gms_leads_enriched (email_status, created_at);

CREATE INDEX IF NOT EXISTS idx_enriched_score
  ON cold_outreach.gms_leads_enriched (icp_score DESC);
