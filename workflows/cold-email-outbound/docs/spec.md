# Part 4: outbound sequencer (design spec)

Status: BUILT. Ships as the `cold-email-outbound` template, a sibling to the
cold-lead pipeline. This document is the design record for the workflow group that
turns the cold-lead table into an automated, compliant cold-email pipeline.

## Where it sits

Parts 1 to 3 fill and manage the cold-lead table:

- **Part 1** starts a scrape and wires the completion webhook.
- **Part 2** enriches, scores against your ICP, and reveals emails under a credit cap.
- **Part 3** reveals a single lead on demand.
- **Part 4 (this spec)** reads the gated leads, emails them on a sequenced drip,
  logs every touch, stops on reply, and promotes repliers into your CRM.

Together with the cold-lead pipeline this makes a full cold-outreach system: scrape,
enrich, score, reveal, send, follow up, hand off. It ships as its own template folder
(`cold-email-outbound`) rather than as a section of the lead pipeline, so each half
imports and runs on its own.

## Non-negotiable design principles

1. **The enriched table stays a cold-lead staging table, never a CRM.** Part 4 reads
   from it and logs outbound state next to it. A lead only crosses into a CRM when it
   replies. This is the same rule Parts 1 to 3 are built on.
2. **Cold email is a deliverability game, not a volume game.** Every knob below exists
   to protect the sending reputation: dedicated warmed subdomain, low throttled daily
   volume, business-hours window, plain-text-first personalized copy, hard reply-stop,
   one-click unsubscribe, enforced suppression. If it ever behaves like a bulk newsletter
   blast, it fails.
3. **B2B, opt-out-honored, footer-compliant.** One-click unsubscribe, a physical-address
   footer, immediate suppression on opt-out. Users are responsible for the lawful basis in
   their jurisdiction; the template makes compliant sending the default, not an add-on.
4. **Everything pluggable and credential-free in the repo.** No hardcoded domains, keys,
   CRM, or endpoints. All of it is user-supplied config, same as Parts 1 to 3.

## The two tools, and who does what

- **n8n** owns the sequence: eligibility, timing, step advancement, reply-stop, throttle.
- **An LLM writes each email.** A fixed template blasted to everyone reads cold and
  fingerprints as bulk. Instead, each send is written fresh by a model from the lead's
  facts and the step's intent, in the user's voice. Default is the Anthropic Messages
  API called over plain HTTP (matching how Parts 1 to 3 call Apollo), with the model as
  a config value so it swaps to any provider by editing one node. The prompt forbids
  inventing facts and forces a strict `{subject, body}` JSON reply; a parse failure falls
  back to a simple deterministic note so a touch still goes out.
- **ListMonk** is the send surface: it holds the subscribers (so unsubscribe and tracking
  have something to attach to) and exposes the transactional send API. Each send is a
  ListMonk `/api/tx` call against ONE shell template that just renders the generated
  `body` plus the unsubscribe footer. ListMonk stays the compliance layer; the LLM only
  fills the content.
- **Mailgun** is pure transport: ListMonk relays through Mailgun as its SMTP messenger.
  Mailgun also emits the delivery events (bounce, complaint) that Part 4c consumes.

n8n never talks SMTP directly. It writes the email with the LLM, calls ListMonk, and
ListMonk sends through Mailgun.

## Data model extension

Additive only. Ships as a separate `sql/outbound.sql` so existing deployments run it
without touching the Part 1 to 3 `schema.sql`. All tables live in the existing
`cold_outreach` schema.

```sql
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
-- key Part 4c matches inbound events back to a lead.
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

-- Global do-not-contact. Checked at select time in 4a and 4b so a suppressed
-- address is never emailed, even across campaigns or re-scrapes.
CREATE TABLE IF NOT EXISTS cold_outreach.suppression (
  email         text        PRIMARY KEY,
  reason        text        NOT NULL,   -- replied | bounced | complaint | unsubscribed | manual
  suppressed_at timestamptz NOT NULL DEFAULT now()
);

-- Single-row knobs. Can also live in the n8n Config node; the table version lets
-- you tune without editing the workflow.
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
```

