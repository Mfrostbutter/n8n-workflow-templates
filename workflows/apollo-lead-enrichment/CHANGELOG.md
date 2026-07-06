# Changelog

All notable changes to the **Apollo lead enrichment** workflow template.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Dates are `YYYY-MM-DD`.

## [2026-07-06]

### Added
- **Part 1, `1-gms-scrape-start.json`** - a form-driven scrape trigger. It records the run, launches the Apify Google Maps actor, and registers Apify's run-finished webhook (base64 `webhooks` query param), so the whole pipeline runs end to end from a single form submission. The template previously shipped only the enrichment half and left the trigger to you.
- **Part 3, `3-manual-reveal.json`** - an optional, token-gated webhook that reveals a single unrevealed contact on demand (Apollo `people/match` + DB update). Not bound by the monthly cap; deliberate one-click-one-credit.
- **`viewer/`** - a lightweight read-only viewer for the cold-lead table. One Python file plus one self-contained HTML page, no framework, no CDN. SELECT-only on a forced read-only connection. With Part 3 wired (`REVEAL_WEBHOOK_URL` + `REVEAL_TOKEN`), it adds a per-row **Reveal** button that relays to the reveal webhook; the viewer never writes the database or holds the Apollo key.

### Changed
- **`viewer/` gained a + New scrape button.** With `SCRAPE_FORM_URL` set to your Part 1 form URL, the header shows a button that opens the n8n form in a popup, so you can start a scrape and watch the leads land without leaving the viewer. The viewer only opens the link; n8n owns the scrape start, so the read-only guarantee holds.
- **Part 2 reveal gate** now evaluates *every* enriched contact in a run, not just the first. It carries a running within-batch counter so the monthly cap still holds exactly.
- **Part 1 form** acks on submit (`responseMode: onReceived`) instead of ending on a completion-page node. n8n held those executions in "Waiting" until a browser fetched the page, so programmatic submits and abandoned tabs piled up unfinished. They now finish cleanly.
- **README + AI-SETUP-PROMPT** rewritten for the two-part import, plus the Apify "unquoted variable" gotcha.

### Fixed
- **`viewer/` 500'd on non-ASCII names.** The database connection decoded text as ASCII, so a firm or contact name with an accented character crashed `/api/leads` (the stat tiles still loaded, the table did not). The connection now forces `client_encoding=UTF8`.
- **Part 2 org enrich was silently returning nothing, which poisoned every lead.** It POSTed a JSON `{domain}` body to `/v1/organizations/enrich`, but Apollo's org enrich is a **GET** with `domain` as a **query param** on `/api/v1/`, so every org came back empty. With no org id, the people search had nothing to scope to and fell back to Apollo's **sample dataset** (the same demo contacts, e.g. "Uros Flere", for every firm). Fixed to `GET /api/v1/organizations/enrich?domain=...`. The ICP scorer now also drops people entirely when Apollo has no org for the domain, so a domain Apollo does not know yields no contacts instead of fake ones. Note: Apollo's people search returns first name + title with the last name and email masked; the reveal step unmasks them.
- **Part 2 people search** endpoint corrected to `https://api.apollo.io/api/v1/mixed_people/api_search` (the older path returned 422).
- **Part 2 dedup** key null-coalesced, so a place with no domain no longer trips a NOT NULL violation.
- **`sql/schema.sql`** - `gms_runs` gained `search_terms`, `location_query`, `max_per_search`, and `apify_dataset_id` so Part 1 can persist a run.

## [2026-07-03]

### Added
- Initial release: Part 2 enrichment, ICP scoring, and credit-gated reveal (`2-apollo-lead-enrichment.json`), `sql/schema.sql`, and `AI-SETUP-PROMPT.md`.
