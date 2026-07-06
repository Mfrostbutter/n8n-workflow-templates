-- Cold Email Outbound (sequenced, AI-written drip)
-- Additive schema for the outbound pipeline. Apply this to the SAME Postgres
-- database your cold-lead pipeline uses. It adds four tables to the existing
-- `cold_outreach` schema and touches nothing the lead pipeline created, so an
-- existing deployment can run it safely.
--
-- Depends on cold_outreach.gms_leads_enriched (created by the cold-lead
-- pipeline's schema.sql). Run that first.
--
-- Tables:
--   outreach_state   : one row per enrolled lead, tracks the sequence position
--   outreach_sends   : append-only log, one row per delivered touch (audit + event match)
--   suppression      : global do-not-contact list, checked before every enroll and send
--   outreach_config  : single-row volume/timing knobs (optional; the n8n Config node also holds these)

CREATE SCHEMA IF NOT EXISTS cold_outreach;

-- One row per enriched lead that has entered the outbound sequence.
CREATE TABLE IF NOT EXISTS cold_outreach.outreach_state (
  lead_id                bigint PRIMARY KEY
                           REFERENCES cold_outreach.gms_leads_enriched(id),
  campaign               text        NOT NULL DEFAULT 'default',
  status                 text        NOT NULL DEFAULT 'in_sequence',
                           -- in_sequence | replied | bounced | unsubscribed | completed | suppressed
  sequence_step          integer     NOT NULL DEFAULT 0,   -- next step index to send (0-based)
  next_send_at           timestamptz,                      -- when the next touch is due; null = nothing scheduled
  last_sent_at           timestamptz,
  listmonk_subscriber_id bigint,                           -- the upserted ListMonk subscriber
  enrolled_at            timestamptz NOT NULL DEFAULT now(),
  replied_at             timestamptz,
  bounced_at             timestamptz,
  unsubscribed_at        timestamptz,
  completed_at           timestamptz
);

CREATE INDEX IF NOT EXISTS idx_outreach_due
  ON cold_outreach.outreach_state (status, next_send_at);

-- Append-only log, one row per delivered touch. This is the audit trail and the
-- key 4c matches inbound events back to a lead.
CREATE TABLE IF NOT EXISTS cold_outreach.outreach_sends (
  id                  bigserial   PRIMARY KEY,
  lead_id             bigint      REFERENCES cold_outreach.gms_leads_enriched(id),
  campaign            text,
  step                integer,
  subject             text,
  sent_at             timestamptz NOT NULL DEFAULT now(),
  provider_message_id text,       -- ListMonk/Mailgun message id, for reply + event matching
  status              text        -- sent | failed
);

CREATE INDEX IF NOT EXISTS idx_outreach_sends_lead
  ON cold_outreach.outreach_sends (lead_id);

CREATE INDEX IF NOT EXISTS idx_outreach_sends_sent_at
  ON cold_outreach.outreach_sends (sent_at);

-- Global do-not-contact. Checked at select time in 4a and 4b so a suppressed
-- address is never emailed, even across campaigns or re-scrapes.
CREATE TABLE IF NOT EXISTS cold_outreach.suppression (
  email         text        PRIMARY KEY,
  reason        text        NOT NULL,   -- replied | bounced | complaint | unsubscribed | manual
  suppressed_at timestamptz NOT NULL DEFAULT now()
);

-- Single-row knobs. Can also live in the n8n Config node; the table version lets
-- you tune volume without editing the workflow. When a row exists, the workflows
-- prefer it over the Config node defaults.
CREATE TABLE IF NOT EXISTS cold_outreach.outreach_config (
  id                integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  campaign          text    NOT NULL DEFAULT 'default',
  min_score         integer NOT NULL DEFAULT 60,  -- only email leads scoring at or above this
  daily_send_cap    integer NOT NULL DEFAULT 40,  -- max sends per day (raise slowly during warmup)
  max_new_per_day   integer NOT NULL DEFAULT 20,  -- max new enrollments per day (warmup ramp)
  send_window_start integer NOT NULL DEFAULT 9,   -- local hour, inclusive
  send_window_end   integer NOT NULL DEFAULT 16,  -- local hour, exclusive
  min_gap_seconds   integer NOT NULL DEFAULT 90   -- throttle between individual sends
);

-- Seed the single config row with the defaults. Edit these values (or the n8n
-- Config node) to tune your campaign. Start the caps low and ramp over weeks.
INSERT INTO cold_outreach.outreach_config (id) VALUES (1)
  ON CONFLICT (id) DO NOTHING;
