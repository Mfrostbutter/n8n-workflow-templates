# AI Setup Prompt

> Paste the block below into Claude, ChatGPT, Gemini, or any reasoning-capable LLM. It walks you through deploying this workflow against YOUR channel: the Config node (your vertical, your 5 topics, your posting cycle), the Airtable table, the Meta and image credentials, your notification platform, and an end-to-end test post. It asks the questions it needs; you answer with what your brand and stack actually look like.

**Why use it:** the workflow imports and runs, but the one node that decides everything, `Config`, is a blank template. Your industry, your five topics, your brand voice, and your grid cycle all live there. The prompt pulls those out of you with targeted questions and hands you a finished config block to paste in, instead of leaving you staring at placeholders.

**Recommended models:** Claude Sonnet 4.5 / Opus 4.8, GPT-5, or Gemini 2.5 Pro. Smaller models work too, with less nuance in the topic writing.

---

## Copy everything below this line and paste it into your AI

```
You are helping me deploy the "Autonomous Social Media Pipeline" n8n workflow from
https://github.com/Mfrostbutter/n8n-workflow-templates/tree/main/workflows/autonomous-social-media-pipeline
into my own environment. On a schedule the workflow picks the next slot in a
grid cycle, writes a caption and an image prompt with an LLM, generates an
original image via KIE.ai, publishes to Facebook and Instagram, logs the post to
Airtable, and pings me on a messaging platform. It adapts to any industry by
editing ONE node called Config.

## Your job

Walk me through deployment in order. Ask me one focused question at a time (or one
tight cluster). Wait for my answer before moving on. Do not dump the whole plan up
front. Do not lecture or pad with reassurance. The centerpiece of this session is
helping me fill in the Config node, so spend the most effort there.

## Order of operations

1. Environment audit. Confirm I have:
   - n8n (self-hosted or Cloud)
   - An LLM provider for the captions/prompt writing (Anthropic Claude by default;
     the model id lives in Config.llmModel)
   - A KIE.ai account and API key (image generation; this is where almost all the
     per-post cost lands, a few cents each)
   - A Meta (Facebook) Page linked to an Instagram Business/Creator account, and a
     long-lived Page access token with content-publishing scopes
   - An Airtable account
   - A notification channel: Telegram out of the box, or Slack / Discord / any
     incoming webhook
   If anything is missing, give me the shortest viable path and pause.

2. Build the Config node with me. This is the main event. Config is the only node
   with my content in it. Interview me and then produce a complete, ready-to-paste
   config object. Ask me, roughly in this order:
   - My brand name (Config.brand) and my niche/industry (Config.vertical).
   - My brand voice in a few words (Config.brandVoice), e.g. "technical but
     accessible, community-driven".
   - My FIVE content topics. For EACH topic help me define:
       label     - a short name; this also becomes an option in Airtable's "Type"
                   field, so keep it consistent (e.g. "Tips", "Deep Dive")
       angle     - the editorial instruction for that topic, one sentence
       subtopics - 3 to 5 variations the model rotates through for variety
       hashtags  - a couple of topic-specific hashtags
     If I am stuck, propose five topics that fit my vertical and let me edit them.
   - My base hashtags added to every post (Config.baseHashtags).
   - The posting cycle (Config.cycle): a 12-slot array of my topic keys t1..t5,
     laid out as a 4-row x 3-column Instagram grid. Explain that the order IS the
     grid: slots fill left-to-right, top-to-bottom, so grouping the same topic
     three-in-a-row makes a clean horizontal band on the mobile grid. Offer a
     sensible default like ['t1','t1','t1','t2','t3','t2','t5','t5','t5','t4','t4','t4']
     and let me reshape it. It does not have to be 12 slots.
   Leave the image settings (kieModel, kieAspectRatio, kieResolution) at their
   defaults unless I ask. Output the finished Config object and tell me to paste it
   over the config = { ... } block in the Config node, keeping the code BELOW it
   (the cycle-advance logic) untouched.

3. Stand up the Airtable table. Tell me to import airtable/content-table.csv into
   my base to create the table in one click, then set the field types per
   airtable/SCHEMA.md. Confirm the "Type" single-select options match my five
   topic labels from step 2. Have me grab my Base ID and Table ID.

4. Import the workflow. Give me the exact n8n menu path to import
   autonomous-social-media-pipeline.json.

5. Fill the destination placeholders. Back in Config, replace:
   - airtableBaseId / airtableTableId with the ids from step 3
   - metaPageId (YOUR_META_PAGE_ID) and metaIgUserId (YOUR_META_IG_USER_ID)
   - telegramChatId if I am using Telegram (otherwise see step 7)
   Also remind me the three Airtable HTTP nodes (Fetch Last Record, Fetch Past
   Topics, Log to Airtable) have the base/table ids in their URLs, so those need
   the same values.

6. Attach credentials (none are bundled). Walk me through creating and attaching:
   - Anthropic on the Generate Content node
   - HTTP Bearer Auth (my KIE.ai key) on KIE Create and KIE Poll
   - n8n Variables AIRTABLE_PAT (Airtable token) and META_PAGE_ACCESS_TOKEN
     (long-lived Meta Page token), under Settings -> Variables
   Never ask me to paste any of these keys or tokens into this chat; they live in
   n8n's Credentials/Variables panels only.

7. Wire my notification platform. The workflow ships wired for Telegram on two
   nodes: KIE Error and Success Notification. Ask what I actually use:
   - Telegram: attach a Telegram credential and set telegramChatId in Config.
   - Slack / Discord / other: replace those two nodes with the matching send node,
     or an HTTP POST to an incoming webhook. Everything upstream is unchanged.
   Help me do whichever one I pick.

8. End-to-end test. Have me run the Manual Trigger once (not the schedule) and
   confirm: an image generates, a post appears on the Facebook Page and the linked
   Instagram account, a row is written to Airtable with the right Cycle Position,
   and my notification fires. If the KIE poll times out (30 attempts, ~2.5 min) it
   routes to the error notification instead of hanging, so tell me to check the
   KIE key and model if that happens.

9. Go live. Once the manual run is clean, activate the workflow. The schedule fires
   at 10am and 3pm server time by default (cron 0 0 10,15 * * *); tell me how to
   change it if I want a different cadence.

## Constraints
- Config is the only node with my content. Guide me to edit it and nothing else
  unless a step above says otherwise.
- Never ask me to paste API keys, tokens, or the Meta access token into this chat.
  Credentials live in n8n only.
- Keep it practical. Assume I can click around n8n and edit a JavaScript object.
```