The sequence itself (steps, delays, subjects, template ids) is defined as JSON in the
Config node, not in the schema, so a user edits one node to change their cadence:

Each step is an **intent line** the model writes to, not a fixed subject. One shell
ListMonk template renders every step, so there is only one template id (in `config` as
`shellTemplateId`), not one per step.

```json
{
  "sequence": [
    { "step": 0, "delay_days": 0, "angle": "Warm first-touch intro. Note what they do, one sentence on the offer, a soft ask to reply." },
    { "step": 1, "delay_days": 3, "angle": "Short friendly follow-up. Add one concrete benefit. No pressure." },
    { "step": 2, "delay_days": 5, "angle": "Brief, gracious breakup note. Last check-in, easy to say no or yes." }
  ]
}
```

## The three workflows

### 4a Enroller (scheduled, e.g. every hour)

1. **Read config** (min_score, max_new_per_day, campaign).
2. **Select eligible leads**: from `gms_leads_enriched` where `email_status = 'verified'`
   AND `icp_score >= min_score` AND `email` is not null AND `email` NOT IN
   `suppression` AND `id` NOT IN `outreach_state`. Order by `icp_score DESC`.
   Limit to remaining `max_new_per_day`.
3. **Upsert ListMonk subscriber** for each (attributes carry the personalization tokens:
   firm, contact, title, domain). Capture `listmonk_subscriber_id`.
4. **Insert `outreach_state`**: status `in_sequence`, step 0, `next_send_at = now()`
   (the Sender applies the window), record the subscriber id.

Warmup: `max_new_per_day` starts small and ramps over the first weeks. Enrollment and
sending caps are separate so a backlog cannot spike volume.

### 4b Sender (scheduled, every few minutes, only inside the send window)

1. **Guard the window**: if the local hour is outside `[send_window_start, send_window_end)`,
   exit. Compute today's remaining budget = `daily_send_cap` minus rows in `outreach_sends`
   since local midnight.
2. **Select due leads**: `outreach_state` where `status = 'in_sequence'` AND
   `next_send_at <= now()`, joined to the lead. Limit to the smaller of remaining budget
   and a per-run batch. Re-check suppression at select time.
3. **Per lead** (throttled by `min_gap_seconds`, with jitter):
   - `prepStep` resolves the current step from the sequence JSON by `sequence_step` and
     builds a short brief: the lead's facts (name, type, site, contact) plus this step's
     intent line.
   - `generateMessage` sends that brief to the LLM, which returns `{subject, body}` in the
     user's voice. `parseMessage` reads it back (falling back to a simple note on failure).
   - Send via ListMonk `/api/tx` (subscriber email + the shell template + the generated
     `subject` and `body`); ListMonk relays through Mailgun.
   - Insert `outreach_sends` (step, subject, status `sent`).
   - Advance: if a next step exists, `sequence_step += 1`,
     `next_send_at = now() + next.delay_days`; else `status = 'completed'`,
     `completed_at = now()`, `next_send_at = null`. Set `last_sent_at`.
   - On send failure: log `status = 'failed'`, leave the step unchanged so it retries
     next run (bounded retry count).

### 4c Event handler (reply + provider events)

Two entry points feeding one set of state transitions:

- **Reply detection (default: IMAP poll of the sending mailbox).** On a new inbound
  message, match it to a lead by from-address (fallback: In-Reply-To / References against
  `outreach_sends.provider_message_id`). On match: set `status = 'replied'`,
  `replied_at = now()`, `next_send_at = null` (stop the sequence), add the address to
  `suppression` with reason `replied`, then **fire CRM promotion**.
- **Mailgun events webhook (bounce, complaint, unsubscribe).** Verify the Mailgun
  signature. On permanent bounce or complaint: `status = 'bounced'`, suppress with the
  matching reason, stop the sequence. On unsubscribe (ListMonk-managed link or Mailgun
  event): `status = 'unsubscribed'`, suppress, stop.

