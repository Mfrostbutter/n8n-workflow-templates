# Airtable table schema

The workflow reads from and writes to a single Airtable table. You can stand it up in one click by importing [`content-table.csv`](content-table.csv), then set the field types below (CSV import defaults every field to single line text).

## Import

1. In Airtable, open your base → **Add a table → Import data → CSV file** → upload `content-table.csv`.
2. Delete the sample row.
3. Adjust the field types to match the table below (especially the single-selects and the date/number fields).
4. Copy the **base ID** (`app…`) and **table ID** (`tbl…`) from the URL into the workflow's `Config` node and the three Airtable HTTP nodes.

## Fields

| Field | Airtable type | Notes |
|---|---|---|
| **Content Title** | Single line text | Primary field |
| **Type** | Single select | Options: `Tips`, `Models`, `Design`, `Tech`, `Art` |
| **Status** | Single select | The workflow writes `Published` |
| **Post Date** | Date | Used to sort for the dedup + cycle lookups |
| **Cycle Position** | Number (integer) | `0`–`11`. Drives the 12-post IG grid cycle; the workflow reads the last value and advances it |
| **Output Type** | Single select | The workflow writes `photo` |
| **Generation Source** | Single select | The workflow writes `live_v3` |
| **Image Prompt** | Long text | The AI-generated image prompt (also used for topic dedup) |
| **KIE Task ID** | Single line text | KIE.ai task ID, for debugging |
| **IG Post ID** | Single line text | Instagram post ID returned after publishing |
| **Source Image** | URL | Generated image URL (KIE URLs are temporary) |
| **Script/Caption** | Long text | The published caption |

Single-select option lists will auto-populate as the workflow writes new values, or you can pre-create them from the notes above.
