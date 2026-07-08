# Document Fabric: Drive to Qdrant Ingest

The ingestion half of a high-accuracy RAG pipeline. Drop a document into a Google Drive folder and it gets normalized, tagged, chunked, embedded, and made searchable in Qdrant, automatically.

![Workflow](assets/workflow.png)

## Flow

```
Google Drive Trigger (new file in folder)
  → Config (sets the Qdrant collection name)
  → Download File
  → MarkItDown Convert (any format → Markdown)
  → Information Extractor (doc-level metadata via a cheap LLM)
  → Assemble Metadata + content hash (Code)
  → Delete existing vectors for this file_id (idempotent upsert)
  → Chunk by Structure (split on Markdown headings, Code)
  → Qdrant Insert  [Default Data Loader + pass-through Splitter + OpenAI Embeddings]
```

## Generic by design

This template ingests **any** documentation type. The pipeline (normalize, tag, upsert) is fixed; the only content you customize is the **metadata tagging**. Three nodes carry the doc-specific fields, and they must stay in sync on the same keys:

- **Information Extractor** — the schema of *what* to pull from each document
- **Assemble Metadata** — maps the extracted fields plus the deterministic Drive fields into one object
- **Default Data Loader** — which fields ride onto every chunk

The template ships with a richer neutral default: `title`, `doc_type`, `summary`, `topics[]`, `keywords[]`, `entities[]`, `effective_date`, `audience`. The array fields break a document out into its component subjects, terms, and named things (products, models, versions, people), which land in Qdrant as array payloads you can filter with match-any. Legal contracts, API references, and support tickets each want different fields. Rather than edit three nodes by hand, point an LLM at [`AI-SETUP-PROMPT.md`](AI-SETUP-PROMPT.md): it interviews you about your documents and emits the matching, in-sync field definitions for all three.