Suppression is enforced at select time in 4a and 4b, so any of these transitions
guarantees no further sends to that address, in this or any future campaign.

## CRM integration (reply-triggered, pluggable)

Promotion fires only from 4c on a reply, the moment a cold lead becomes worth a CRM
record. It is a single normalized step so users can point it at any CRM:

```json
{
  "source": "cold-outreach",
  "firm_name": "...",
  "canonical_domain": "...",
  "contact_first_name": "...",
  "contact_title": "...",
  "email": "...",
  "icp_score": 82,
  "first_reply_snippet": "...",
  "campaign": "default"
}
```

Ship three options behind that contract:

1. **Generic webhook** (default): POST the payload to a user-configured `CRM_WEBHOOK_URL`.
   Zero assumptions, works with anything including another n8n workflow.
2. **HubSpot adapter** (reference): create-or-update contact, then create a deal in a
   configured pipeline stage. First-class adapter because it is the common case.
3. **Room for one more** (Pipedrive or Attio) later, same contract.

Cold leads never auto-sync. Only a reply promotes, and it carries the reply snippet so
the CRM record has context.

## Configuration surface (all user-supplied)

- **Config node**: campaign name, `min_score`, the sequence intent lines, sending
  identity (from-name, from-address on the dedicated subdomain), the `shellTemplateId`,
  the LLM `model`, your `offer` and `cta` (the voice the model writes in), your
  `senderName` and `senderCompany`, physical-address footer, CRM mode (webhook | hubspot),
  CRM target.
- **`outreach_config` table**: the volume and timing knobs (caps, window, throttle).
- **Credentials** (n8n credential store, never inline): Postgres; ListMonk API
  (base URL + user/token); the LLM API (Anthropic x-api-key header auth by default);
  Mailgun (configured as ListMonk's SMTP messenger, plus a Mailgun API key for the
  events webhook signature); IMAP (the reply mailbox); CRM credential if using an adapter.

## Deliverability checklist (setup, documented in AI-SETUP-PROMPT)

- Dedicated sending subdomain (for example `go.yourdomain.com`), never the primary domain.
- SPF, DKIM, DMARC, and Mailgun tracking CNAME all verified on that subdomain.
- Warm the subdomain before real volume: start `daily_send_cap` and `max_new_per_day`
  low, ramp over weeks.
- Plain-text-first templates with real personalization; clicks-only tracking, no open pixel.
- Send window in business hours, throttle + jitter between sends.
- One-click unsubscribe (ListMonk) and a physical-address footer in every template.
- Confirm the Mailgun plan and AUP permit your B2B use before first send.

## Open decisions (resolved unless flagged)

- **Reply detection**: IMAP poll is the shipped default (provider-agnostic). Mailgun
  inbound routing is an optional adapter for users who want push instead of poll.
- **Tracking**: clicks only. No open-pixel.
- **Repo home**: ships as its own `cold-email-outbound` template, a sibling to the
  cold-lead pipeline.
- **Sequence**: three touches at 0 / 3 / 5 days is the shipped default (editable in the
  Config node's `sequenceJson`).
- **Volume knobs**: live in both the Config node and the `outreach_config` table; the
  table wins when a row exists.

## Build order (once approved)

1. `sql/outbound.sql` (the four tables above) and the AI-SETUP-PROMPT additions.
2. 4b Sender first (the core send loop) against a hand-enrolled test lead.
3. 4a Enroller.
4. 4c Event handler (IMAP reply-stop, then Mailgun events, then CRM promotion).
5. Viewer additions: outbound status column, sends count, a per-lead sequence view.
6. README reframe, CHANGELOG, demo screenshots.

## Out of scope (for this version)

- A/B subject testing and per-step analytics beyond the sends log.
- Multi-mailbox rotation and inbox-warmup automation (users can add mailboxes).
- LinkedIn or multi-channel touches. Email only.
