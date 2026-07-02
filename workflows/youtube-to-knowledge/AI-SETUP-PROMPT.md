# AI Setup Prompt

> Paste the block below into Claude, ChatGPT, Gemini, or any reasoning-capable LLM. It walks you through deploying this workflow against YOUR stack: the captions service, n8n import, the AI Agent model choice, Google Drive, and an end-to-end test. It asks the questions it needs; you answer with what your environment actually looks like.

**Why use it:** the workflow imports and runs, but the two decisions that matter — where the captions service lives on your network, and which model you point the agent at — depend on your setup. The prompt pulls those out of you with targeted questions instead of leaving you staring at a template.

**Recommended models:** Claude Sonnet 4.5 / Opus 4.8, GPT-5, or Gemini 2.5 Pro. Smaller models work too, with less detail.

---

## Copy everything below this line and paste it into your AI

```
You are helping me deploy the "YouTube to Knowledge" n8n workflow from
https://github.com/Mfrostbutter/n8n-workflow-templates/tree/main/workflows/youtube-to-knowledge
into my own environment. The workflow takes a YouTube link from a form,
pulls the video's captions via a small yt-dlp HTTP service, runs the
transcript through an AI Agent to produce a deep-dive structured markdown
research document, and saves it to Google Drive.

## Your job

Walk me through deployment in order. Ask me one focused question at a time
(or one tight cluster). Wait for my answer before moving on. Do not dump the
whole plan up front. Do not lecture or pad with reassurance.

## Order of operations

1. Environment audit. Confirm I have:
   - n8n (self-hosted or Cloud) and its public hostname
   - Docker available to run the captions service (self-hosted), OR a plan to
     host it somewhere n8n can reach over HTTP. n8n Cloud users cannot run it
     inside n8n.
   - At least one chat-model provider: Anthropic, OpenAI, or a local Ollama
     endpoint
   - A Google account with Drive, for the Drive OAuth2 credential
   If anything is missing, give me the shortest viable path and pause.

2. Deploy the captions service. It lives in service/ (app.py, Dockerfile,
   requirements.txt). Give me the exact commands to build and run it, and
   stress that it must sit on the SAME Docker network as my n8n container so
   n8n can resolve it by container name. Ask what my n8n container and network
   are called so the run command is correct. Help me confirm it answers on
   GET /transcript?url=<a youtube link>.

3. Import the workflow. Tell me the exact n8n menu path to import
   youtube-to-knowledge.json.

4. Wire the captions URL. In the Fetch Transcript node, set the URL to my
   service (e.g. http://ytdlp-captions:8080/transcript). Confirm the host and
   port match how I ran the container.

5. Pick and attach a model. Explain that the AI Agent uses one chat model at a
   time. Ask which provider I want to start with, walk me through creating that
   credential in n8n, attaching it to the matching model node, and making sure
   that node's connector runs to the agent's Chat Model input. Mention I can
   add the other model nodes later to compare outputs.

6. Google Drive. Walk me through creating a Google Drive OAuth2 credential in
   n8n, attaching it to the Save to Google Drive node, and setting the target
   folder id (replace YOUR_DRIVE_FOLDER_ID). Remind me that OAuth client
   secrets are secrets: never paste them in chat or commits.

7. End-to-end test. Have me open the form's Production URL, paste a YouTube
   link that has captions, submit, and confirm a .md file lands in the Drive
   folder. If a video has captions disabled the run fails cleanly with a 422,
   so tell me to try a different video.

## Constraints
- Captions-only by design: no Whisper, no GPU. Videos without captions 422.
- Never ask me to paste API keys or OAuth secrets into this chat. Credentials
  live in n8n's Credentials panel only.
- Keep it practical. Assume I can run shell commands and click around n8n.
```
