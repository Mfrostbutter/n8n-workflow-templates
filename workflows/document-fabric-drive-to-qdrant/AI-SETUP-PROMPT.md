# AI Setup Prompt

> Paste the block below into Claude, ChatGPT, Gemini, or any reasoning-capable LLM. It walks you through deploying this workflow against YOUR documents. The centerpiece is the **metadata tagging**: the three nodes that decide what gets pulled out of each document and filed alongside every chunk. The prompt interviews you about the kind of documentation you are ingesting, then hands you ready-to-paste field definitions for all three nodes so retrieval can filter to the right slice before it searches.

**Why use it:** the workflow imports and runs, but the tagging fields ship as a generic example (`title`, `doc_type`, `topic`, `effective_date`, `audience`). Legal contracts, API references, support tickets, and product manuals each want different fields. Getting those wrong is the difference between "filter to the 2024 refund policy for customers" and "semantic search across everything and hope." This prompt turns your doc type into the right fields and keeps the three nodes in sync.

**Recommended models:** Claude Sonnet 4.5 / Opus 4.8, GPT-5, or Gemini 2.5 Pro. Smaller models work too, with less nuance in the field design.

---

## Copy everything below this line and paste it into your AI

```
You are helping me deploy the "Document Fabric: Drive to Qdrant Ingest" n8n
workflow from
https://github.com/Mfrostbutter/n8n-workflow-templates/tree/main/workflows/document-fabric-drive-to-qdrant
into my own environment. The workflow watches a Google Drive folder, converts
each new document to Markdown, uses an LLM to tag it with metadata, deletes any
old vectors for that file, chunks the Markdown, embeds it, and upserts it into a
Qdrant collection. It is the ingestion half of a RAG pipeline. It ingests any
kind of documentation; the one thing I customize is the metadata tagging.

## Your job

Walk me through deployment in order. Ask me one focused question at a time (or one
tight cluster). Wait for my answer before moving on. Do not dump the whole plan up
front. Do not pad with reassurance. The main event is designing my metadata fields
and emitting the matching code for three nodes, so spend the most effort there.

## Order of operations

1. Environment audit. Confirm I have:
   - n8n (self-hosted or Cloud)
   - A Google Drive folder to watch, plus a Google Drive OAuth2 credential
   - A Markdown converter reachable over HTTP that returns { "markdown": "..." }.
     MarkItDown, Docling, and Unstructured all work. Ask which I am using and,
     if none, point me at MarkItDown as the shortest path.
   - An OpenAI API key (embeddings, plus a cheap model for the metadata
     extraction; the workflow ships with gpt-4o-mini)
   - A Qdrant instance (Cloud or self-hosted) and its API key
   If anything is missing, give me the shortest viable path and pause.

2. Understand my documents. THIS DRIVES EVERYTHING ELSE. Ask me:
   - What kind of documents am I ingesting? (e.g. legal contracts, API docs,
     support tickets, product manuals, research papers, SOPs, meeting notes)
   - How will I query them later? What would I want to FILTER on before the
     semantic search runs? (e.g. "only active contracts", "only the v3 API",
     "only tickets tagged billing") Filters are the whole reason we tag metadata,
     so mine my answer here for the fields that matter.
   - Roughly how consistent is the structure? Do the docs reliably contain the
     things I want to extract, or is it best-effort?

3. Design the metadata fields. The template already ships a solid richer default:
   title, doc_type, summary, topics[], keywords[], entities[], effective_date,
   audience. Start from that and tune it to my doc type and my filters from step
   2 — add, remove, or rename fields. For each field give: a snake_case key, a
   one-line description written AS AN INSTRUCTION TO THE EXTRACTING LLM (it goes
   in the schema and steers extraction), the type (string or array of strings),
   and whether it is a good filter field. Guidance:
   - Prefer low-cardinality, filterable fields (doc_type, status, product,
     jurisdiction, version, department) over free prose. Those are what make
     pre-filtered retrieval work.
   - Use ARRAY-of-string fields to break a document out into its parts: topics,
     keywords, entities (products, people, orgs, versions), tags. These land in
     Qdrant as array payloads you filter with match-any, and they are the main
     way to enrich retrieval beyond a single topic string.
   - Keep at most one or two long free-text fields (like summary); they are
     nice-to-have, not filters.
   - Dates should be one string field; tell the LLM to return ISO YYYY-MM-DD or
     empty if absent.
   - If a value should come from a fixed set, say so in the description (e.g.
     "one of: draft, active, expired") so the LLM stays consistent.
   Let me edit your proposal until the field list is right. Do not proceed until
   I approve the final list.

   Advanced (only if I ask): if I have a few well-defined doc types that each want
   DIFFERENT fields, offer the classify-then-branch pattern instead — a first
   Information Extractor that only assigns doc_type, a Switch on doc_type, and a
   per-type extractor with its own schema. Keep a few shared keys (doc_type,
   title, summary) and all provenance/structural keys identical on every branch.
   Default to the single richer schema unless I say my types are truly distinct.

4. Emit the three edits, in sync. Once I approve the fields, produce all three of
   the following so they line up on the same keys. Show them as copy-paste blocks
   and tell me exactly where each goes.

   (a) Information Extractor node -> "Input Schema" field. A JSON Schema object:
       {
         "type": "object",
         "properties": {
           "<key>": { "type": "string", "description": "<instruction>" },
           ...
         }
       }
       One property per field I approved. Use "string" for scalars; for the
       break-out fields use an array of strings:
         "topics": { "type": "array", "items": { "type": "string" },
                     "description": "<instruction>" }
       Put the extraction instruction in each "description".

   (b) Assemble Metadata node (Code) -> the `extracted` object near the top. One
       line per field, reading from the LLM output with a null fallback:
         const extracted = {
           <key>: ex.<key> ?? null,                              // scalar
           <arrayKey>: Array.isArray(ex.<arrayKey>) ? ex.<arrayKey> : [],  // array
           ...
         };
       (arrays default to [] so a missing extraction never breaks a filter)
       Do not touch the `provenance` block below it (file_id, file_name, source,
       mime_type, modified_time, content_hash, ingested_at) unless I ask; those
       are the deterministic Drive fields and should stay.

   (c) Default Data Loader node -> Options -> Metadata. One metadataValue row per
       field I want queryable on each chunk. Chunking happens in the "Chunk by
       Structure" node just upstream, which flattens each chunk's fields to the
       top level, so these read from the current item:
         name:  <key>
         value: ={{ $json.<key> }}
       Include my approved fields PLUS keep file_id, source, and content_hash so
       upsert-by-file and dedup keep working. Also LEAVE the three structural
       fields the chunker adds automatically -- heading, section_path,
       chunk_index -- they let retrieval show and filter by document section. I
       do not have to expose every field here, only what I will filter or display.

   Remind me: the keys must match across all three. If the Extractor calls it
   `jurisdiction` but Assemble Metadata reads `ex.region`, the field silently
   comes back null.

5. Set the collection name. In the Config node, set `collection` to my Qdrant
   collection name (default document_knowledge). The Delete and Qdrant Insert
   nodes read it from Config, so this is the only place I set it.

6. Create the Qdrant collection BEFORE the first run. It must match the embedding
   model's dimensions: text-embedding-3-large = 3072. If I switch the Embeddings
   node to text-embedding-3-small, that is 1536. Give me the create-collection
   call for my Qdrant (REST or dashboard) with Cosine distance.

7. Import the workflow and fill placeholders. Give me the n8n import path, then
   have me set:
   - YOUR_DRIVE_FOLDER_ID on the Google Drive Trigger
   - the MarkItDown Convert URL to my converter (it must return { "markdown": ".." };
     if mine returns a different shape, tell me which expression to adjust)
   - YOUR_QDRANT_HOST in the Delete Existing Vectors URL
   - a QDRANT_API_KEY environment variable for n8n

8. Attach credentials (none are bundled): Google Drive OAuth2 (trigger + Download),
   OpenAI (Chat Model + Embeddings), and my Qdrant credential (Qdrant Insert).
   Never ask me to paste any key into this chat; they live in n8n's Credentials
   and Variables panels only.

9. End-to-end test. Have me drop one representative document into the Drive folder
   (or run the trigger manually) and confirm: it converts to Markdown, the metadata
   comes back with my fields populated, old vectors for that file are cleared, and
   chunks land in Qdrant carrying my metadata. Have me spot-check one point in the
   Qdrant dashboard to verify the payload has my fields. Then re-drop the SAME file
   and confirm the count does not double (upsert works).

10. Go live. Activate the workflow. Note two things: native Google Docs need an
    export format set on the Download File node (uploaded PDFs/Word work as-is),
    and this workflow does not see file deletions, so if I need those I should add a
    small companion workflow on the Drive fileDeleted event that deletes Qdrant
    points by file_id.

## Constraints
- The metadata fields are the thing I customize. Keep the three nodes in step 4
  in sync on the same keys; that is the most common way this breaks.
- Never ask me to paste API keys or tokens into this chat. Credentials live in
  n8n only.
- Keep it practical. Assume I can click around n8n and edit a JSON object and a
  small JavaScript block.
```
