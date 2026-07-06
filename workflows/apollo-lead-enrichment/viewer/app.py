#!/usr/bin/env python3
"""
Cold-lead viewer: a read-only HTML wrapper over the cold_outreach Postgres schema.

Serves a single dashboard page plus a small JSON API that runs SELECT-only queries
against the same database the n8n workflow writes to. Nothing here can mutate data:
every connection is forced read-only, and only SELECTs are issued.

Run:
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"   # or set PG* vars
    python3 app.py                      # serves http://127.0.0.1:8787

Optional:
    VIEWER_TOKEN=secret python3 app.py  # require ?token=secret (thin gate for LAN use)
    VIEWER_PORT=9000 python3 app.py

Dependency: psycopg2 (pip install psycopg2-binary).
"""

import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import psycopg2
import psycopg2.extras

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("VIEWER_PORT", "8787"))
TOKEN = os.environ.get("VIEWER_TOKEN", "")

# Optional manual-reveal relay. If REVEAL_WEBHOOK_URL is set, the viewer exposes a
# Reveal button that POSTs the lead id here; this server forwards it (with the
# shared token, kept server-side) to your n8n manual-reveal webhook, which does
# the Apollo call and the DB write. The viewer's own DB connection stays
# read-only; it never writes your database.
REVEAL_URL = os.environ.get("REVEAL_WEBHOOK_URL", "")
REVEAL_TOKEN = os.environ.get("REVEAL_TOKEN", "")

# Columns exposed to the table view. Heavy jsonb payloads are fetched only on the
# per-lead detail call, never in the list, to keep the grid fast.
LEAD_COLS = [
    "id", "run_id", "canonical_domain", "firm_name", "firm_short_name",
    "first_name", "last_name", "title", "seniority", "industry", "practice_area",
    "email", "email_status", "phone", "person_linkedin_url", "linkedin_url",
    "employee_count", "icp_score", "created_at",
]

SORTS = {
    "score":   "icp_score DESC NULLS LAST, created_at DESC",
    "newest":  "created_at DESC",
    "oldest":  "created_at ASC",
    "firm":    "firm_name ASC",
}


def connect():
    """One read-only connection per request. Read-only is belt-and-suspenders on
    top of only ever issuing SELECTs."""
    dsn = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(dsn) if dsn else psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "postgres"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn


def q_stats(cur):
    cur.execute("""
        SELECT
          count(*)                                                         AS total_leads,
          count(*) FILTER (WHERE email_status = 'verified')                AS revealed,
          count(*) FILTER (WHERE email_status = 'unrevealed')              AS unrevealed,
          count(*) FILTER (WHERE email_status = 'verified'
                             AND date_trunc('month', created_at)
                               = date_trunc('month', now()))               AS credits_this_month,
          count(DISTINCT canonical_domain)                                 AS distinct_firms,
          round(avg(icp_score))                                            AS avg_score,
          max(icp_score)                                                   AS max_score
        FROM cold_outreach.gms_leads_enriched;
    """)
    return dict(cur.fetchone())


def q_runs(cur):
    # Only id / vertical / status / lead_count are used by the UI (the run
    # filter dropdown), so no timestamp column is selected. That also keeps this
    # tolerant of schema variants where gms_runs uses started_at vs created_at.
    cur.execute("""
        SELECT r.id, r.vertical, r.status,
               count(e.id) AS lead_count
        FROM cold_outreach.gms_runs r
        LEFT JOIN cold_outreach.gms_leads_enriched e ON e.run_id = r.id
        GROUP BY r.id
        ORDER BY r.id DESC
        LIMIT 200;
    """)
    return [dict(row) for row in cur.fetchall()]


