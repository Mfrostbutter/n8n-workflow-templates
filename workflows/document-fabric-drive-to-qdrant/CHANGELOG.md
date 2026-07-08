# Changelog

All notable changes to the **Document fabric (Drive to Qdrant)** workflow template.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Dates are `YYYY-MM-DD`.

## [Unreleased]

### Changed
- **Richer default metadata schema.** The example fields moved from a single `topic` string to a structured set: `title`, `doc_type`, `summary`, `topics[]`, `keywords[]`, `entities[]`, `effective_date`, `audience`. The array fields break a document out into its subjects, terms, and named things and land in Qdrant as array payloads (filter with match-any). All three meta-tagging nodes stay in sync on the new keys. The README documents a classify-then-branch pattern for users whose doc types each want different fields.
- **Genericized off product docs.** The example metadata schema moved from product-specific fields (`product_line`, `sku`) to a neutral documentation set (`title`, `doc_type`, `topic`, `effective_date`, `audience`), and the default collection is now `document_knowledge`. The template now reads as ingesting any documentation type, not just a product catalog.
- **Added a `Config` node.** The Qdrant `collection` name lives in one Set node and is read by the Delete and Qdrant Insert nodes via expression, so there is a single place to set it.
- **Refactored `Assemble Metadata`** into an `extracted` (LLM fields, edit these) block and a `provenance` (deterministic Drive fields, leave as-is) block, with inline guidance for retargeting.

### Added
- **True structure-aware chunking, three tiers.** New **Chunk by Structure** Code node keeps each chunk to a coherent section: (1) real Markdown headings when present, (2) heuristic heading *recovery* for flat text like PDFs (short title-like lines become boundaries), (3) clean line-aware windows as a last resort. It strips converter noise (form feeds, page numbers, repeating page headers/footers), attaches the heading breadcrumb as `section_path` (plus `heading`, `chunk_index`) and prepends it to the embedded text. The recursive splitter is a large pass-through backstop, so the Code node is the single source of truth for chunking. Chunk size (`MAX_CHARS` / `OVERLAP_LINES`) is tuned in the Code node.
- **Multi-format ingest out of the box.** The Download File node now exports native Google files (Docs→Word, Sheets→CSV, Slides→PowerPoint) so they no longer error; uploaded PDF/Word/PowerPoint/Excel/CSV/HTML/text/images pass through to the converter as-is. A docx→PDF pre-conversion is no longer needed (and is discouraged — it strips the headings that make structure-aware chunking work).
- **Bundled converter service.** `markitdown-service/` ships a Dockerized MarkItDown HTTP wrapper (`POST /convert`), so users can stand up the converter the workflow needs with `docker compose up -d --build`.
- **Runner-safe hashing.** `Assemble Metadata` uses a dependency-free content fingerprint instead of `crypto.createHash`, so it runs on n8n's external task runner (where `crypto` is not a global) without extra env flags.
- **Sticky notes on the canvas** per the template directive: an overview, three stage panels (Ingest & Normalize, Tag Metadata, Chunk & Store), and a "What This Achieves" summary. The Tag Metadata zone is flagged as the one part you customize.
- **`AI-SETUP-PROMPT.md`** that interviews an LLM about your documentation type and emits the matching, in-sync field definitions for the three meta-tagging nodes (Information Extractor schema, Assemble Metadata mapping, Default Data Loader metadata).

## [2026-07-01]

### Added
- Initial published release of the workflow template.
