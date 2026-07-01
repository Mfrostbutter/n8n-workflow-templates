# n8n Workflow Templates

[![Validate workflows](https://github.com/Mfrostbutter/n8n-workflow-templates/actions/workflows/validate-workflows.yml/badge.svg)](https://github.com/Mfrostbutter/n8n-workflow-templates/actions/workflows/validate-workflows.yml)

Production-ready [n8n](https://n8n.io) workflows I've built and open-sourced. Import the JSON, wire up your own credentials, run.

Each workflow lives in its own folder under [`workflows/`](workflows/) with a dedicated README covering setup, required credentials, and the gotchas that aren't obvious from the canvas.

## Workflows

| Workflow | What it does |
|---|---|
| [Document Fabric — Drive to Qdrant](workflows/document-fabric-drive-to-qdrant/) | Watches a Google Drive folder, converts each new document to Markdown, tags metadata at the document level, chunks on structure, and upserts into a Qdrant vector store. The ingestion half of a high-accuracy RAG pipeline. |

## How to import

1. Open the workflow folder and grab its `workflow.json`.
2. In n8n: **top-right menu → Import from File**, or copy the JSON and paste it straight onto the canvas.
3. Open each node with a credential dropdown and attach your own credentials (none are bundled).
4. Follow that workflow's README for any external setup: vector-store collections, env vars, converter services, etc.

## License

[MIT](LICENSE). Use them, fork them, ship them.
