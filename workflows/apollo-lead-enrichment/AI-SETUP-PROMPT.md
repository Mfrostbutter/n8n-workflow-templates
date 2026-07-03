# AI Setup Prompt

> Paste the block below into Claude, ChatGPT, Gemini, or any reasoning-capable LLM. It walks you through deploying this workflow against YOUR business: the Postgres schema, the Apify and Apollo credentials, the trigger, and the one thing that decides everything, your ICP (which businesses are worth an enrichment credit). It asks the questions it needs; you answer with what you actually sell and to whom.

**Why use it:** the workflow imports and runs, but the `Score ICP` node ships with placeholder target states and categories. Your regions, your customer type, and your score threshold all live there. The prompt pulls those out of you and hands you a finished ICP block to paste in, instead of leaving you guessing.

**Recommended models:** Claude Sonnet 4.5 / Opus 4.8, GPT-5, or Gemini 2.5 Pro. Smaller models work too, with less nuance in the ICP tuning.

---

## Copy everything below this line and paste it into your AI

```
You are helping me deploy the "Lead Enrichment - Apollo (credit-aware)" n8n
workflow from
https://github.com/Mfrostbutter/n8n-workflow-templates/tree/main/workflows/apollo-lead-enrichment
into my own environment. The workflow takes a Google Maps business scrape,
dedups it, enriches each business through Apollo's FREE endpoints, scores each
against my ideal customer profile, and spends a paid Apollo email-reveal credit
ONLY on the highest-conviction contacts, under a monthly cap. The output is a
cold-lead table in Postgres, NOT a CRM.

## Your job

Walk me through deployment in order. Ask me one focused question at a time (or one
tight cluster). Wait for my answer before moving on. Do not dump the whole plan up
front. Do not lecture. The centerpiece of this session is helping me write my ICP
in the Score ICP node, so spend the most effort there.

## Order of operations

1. Environment audit. Confirm I have:
   - n8n (self-hosted or Cloud)
   - A Postgres database I can run a schema file against
   - An Apify account and API token, running (or willing to run) a Google Maps
     Scraper actor
   - An Apollo account and API key. Ask which plan / how many reveal credits per
     month I get, because that number becomes my monthly cap.
   If anything is missing, give me the shortest viable path and pause.

2. Create the database schema. Tell me to run sql/schema.sql against my Postgres.
   Explain that it creates a cold_outreach schema with four tables: gms_runs,
   seen_leads, gms_leads_raw, and gms_leads_enriched (the cold-lead table).

3. Write my ICP with me. THIS IS THE MAIN EVENT. Open the Score ICP node; the top
   is a marked block with four constants. Interview me, then produce a ready-to-paste
   block. Ask, roughly in order:
   - What do I sell, and who is the ideal customer business? (a category, e.g.
     "independent HVAC contractors", "boutique law firms", "med spas")
   - What regions do I sell into? Map these to two-letter state codes for
     TARGET_STATES, or tell me to set it to [] if geography does not matter.
   - What words show up in those businesses' Google Maps category that signal a
     good fit? Help me turn those into the TARGET_CATEGORY regex.
   - Any quality floor? Default MIN_RATING 4.0 and MIN_REVIEWS 50 (a proxy for a
     real, established business). Adjust with me if my market skews small.
   Explain the scoring: five signals, 20 points each, 100 max (rating, reviews,
   has-website, region match, category match). A lead needs three of five to reach
   60. Output the finished block and tell me to paste it over the marked section at
   the top of Score ICP, leaving the code below it untouched.

4. Set the decision-maker titles. In the Apollo: people search node and the Reveal
   gate node there are title lists (owner, founder, principal, partner, director,
   etc.). Ask who actually signs off on buying what I sell, and help me align both
   lists to that title.

5. Set my budget. In the Config node:
   - MONTHLY_REVEAL_CAP = my Apollo monthly credit allowance (from step 1)
   - REVEAL_MIN_SCORE = the ICP score a lead must hit before I spend a credit
     (default 60; raise it to be stingier, lower it to reveal more)

6. Import the workflow. Give me the exact n8n menu path to import
   apollo-lead-enrichment.json.

7. Attach credentials (none are bundled). Walk me through:
   - A Postgres credential on every database node (they share one connection)
   - HTTP Query Auth on "Get dataset items": my Apify API token sent as the
     `token` query parameter
   - HTTP Header Auth on the three Apollo nodes: header name X-Api-Key, value my
     Apollo API key
   Never ask me to paste any of these keys into this chat; they live in n8n's
   Credentials panel only.

8. Wire the trigger. The workflow starts from a POST to the webhook path
   maps-lead-enrich-inbound. Explain the contract and help me set up the minimal
   starter:
   - Before a scrape, INSERT a row into cold_outreach.gms_runs and keep its id.
   - Start the Apify Google Maps Scraper with that id in the payload.
   - When the run finishes, POST this to the webhook:
     { "run_pk": <that id>, "vertical": "<label>", "apify_run_id": "...",
       "dataset_id": "...", "status": "SUCCEEDED" }
   - The easiest wiring is Apify's own run-finished webhook, which carries the
     dataset id (resource.defaultDatasetId). Help me set whichever path fits.

9. Test end to end. Have me run a small scrape (a handful of places), fire the
   trigger, and confirm: raw rows land in gms_leads_raw, enriched contacts land in
   gms_leads_enriched with an icp_score, most are email_status='unrevealed', and a
   couple of high scorers got a real email without blowing the cap. Check the
   reveals_used count against my cap.

10. Reinforce the CRM boundary before I go live. Remind me: this table is cold,
    unqualified leads. Do NOT sync it into my CRM. My outbound sequence reads from
    gms_leads_enriched and logs sends; a lead only becomes a CRM contact when they
    REPLY. Ask how my stack does outbound and help me wire the reply-to-CRM step.

## Constraints
- The Score ICP node is the only place with my business logic. Guide me to edit it,
  the two title lists, and the Config knobs, and nothing else unless a step says so.
- Never ask me to paste API keys or tokens into this chat. Credentials live in n8n.
- Respect the cap. The whole point is spending reveal credits sparingly; do not
  suggest changes that reveal everything.
- Keep it practical. Assume I can click around n8n, run a SQL file, and edit a
  JavaScript object.
```
