# Agenius3D — Social Media Pipeline

A fully automated social content engine for a maker/3D-printing brand. On a schedule, it picks the next content type in a 12-post Instagram grid cycle, writes a caption + image prompt with Claude Haiku, generates an original image, publishes to Facebook + Instagram, logs everything to Airtable, and pings you on Telegram.

Runs ~10 posts/week with zero manual effort. Cost is dominated by image generation (a few cents per post) plus a fraction of a cent for the Haiku call.

![Workflow](assets/workflow.png)

## Flow

```
Schedule / Manual
  → Fetch last cycle position (Airtable)
  → Config (brand, image specs, cycle logic)
  → Fetch recent posts (Airtable, for topic dedup)
  → Route by content type  →  Tips | Models | Design | Tech | Art
       each branch: Generate (Claude Haiku) → Parse
  → Merge into one publish pipeline
  → KIE.ai image gen (create → wait → poll → check → route)
  → Facebook photo post → Instagram container → publish
  → Log to Airtable
  → Telegram success notification
```

The key design decision: all five content branches merge into **one** shared publish pipeline instead of duplicating the image-gen → publish → log chain five times. That keeps it at ~40 nodes instead of 100+.

## What you need

- n8n (self-hosted or Cloud)
- **Anthropic** API key (Claude Haiku writes the content)
- **KIE.ai** API key (image generation, this is where most of the per-post cost lands)
- **Meta Graph API** access token for a Facebook Page linked to an Instagram Business account
- **Airtable** account (content cycle state + published-post log)
- **Telegram** bot (notifications) — or swap these two nodes for Slack, see below

## Setup

### 1. Import
`agenius3d-social-media-pipeline.json` → **Import from File** in n8n.

### 2. Attach credentials (none are bundled)
- **Anthropic** on the five `Generate * Content` nodes.
- **HTTP Bearer Auth** (your KIE.ai key) on `KIE Create` and `KIE Poll`.
- **Telegram** on `KIE Error` and `Success Notification`.

### 3. Set n8n variables (Settings → Variables)
- `AIRTABLE_PAT` — Airtable personal access token
- `META_PAGE_ACCESS_TOKEN` — long-lived Meta Page access token

### 4. Fill the placeholders
In the **Config** node, replace:
- `YOUR_TELEGRAM_CHAT_ID`
- `YOUR_AIRTABLE_BASE_ID`, `YOUR_AIRTABLE_TABLE_ID`
- `YOUR_META_PAGE_ID`, `YOUR_META_IG_USER_ID`

Then replace `YOUR_AIRTABLE_BASE_ID` / `YOUR_AIRTABLE_TABLE_ID` in the URLs of the three Airtable HTTP nodes (`Fetch Last Record`, `Fetch Past Topics`, `Log to Airtable`).

### 5. Create the Airtable table
Import [`airtable/content-table.csv`](airtable/content-table.csv) into your base to stand up the table in one click, then set the field types per [`airtable/SCHEMA.md`](airtable/SCHEMA.md). The table tracks published posts and drives the cycle/dedup logic.

### 6. Activate
The schedule fires at 10am and 3pm (cron `0 0 10,15 * * *`, server timezone). Use the **Manual Trigger** to test a single run first.

## Customize

- **Slack instead of Telegram:** swap the two Telegram nodes (`KIE Error`, `Success Notification`) for a Slack node or an HTTP POST to an incoming webhook. Everything upstream is unchanged.
- **The grid cycle** lives in the `Config` node's `cycle` array. Reorder or resize it to change what posts when.
- **Content voice + topics** live in each `Generate * Content` node's system prompt.
- **Image specs** (model, aspect ratio, resolution) are in `Config` (`kieModel`, `kieAspectRatio`, `kieResolution`).

## Notes

- This is the published/sanitized version: an internal logging node and a dashboard webhook trigger were removed, and all account IDs, chat IDs, and credentials were replaced with placeholders. Triggers are schedule + manual only.
- The KIE poll loop caps at 30 attempts (~2.5 min) then routes to a Telegram error alert, so it never hangs forever.

## License

MIT
