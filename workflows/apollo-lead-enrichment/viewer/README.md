# Cold-lead viewer

A lightweight, read-only web view over the `cold_outreach` Postgres schema this
workflow writes to. Two files: a single Python server (`app.py`) and a single
self-contained HTML page (`index.html`). No build step, no framework, no CDN.

It is strictly read-only. Every database connection is opened `readonly=True` and
the server only ever issues `SELECT` queries, so nothing here can change your data.

![viewer](assets/viewer.png)

## What you get

- Stat tiles: total leads, distinct firms, revealed contacts, credits spent this
  calendar month (mirrors the workflow's monthly cap logic), unrevealed count,
  average and top ICP score.
- A filterable, sortable table of `gms_leads_enriched` (your cold-lead table):
  search by firm / domain / name / title, filter by minimum ICP score, email
  status, or scrape run, and toggle "revealed only".
- Click any row to expand the ICP score reasons and the raw Apollo org/person
  payloads.

## Run it

Requires Python 3.8+ and `psycopg2`:

```bash
pip install psycopg2-binary
```

Point it at the same database the workflow uses, then start it:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
python3 app.py
# -> http://127.0.0.1:8787
```

`DATABASE_URL` is optional; if unset, the standard `PGHOST` / `PGPORT` /
`PGDATABASE` / `PGUSER` / `PGPASSWORD` variables are used instead.

### Options

| Env var | Default | Purpose |
|---|---|---|
| `VIEWER_PORT` | `8787` | Port to serve on. |
| `VIEWER_TOKEN` | (none) | If set, API calls require `?token=...`. A thin gate for when you expose it on a LAN or private mesh. Open the page as `http://host:8787/?token=YOURTOKEN`. |
| `REVEAL_WEBHOOK_URL` | (none) | If set, the viewer shows a **Reveal** button next to unrevealed contacts. Clicking it POSTs the lead id to the viewer, which relays it (with `REVEAL_TOKEN`) to your Part 3 `manual-reveal` webhook. Leave unset to keep the viewer strictly read-only. |
| `REVEAL_TOKEN` | (none) | Shared secret forwarded to the reveal webhook. Must match `REVEAL_TOKEN` in Part 3's Config node. Stays server-side; never sent to the browser. |

## Revealing on demand (optional)

Part 2 leaves most contacts unrevealed. If you deploy Part 3 (`3-manual-reveal.json`) and set `REVEAL_WEBHOOK_URL` + `REVEAL_TOKEN`, each unrevealed row gets a **Reveal** button. The reveal itself (the Apollo call and the database write) happens in n8n, not here: the viewer only relays the request. Its own database connection is still opened `readonly=True` and only ever runs `SELECT`, so the read-only guarantee holds even with reveal enabled.

The server binds to `127.0.0.1` (localhost only). To reach it from another
machine, front it with your own reverse proxy / mesh (e.g. a private overlay
network) and set `VIEWER_TOKEN`. Do not put it on the public internet as-is: it
is a read-only viewer, not an authenticated app.

## Notes

- Read-only by construction: `app.py` forces `readonly=True` sessions and runs
  only SELECTs. Safe to point at your production leads database.
- Schema-qualified queries (`cold_outreach.*`), matching the workflow, so no
  `search_path` change is needed.
- Heavy `jsonb` payloads load only when you expand a row, keeping the grid fast
  on large tables.
