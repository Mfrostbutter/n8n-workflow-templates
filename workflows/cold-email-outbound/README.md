# Cold Email Outbound (AI-written, sequenced drip)

> The outbound half of the cold-lead system. Take a table of scored, verified cold leads and work it: email the best ones on a follow-up sequence, have an AI model write each message so it reads human instead of templated, stop the moment someone replies, bounces, or unsubscribes, and hand replies off to your CRM.

[![Built by Agenius AI Labs](https://img.shields.io/badge/Built%20by-Agenius%20AI%20Labs-0033ff)](https://ageniuslabs.com) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This is the continuation of the [**cold-lead pipeline**](../apollo-lead-enrichment/), which scrapes, enriches, scores, and reveals leads into `cold_outreach.gms_leads_enriched`. That table is the input here. You can point this template at any Postgres table of verified-email leads; the lead pipeline is just how those leads get there.

It keeps the same rule the lead pipeline is built on: the cold-lead table is a staging area, and a lead only becomes a CRM contact when they reply.

Three n8n workflows plus a short list of platforms to connect. Nothing here is baked in; you bring your own accounts and attach your own credentials.

## Prerequisites: the platforms, and why each one is here

| Platform | What it is | Why we use it | Where to get it |
|---|---|---|---|
| **Postgres** | The same database your cold-lead pipeline writes to. | Stores the outbound state, the send log, and the suppression (do-not-email) list. Same database, four more tables. | The [cold-lead pipeline](../apollo-lead-enrichment/) sets it up; any Postgres 12+ works. |
| **ListMonk** | A self-hosted, open-source newsletter and list manager. | It holds your subscribers, owns the unsubscribe link and the open/click tracking, and exposes a transactional send API. It is your compliance layer, so you are not hand-rolling unsubscribe handling. | [listmonk.app](https://listmonk.app) (single Go binary or Docker, self-hosted, free). |
| **Mailgun** | An email delivery service (SMTP and API). | Actual deliverability: it sends the mail, handles your sending domain's SPF / DKIM / DMARC, and emits the bounce and complaint events Part 4c listens for. ListMonk relays through it. | [mailgun.com](https://www.mailgun.com) (free tier to start; a paid plan for real volume). |
| **An LLM API** | A large language model, Anthropic by default. | Writes every email fresh from the lead's real details and the step's intent, so outreach reads like a person wrote it. A fixed template blasted to hundreds of people is what reads cold. | [anthropic.com](https://www.anthropic.com) for an API key. Swappable to OpenAI, a local model, or anything with a chat API by editing one node. |
| **An IMAP mailbox** | The inbox you send from (Google Workspace, Microsoft 365, Fastmail, anything with IMAP). | Part 4c watches it so a reply instantly stops that lead's sequence and promotes them. | Your existing email provider. Use the same address you send from. |
| **A CRM** | Where a lead goes once they reply. | Replies are the only thing that crosses into your CRM. See the CRM section below. | See below; several plug in directly. |

### Why this stack

ListMonk plus Mailgun is a self-hostable, low-cost pairing where each tool does one job well.
ListMonk manages lists, subscribers, unsubscribe, and tracking; Mailgun handles raw
deliverability and domain authentication. Both are swappable: any SMTP provider works behind
ListMonk, and any provider with a transactional API can replace ListMonk. The LLM is a plain
HTTP call, so the model and even the vendor are a one-node change. Nothing locks you in.

## The three workflows

- **`4a-outbound-enroller.json`** picks your best unworked leads (verified email, score above
  your floor, not already enrolled, not suppressed) and lines them up for the sequence. A
  daily cap ramps volume so a fresh sending domain warms up instead of getting flagged.
- **`4b-outbound-sender.json`** sends the due message for each enrolled lead, on a schedule,
  inside your chosen hours and under a daily cap. The AI model writes each email; ListMonk and
  Mailgun send it; the workflow logs it and schedules the next touch on a 0 / 3 / 5 day drip.
- **`4c-outbound-events.json`** listens for what happens next. A reply stops the sequence and
  promotes the contact to your CRM. A Mailgun bounce, complaint, or unsubscribe stops the
  sequence and adds the address to a permanent do-not-email list.

## Setup

> Deploying with an AI assistant? The cold-lead pipeline's
> [`AI-SETUP-PROMPT.md`](../apollo-lead-enrichment/AI-SETUP-PROMPT.md) covers the outbound part
> too, and will interview you through your offer, your voice, and your sequence.

1. **Create the outbound tables.** Apply [`sql/outbound.sql`](sql/outbound.sql) to the same
   Postgres database your cold-lead pipeline uses. It adds `outreach_state`, `outreach_sends`,
   `suppression`, and `outreach_config` to the `cold_outreach` schema.
2. **Import the three workflows** (`4a`, `4b`, `4c`).
3. **Stand up ListMonk and point it at Mailgun.** In ListMonk, add Mailgun as the SMTP
   messenger. Verify your **dedicated sending subdomain** (for example `go.yourdomain.com`,
   never your main domain) in Mailgun with SPF, DKIM, and DMARC. In ListMonk, create ONE
   transactional template that renders `{{ .Tx.Data.body }}` plus your unsubscribe footer, and
   note its id.
4. **Attach credentials** (none are bundled):
   - **Postgres** on every database node in all three workflows.
   - **ListMonk** (HTTP Basic Auth) on the send nodes.
   - **Your LLM** (Anthropic x-api-key header auth by default) on `generateMessage` in 4b.
   - **IMAP** on `imapTrigger` in 4c (the mailbox you send from).
   - **Your CRM** credential if you use an adapter (see below).
5. **Set your voice and knobs** in each workflow's `config` node: your `offer` and `cta`, your
   `senderName` and `senderCompany`, the `model`, your from name and address, the daily cap and
   send window, the `shellTemplateId`, and the three per-step intent lines. Volume knobs can
   also live in the `outreach_config` table, which wins over `config` when it has a row.
6. **Warm up.** Start `dailySendCap` and `maxNewPerDay` low and raise them over the first weeks.
7. **Go live.** Activate 4a and 4b. For 4c, point Mailgun's event webhook at
   `POST /webhook/mailgun-events` and activate the workflow so the IMAP trigger runs.

## Deliverability: please do not skip this

Cold email is a deliverability game, not a volume game. The workflows default to safe settings,
but the setup around them matters just as much:

- **Dedicated, warmed sending subdomain.** Never your primary domain. Protects your main
  reputation.
- **Low, throttled volume in business hours.** Ramp slowly. A blast gets you flagged.
- **Plain, personalized copy.** The LLM prompt already enforces short, human, no-hype writing
  and forbids invented facts. Keep it that way.
- **Honor opt-out instantly.** One-click unsubscribe and a physical-address footer on every
  send (ListMonk handles this), suppression enforced before every enroll and send.
- **Stay B2B and confirm your Mailgun plan permits it.** Some plans restrict cold or bulk
  sending; check the AUP before your first real send.
- **Add Mailgun signature verification** to the 4c webhook before production, so only Mailgun
  can trigger it.

## CRM integration

Promotion is **reply-triggered only**. When a lead replies, Part 4c stops their sequence and
posts one normalized payload to your CRM:

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

The `promoteToCrm` node ships as a **generic webhook** so it works with anything out of the
box. To wire a specific CRM, either point that webhook at the CRM's inbound hook, or swap the
node for the CRM's own n8n node. A few that plug in directly:

| CRM | How to connect | Notes |
|---|---|---|
| **Generic webhook** (default) | Set `promoteToCrm`'s URL to any endpoint. Point it at another n8n workflow, a Make / Zapier hook, or your own app. | Zero assumptions. The fastest way to start. |
| **HubSpot** | Swap `promoteToCrm` for HubSpot's **Create or update a contact** node, then optionally a **Create deal** node in your pipeline. | Free CRM tier is enough. The email is the dedupe key. |
| **Pipedrive** | Use the Pipedrive node: **Create person**, then **Create lead** or **Create deal**. | Map `first_reply_snippet` into a note on the deal. |
| **Airtable** | Append a row to a "Replies" table with the Airtable node. | Good if you do not run a full CRM yet; keeps replies in one place. |

Whichever you pick, keep the boundary intact: only replies get promoted. Cold leads never
auto-sync, so your CRM stays a list of people who actually engaged.

## Where this fits

- The pipeline that fills the table: the [**cold-lead pipeline**](../apollo-lead-enrichment/) (scrape, enrich, score, reveal, and the viewer).
- The design and data model behind this template: [`docs/spec.md`](docs/spec.md).

## Who built this

[Michael Frostbutter](https://ageniuslabs.com), founder of Agenius AI Labs. 25+ years in network engineering and technology operations.

## License

MIT, see [LICENSE](LICENSE). Use it however you want.
