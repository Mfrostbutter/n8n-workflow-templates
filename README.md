# n8n Workflow Templates

[![Validate workflows](https://github.com/Mfrostbutter/n8n-workflow-templates/actions/workflows/validate-workflows.yml/badge.svg)](https://github.com/Mfrostbutter/n8n-workflow-templates/actions/workflows/validate-workflows.yml)

Production-ready [n8n](https://n8n.io) workflows I've built and open-sourced. Import the JSON, wire up your own credentials, run.

Each workflow lives in its own folder under [`workflows/`](workflows/) with a dedicated README covering setup, required credentials, and the gotchas that aren't obvious from the canvas.

## Workflows

| Workflow | What it does |
|---|---|
| [Document Fabric: Drive to Qdrant](workflows/document-fabric-drive-to-qdrant/) | Watches a Google Drive folder, converts each new document to Markdown, tags metadata at the document level, chunks on structure, and upserts into a Qdrant vector store. The ingestion half of a high-accuracy RAG pipeline. |
| [AI Product Photo Studio](workflows/ai-product-photo-studio/) | Turn a plain product photo into a styled studio shot from a single n8n form. Upload a photo, pick a look, describe the scene, and an image-to-image model re-renders it into a professional product or lifestyle shot. ~$0.11 per image. |
| [Wazuh AI Security Analyzer](workflows/wazuh-ai-security-analyzer/) | Turns every high-severity Wazuh alert into an AI-triaged Slack message with risk assessment, likely cause, and the exact shell commands to investigate. Infrastructure-context aware. ~$0.001 per alert with Claude Haiku. |
| [Autonomous Social Media Pipeline](workflows/autonomous-social-media-pipeline/) | Fully automated social content engine for any vertical: on a schedule, writes a caption + image prompt with Claude Haiku, generates an original image via KIE.ai, publishes to Facebook + Instagram, logs to Airtable, and notifies you on the messaging platform of your choice (Telegram out of the box). Grid-aware 12-post cycle with topic dedup. |
| [YouTube → Knowledge](workflows/youtube-to-knowledge/) | Paste a YouTube link in a form; it pulls the captions (via a small bundled yt-dlp service), runs the transcript through an AI Agent that writes a deep-dive structured markdown research document, and saves it to Google Drive. Swap between Claude, GPT, or a local Ollama model to compare outputs. |
| [Apollo Lead Enrichment (credit-aware)](workflows/apollo-lead-enrichment/) | Turns a Google Maps business scrape into a scored, deduplicated cold-lead table. Enriches every business through Apollo's free endpoints, scores each against your ICP for free, and spends a paid email-reveal credit only on the highest-conviction contacts under a hard monthly cap. Output is a cold-lead staging table, not your CRM. |
| [Cold Email Outbound (AI-written drip)](workflows/cold-email-outbound/) | The outbound half of the cold-lead system. Emails your best scored leads on a sequenced follow-up drip, has an LLM write each message so it reads human instead of templated, throttles under a daily cap in a business-hours window, stops the instant someone replies, bounces, or unsubscribes, and promotes replies into your CRM. ListMonk + Mailgun for compliant delivery. |

## How to import

1. Open the workflow folder and grab its `workflow.json`.
2. In n8n: **top-right menu → Import from File**, or copy the JSON and paste it straight onto the canvas.
3. Open each node with a credential dropdown and attach your own credentials (none are bundled).
4. Follow that workflow's README for any external setup: vector-store collections, env vars, converter services, etc.

## License

[MIT](LICENSE). Use them, fork them, ship them.