def q_leads(cur, params):
    where, args = [], []

    term = (params.get("q", [""])[0] or "").strip()
    if term:
        where.append("(firm_name ILIKE %s OR canonical_domain ILIKE %s "
                     "OR first_name ILIKE %s OR last_name ILIKE %s OR title ILIKE %s)")
        args += ["%" + term + "%"] * 5

    min_score = params.get("min_score", [""])[0]
    if min_score not in ("", None):
        where.append("icp_score >= %s")
        args.append(int(min_score))

    status = params.get("status", [""])[0]
    if status:
        where.append("email_status = %s")
        args.append(status)

    run_id = params.get("run_id", [""])[0]
    if run_id:
        where.append("run_id = %s")
        args.append(int(run_id))

    if params.get("revealed", [""])[0] == "1":
        where.append("email_status = 'verified' AND email IS NOT NULL")

    order = SORTS.get(params.get("sort", ["score"])[0], SORTS["score"])
    limit = min(int(params.get("limit", ["100"])[0] or 100), 500)
    offset = int(params.get("offset", ["0"])[0] or 0)

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    cur.execute(
        "SELECT count(*) AS n FROM cold_outreach.gms_leads_enriched " + clause, args)
    total = cur.fetchone()["n"]

    cur.execute(
        "SELECT " + ", ".join(LEAD_COLS) +
        " FROM cold_outreach.gms_leads_enriched " + clause +
        " ORDER BY " + order + " LIMIT %s OFFSET %s",
        args + [limit, offset])
    rows = [dict(r) for r in cur.fetchall()]
    return {"total": total, "limit": limit, "offset": offset, "rows": rows}


def q_lead_detail(cur, lead_id):
    cur.execute("""
        SELECT id, icp_score, icp_reasons, apollo_org_payload, apollo_person_payload
        FROM cold_outreach.gms_leads_enriched WHERE id = %s;
    """, [lead_id])
    row = cur.fetchone()
    return dict(row) if row else None


def forward_reveal(lead_id):
    """Relay a reveal request to the n8n manual-reveal webhook. The token stays
    server-side (never sent to the browser). Returns the webhook's JSON verbatim."""
    payload = json.dumps({"lead_id": lead_id, "token": REVEAL_TOKEN}).encode("utf-8")
    req = urllib.request.Request(
        REVEAL_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "cold-lead-viewer"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": "reveal webhook returned %d" % e.code}
    except Exception as e:  # noqa: BLE001 - surface any relay failure to the UI
        return {"ok": False, "error": str(e)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet console
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str), "application/json")

    def do_GET(self):
        u = urlparse(self.path)
        params = parse_qs(u.query)

        if TOKEN and params.get("token", [""])[0] != TOKEN and u.path != "/":
            return self._json({"error": "unauthorized"}, 401)

        if u.path == "/" or u.path == "/index.html":
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                return self._send(500, b"index.html missing", "text/plain")

        try:
            conn = connect()
        except Exception as e:
            return self._json({"error": "db connect failed: " + str(e)}, 500)

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if u.path == "/api/stats":
                    return self._json({"stats": q_stats(cur), "runs": q_runs(cur),
                                       "reveal_enabled": bool(REVEAL_URL)})
                if u.path == "/api/leads":
                    return self._json(q_leads(cur, params))
                if u.path == "/api/lead":
                    lid = params.get("id", [""])[0]
                    if not lid:
                        return self._json({"error": "id required"}, 400)
                    d = q_lead_detail(cur, int(lid))
                    return self._json(d or {"error": "not found"}, 200 if d else 404)
                return self._json({"error": "not found"}, 404)
        except Exception as e:
            return self._json({"error": str(e)}, 500)
        finally:
            conn.close()

    def do_POST(self):
        u = urlparse(self.path)
        params = parse_qs(u.query)
        if TOKEN and params.get("token", [""])[0] != TOKEN:
            return self._json({"error": "unauthorized"}, 401)
        if u.path != "/api/reveal":
            return self._json({"error": "not found"}, 404)
        if not REVEAL_URL:
            return self._json(
                {"error": "reveal not configured; set REVEAL_WEBHOOK_URL"}, 400)
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            return self._json({"error": "bad request body"}, 400)
        lead_id = body.get("lead_id")
        if lead_id is None:
            return self._json({"error": "lead_id required"}, 400)
        return self._json(forward_reveal(lead_id))


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    gate = " (token required)" if TOKEN else ""
    print("Cold-lead viewer on http://127.0.0.1:%d%s  [Ctrl-C to stop]" % (PORT, gate))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