For a small set of well-defined document types that each want *different* fields, see [Advanced: dynamic schema per document type](#advanced-dynamic-schema-per-document-type) below.

## Supported formats

Drop **anything** in the folder. The converter (MarkItDown) normalizes it all to Markdown:

- **Uploaded files** — PDF, Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`), CSV, HTML, plain text, and images — download as-is and convert directly.
- **Native Google files** (Docs, Sheets, Slides) aren't binary, so the Download File node is configured to **export** them first: Docs→Word, Sheets→CSV, Slides→PowerPoint. That export only fires for Google-native files; uploaded binaries pass through untouched.

**Prefer Word / Google Docs over PDF when you can.** Word and Google Docs carry real heading styles, which survive conversion as Markdown headings and give you true structure-aware chunking. PDFs usually convert to flat text with no headings (see the chunking note below). If you have a docx→PDF conversion step upstream, drop it: feed the Word file straight in.

## Why it's built this way

- **Markdown-first normalization.** Every source (PDF, Word, HTML, Google Doc) is converted to one clean structure before anything else. Headings become real section boundaries and tables survive, which is what makes structure-aware chunking possible instead of blind character splitting.
- **Structure-aware chunking, three tiers.** The **Chunk by Structure** Code node keeps each chunk to a coherent section instead of an arbitrary mid-section character cut, and adapts to how much structure the source actually has: **(1)** real Markdown headings (Word / Google Doc / HTML / Markdown) become the section boundaries — true hierarchical chunking; **(2)** for flat text with no headings (most PDFs), it *recovers* structure by treating short title-like lines as boundaries; **(3)** clean, line-aware windows as a last resort. It also strips converter noise (form feeds, page numbers, repeating page headers/footers). Each chunk carries its heading breadcrumb (`section_path`, e.g. `Guide > Setup > Credentials`) as metadata, prepended to the embedded text so the vector captures section context. This node is the single source of truth for chunking; the connected recursive splitter is sized large so it only ever passes these chunks through (the n8n vector-store node requires a splitter to be wired in).
- **Metadata tagged at the document level, before chunking.** Because it's tagged before the split, every chunk inherits it. That's what lets a retrieval layer filter to the right slice *before* running the semantic search. Design these fields around what you'll want to filter on.
- **Delete-then-insert upsert.** Existing chunks for a `file_id` are cleared before re-inserting, so a changed document never leaves stale vectors behind. A `content_hash` rides along in metadata for later dedup.

## What gets written to Qdrant

Every chunk is one Qdrant point: the chunk text (with its section breadcrumb prepended) as the embedded content, plus this metadata payload. The payload is exactly the field list on the **Default Data Loader** node, so that node is the source of truth for what is queryable. Add or remove rows there to change it.

| Field | Source | Filterable | Notes |
|---|---|---|---|
| `title` | LLM | yes | Document title |
| `doc_type` | LLM | yes | guide / policy / spec / FAQ / … |
| `summary` | LLM | no | One or two sentence summary |
| `topics` | LLM | yes (match-any) | Main subjects, array of strings |
| `keywords` | LLM | yes (match-any) | Search terms, array of strings |
| `entities` | LLM | yes (match-any) | Products / people / orgs / versions, array |
| `effective_date` | LLM | yes | ISO date if present, else empty |
| `audience` | LLM | yes | Who the doc is written for |
| `file_id` | Drive | yes | Source file; the upsert key |
| `source` | constant | yes | `google_drive` |
| `content_hash` | computed | yes | Change-detection / dedup fingerprint |
| `heading` | chunker | yes | The chunk's section heading |
| `section_path` | chunker | yes | Full heading breadcrumb, e.g. `Guide > Setup > Auth` |
| `chunk_index` | chunker | yes | Order of the chunk within the document |

The **Assemble Metadata** node also computes `file_name`, `mime_type`, `modified_time`, and `ingested_at` on the document object. They are not in the Data Loader list by default, so they do not reach Qdrant; add a row for any you want stored.

At retrieval time, filter on the payload first (e.g. `doc_type = "policy"` AND `topics` contains `"refunds"`), then run the semantic search over that slice. That pre-filter is the whole reason metadata is tagged before chunking.

## Requirements

- n8n (self-hosted or cloud)
- A Markdown converter service reachable over HTTP that returns `{ "markdown": "..." }`. MarkItDown is a CLI/library, not a server, so a thin wrapper is bundled in [`markitdown-service/`](markitdown-service/) — `docker compose up -d --build` and you have the `/convert` endpoint. [Docling](https://github.com/DS4SD/docling) or [Unstructured](https://unstructured.io) work too if you prefer.
- [Qdrant](https://qdrant.tech)
- OpenAI API key (embeddings + a cheap model for metadata extraction)
- Google Drive OAuth2 credential

## Setup

1. Import `workflow.json`.
2. **Metadata fields (the main customization):** decide what to tag per document. The fastest path is [`AI-SETUP-PROMPT.md`](AI-SETUP-PROMPT.md), which walks an LLM through your doc type and hands you the three synced edits. Or edit the Information Extractor schema, the Assemble Metadata `extracted` block, and the Default Data Loader metadata by hand, keeping the keys identical across all three.
3. **Credentials:** attach Google Drive OAuth2 (trigger + Download File), OpenAI (Chat Model + Embeddings OpenAI), and your Qdrant credential (Qdrant Insert). None are bundled.
4. **Folder:** set `YOUR_DRIVE_FOLDER_ID` on the Google Drive Trigger.
5. **Converter:** stand up the bundled MarkItDown service — `cd markitdown-service && docker compose up -d --build` (details in [`markitdown-service/README.md`](markitdown-service/README.md)) — then point the **MarkItDown Convert** node URL at it: `http://markitdown:8080/convert` if n8n shares the Docker network, otherwise `http://YOUR_CONVERTER_HOST:8080/convert`. It expects a JSON response shaped `{ "markdown": "..." }`. If yours returns raw text or a different field, adjust the Information Extractor's `text` expression and the Assemble Metadata `.json.markdown` reference.
6. **Collection:** set the collection name once in the **Config** node (default `document_knowledge`); the Delete and Qdrant Insert nodes read it from there. Set `YOUR_QDRANT_HOST` in the Delete node URL and a `QDRANT_API_KEY` env var. Create the collection at **3072 dimensions** (matches `text-embedding-3-large`) before the first run.
7. Activate the workflow.

## Notes & extensions

- **Native Google files are handled by export.** The Download File node's Google File Conversion is preset (Docs→Word, Sheets→CSV, Slides→PowerPoint), so native Google Docs/Sheets/Slides no longer error. Change those targets in the node's options if you prefer different formats.
- **PDFs lose their headings.** A PDF carries no heading markup, so MarkItDown extracts flat text and the chunker falls back to heuristic heading recovery (tier 2). It works, but Word/Google-Doc input gives cleaner sectioning. For PDF-heavy or scanned corpora, lean on metadata filters, and consider a layout-aware converter (Docling, Unstructured) if you need better PDF structure.
- **Tabular data (CSV/Excel)** converts to Markdown tables. Large tables get window-chunked, which can separate rows from their header. For heavy spreadsheet ingestion, consider a per-sheet or header-aware chunking step.
- **Chunk size lives in the Code node, not the splitter.** Tune `MAX_CHARS` (section-size ceiling before a section is sub-split) and `OVERLAP_LINES` at the top of the **Chunk by Structure** node. Leave the Recursive Character Text Splitter sized large (it's a required-by-the-node pass-through); shrinking it would re-split your sections and defeat the structural chunking.
- **Skip-if-unchanged gate:** the `content_hash` is already computed and stored. To avoid re-embedding unchanged docs, add an IF before the delete that compares the hash against a log store (Postgres or an n8n Data Table). Left out here so the template runs without extra infrastructure.
- **Deletions:** this workflow doesn't see file deletes. Add a small companion workflow on the Drive `fileDeleted` event that deletes Qdrant points by `file_id`.
- **Retrieval side:** keep retrieval in a separate, low-latency workflow. This template is ingestion only.

## Advanced: dynamic schema per document type

The default richer schema (`topics[]`, `entities[]`, `keywords`, `summary`, ...) is generic on purpose: stable keys, one extractor, works across mixed documents. That is the right choice for most corpora, and the array fields already adapt their *values* to any document.

If instead you ingest a few **well-defined** document types that each deserve *different* fields (contracts want `parties` / `jurisdiction` / `term`; API docs want `endpoint` / `version` / `auth`; tickets want `product` / `severity` / `status`), classify first and branch:

```
MarkItDown Convert
  → Classify (Information Extractor: just doc_type from your taxonomy)
  → Switch (on doc_type)
      → Extract: Contract   (schema: parties, jurisdiction, term, ...)
      → Extract: API doc     (schema: endpoint, version, auth, ...)
      → Extract: Ticket      (schema: product, severity, status, ...)
  → Assemble Metadata (merge; keep the shared provenance fields)
  → (rest of the pipeline unchanged)
```

Trade-offs: more nodes to maintain, and metadata keys vary by type, so your retrieval layer must handle a per-type key set (keep a few shared keys like `doc_type`, `title`, `summary` on every branch so cross-type queries still work). Keep the deterministic provenance fields (`file_id`, `source`, `content_hash`, plus the structural `heading` / `section_path` / `chunk_index`) identical on every branch so upsert, dedup, and section filtering keep working. [`AI-SETUP-PROMPT.md`](AI-SETUP-PROMPT.md) can scaffold the per-type schemas for you.

## What's in this folder

| File | Purpose |
|---|---|
| [`workflow.json`](workflow.json) | The n8n workflow. Import this. |
| [`AI-SETUP-PROMPT.md`](AI-SETUP-PROMPT.md) | Paste into an LLM to tailor the metadata fields to your documents and walk through deployment. |
| [`markitdown-service/`](markitdown-service/) | Dockerized MarkItDown HTTP converter the workflow calls. `docker compose up -d --build`. |
| [`CHANGELOG.md`](CHANGELOG.md) | Notable changes to this template. |
| `assets/` | Canvas screenshot used in this README. |

## License

MIT
