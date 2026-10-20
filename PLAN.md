# Daily AI Explainer → YouTube Automation (n8n + OpenRouter)

**Status:** Plan (hand-off for Claude Code). **Date:** 2026-10-20.
**Goal:** Every day, automatically pick a topic, generate a short explainer video from AI video clips via OpenRouter, and publish it to YouTube, with no manual steps after setup.

---

## 1. Decisions already made

| Area | Decision |
|---|---|
| Video style | True AI video clips (text-to-video, one clip per scene), stitched into one explainer |
| Orchestrator | n8n (self-hosted, so FFmpeg is available via Execute Command) |
| Model gateway | OpenRouter for the LLM (topic, script, scene prompts) and for video generation |
| Publisher | YouTube Data API v3 (`videos.insert`, resumable upload) |
| Niche | **OPEN. Not chosen yet.** Make it one config value (`CHANNEL_NICHE`) so nothing else changes when it is set. |

Open items the owner must decide before or during build are listed in section 11.

---

## 2. Verified facts that shape the design

- OpenRouter now has a **video generation API**. Flow: `POST /api/v1/videos` (returns 202 with a job id and `polling_url`), poll `GET /api/v1/videos/{id}` until `completed`, then download with `GET /api/v1/videos/{id}/content?index=0`. The download needs the `Authorization` header, because the "unsigned" URLs are not presigned.
- Job statuses: `pending`, `in_progress`, `completed`, and the terminal failures `failed`, `cancelled`, `expired`.
- Request fields: `model`, `prompt`, `duration`, `resolution`, `aspect_ratio`, `generate_audio`, optional `frame_images` (first/last frame), `seed`, and `callback_url` (webhook). Supported values **vary per model**.
- Models listed at time of writing include Veo 3.1 (fast/lite), Seedance 2.0 (and fast), Kling v3.0 (std/pro), Wan 2.6/2.7, Hailuo 2.3, Sora 2 Pro. Discover the live list and per-model limits at runtime with `GET /api/v1/videos/models`. Do not hard-code durations or resolutions.
- Clips are short (the docs' examples use about 4-5 seconds), so an explainer must be assembled from many clips.
- YouTube `videos.insert` costs 1 unit from a separate Video Uploads bucket with a 100 calls/day limit per the current docs, so one upload a day is far inside quota. The docs also state that uploads from unverified API projects are not forced private, but **test this on the owner's actual project with one private upload first**, because older guidance said the opposite.
- If `status.privacyStatus` is not set, the video can default to public. Always set it explicitly.

Sources:
- OpenRouter: [Video generation API guide](https://openrouter.ai/blog/tutorials/video-generation-api/), [Choose a video model](https://openrouter.ai/docs/cookbook/video-generation/choose-video-model), [Text-to-video cookbook](https://openrouter.ai/docs/cookbook/video-generation/text-to-video), [Video models collection](https://openrouter.ai/collections/video-models)
- YouTube: [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert)

---

## 3. Recommended video format

Default to **vertical 9:16 Shorts, 45-60 seconds, about 10-12 scenes of 4-6 s each**. Reasons: cheapest per video, fastest to render, and it fits the short clip lengths the models support. A long-form 16:9 mode should be a config switch (`FORMAT=short|long`), not a rewrite.

Because most video models produce clips with no reliable spoken narration, use a **separate voiceover track** (see section 5, step 6) and make the clips visual-only (`generate_audio: false`) unless testing shows a model's native audio is good enough.

---

## 4. Architecture

```
[Schedule Trigger 09:00 IST]
        │
        ▼
 1. Pick topic ──► LLM via OpenRouter, avoids repeats using history store
        │
        ▼
 2. Write script + storyboard ──► LLM returns strict JSON (scenes[], narration, visual prompt, title, description, tags)
        │
        ▼
 3. Validate JSON + safety/quality gate (schema check, length, banned-content check)
        │
        ▼
 4. Per scene (split in batches): submit video job ──► POST /videos
        │
        ▼
 5. Wait + poll until completed (or webhook) ──► retry failed scenes, then download MP4s
        │
        ▼
 6. Voiceover (TTS) + captions (SRT)
        │
        ▼
 7. FFmpeg: normalize clips → concat → mix voice + music → burn captions → final.mp4 + thumbnail
        │
        ▼
 8. Upload to YouTube (resumable) with title/desc/tags, AI-disclosure flag, scheduled or immediate
        │
        ▼
 9. Log to history store (topic, video id, cost, duration) ──► notify owner (success or failure)
```

A separate **Error Workflow** in n8n catches any failure, notifies the owner, and leaves the day's run marked `failed` so it can be re-run without duplicating a topic.

---

## 5. Workflow detail, step by step

### Step 1: Topic selection
- Store: n8n Data Table (or Google Sheet / Postgres) named `topics_history` with columns `date, topic, video_id, status, cost_usd`.
- Prompt the LLM with `CHANNEL_NICHE`, the last 60 topics, and ask for one new, specific, explainable topic plus a one-line angle. Reject near-duplicates with a simple similarity check (normalized title match plus embedding or LLM check).
- Optional later: a backlog queue the owner can add to; fall back to LLM generation when empty.

### Step 2: Script and storyboard (single LLM call, JSON mode)
Output schema:

```json
{
  "title": "<=70 chars, curiosity + clarity",
  "description": "2-3 sentences + hashtags",
  "tags": ["..."],
  "hook": "first-3-seconds line",
  "scenes": [
    {
      "n": 1,
      "narration": "one or two sentences",
      "visual_prompt": "self-contained cinematic prompt, subject, motion, camera, style",
      "duration_s": 5
    }
  ],
  "style_guide": "single consistent visual style string reused in every scene"
}
```

Consistency rules: prepend the same `style_guide` to every scene prompt; reuse a seed where the model supports it; optionally chain scenes with `frame_images` (last frame of scene N as first frame of scene N+1) for continuity, as an experiment in Milestone 4.

### Step 3: Gate
Schema validation (n8n Code node), total narration length matches the target runtime, no real people or trademarked characters in prompts, then continue or fail loudly.

### Step 4-5: Video generation
- Read `/videos/models` once at the start of the run and pick the configured model, falling back to a second model if the first rejects the request.
- Submit scenes in parallel with a small cap (start with 3 at a time) to stay polite on rate limits, which the docs do not state.
- Poll every 30 s with a 20-30 minute per-scene timeout. Prefer the **`callback_url` webhook** (n8n Webhook node) if the instance is publicly reachable; keep polling as the fallback. Store the idempotency key header to avoid double-processing.
- On `failed` / `expired`: retry that scene once, with a simplified prompt on the second attempt. If a scene still fails, either drop it (if the narration still makes sense) or fail the run.
- Download with the Authorization header, stream to disk at `/data/runs/{date}/scene_{n}.mp4`.

### Step 6: Voiceover and captions
OpenRouter's video API does not give a dependable narration track, so TTS is needed. Options, in order of preference for a first version:
1. An OpenRouter-hosted audio/TTS model if one is available at build time (check `/api/v1/models` for audio-output models).
2. A dedicated TTS API (ElevenLabs, OpenAI TTS, or Google TTS) called from n8n.
3. A local open-source TTS (Piper or Kokoro) in the n8n container, which is free and good enough for a first version.

Generate one audio file per scene, measure its duration, and use it to set each clip's on-screen time. Build an SRT from the narration plus measured timings. Whisper alignment is an upgrade path.

### Step 7: FFmpeg assembly (Execute Command node)
- Normalize every clip to the same size, fps, and pixel format.
- Trim or slow-pad each clip to its narration duration; concat; add a low-volume background music bed (royalty-free, stored in the repo or the data volume); burn captions; add a short end card.
- Output `final.mp4` (H.264/AAC, `-movflags +faststart`) and a `thumb.jpg` (frame grab plus title text).

### Step 8: YouTube upload
- Auth: OAuth 2.0 with offline refresh token (n8n's YouTube credential). Scope `youtube.upload` (plus `youtube` if setting thumbnails).
- Set explicitly: `snippet.title/description/tags/categoryId`, `status.privacyStatus` (`private` during testing, `public` once trusted), `status.selfDeclaredMadeForKids=false`, and **`status.containsSyntheticMedia=true`**, the AI-content disclosure flag.
- Use the resumable upload endpoint for reliability; set the thumbnail afterwards via `thumbnails.set` (requires a verified channel).
- Optionally upload as `private` with `publishAt` for a fixed publish time.

### Step 9: Logging and notifications
Write the row (topic, video id, URL, total OpenRouter cost from each job's `usage.cost`, duration). Send a success or failure message to the owner (email, Telegram, or Slack, owner's choice). Delete scene files older than 7 days.

---

## 6. Config (env vars / n8n variables)

```
OPENROUTER_API_KEY
TEXT_MODEL=<an OpenRouter text model slug>
VIDEO_MODEL_PRIMARY=<slug from /videos/models>
VIDEO_MODEL_FALLBACK=<slug>
VIDEO_RESOLUTION=720p
ASPECT_RATIO=9:16
SCENE_SECONDS=5
MAX_SCENES=12
GENERATE_AUDIO=false
CHANNEL_NICHE=<TO BE DECIDED>
PRIVACY_STATUS=private        # flip to public after the trial period
MAX_COST_PER_VIDEO_USD=<cap>  # run aborts if projected cost exceeds this
PARALLEL_SCENES=3
```

Never commit secrets. Use n8n credentials and a `.env.example` in the repo.

---

## 7. Cost model

`cost_per_video = scenes × per_clip_price(model, resolution, duration) + text LLM calls + TTS`.

Prices vary by model by orders of magnitude, so the plan is to have the workflow read pricing from `/videos/models`, **compute a projected cost before submitting**, and abort if it exceeds `MAX_COST_PER_VIDEO_USD`. Record the actual cost per run from each job's `usage.cost`. Build a cheap-model test run first (Milestone 3) and extrapolate monthly spend from it before turning on the daily schedule. Set a credit limit on the OpenRouter key as a hard backstop.

---

## 8. Repo layout (proposed)

```
/
├─ README.md                  # setup and runbook
├─ PLAN.md                    # this file
├─ CLAUDE.md                  # build conventions for Claude Code
├─ docker-compose.yml         # n8n + ffmpeg (custom image) + volume
├─ Dockerfile                 # n8n image with ffmpeg and TTS installed
├─ .env.example
├─ workflows/
│  ├─ daily-explainer.json    # main workflow export
│  └─ error-handler.json
├─ scripts/
│  ├─ assemble.sh             # ffmpeg pipeline (also runnable standalone)
│  ├─ make_srt.py
│  ├─ validate_storyboard.py  # JSON schema check
│  └─ openrouter_video.py     # submit/poll/download helper for local testing
├─ prompts/
│  ├─ topic.md
│  └─ storyboard.md
├─ schemas/storyboard.schema.json
├─ assets/music/              # royalty-free tracks with licenses noted
└─ tests/                     # fixture storyboards, fake clips for FFmpeg tests
```

Design rule: keep heavy logic in `scripts/` (testable without n8n) and let n8n call it. Export workflow JSON to git after every change.

---

## 9. Milestones (for Claude Code, each with a check)

1. **Scaffold and infra.** Docker Compose with n8n plus ffmpeg, volume mounts, `.env.example`. *Done when:* `docker compose up` gives a working n8n and `ffmpeg -version` runs inside the container.
2. **Text pipeline.** Topic picker and storyboard generator with schema validation and history store. *Done when:* 5 consecutive runs give valid, non-duplicate storyboards.
3. **Single-clip video test.** `openrouter_video.py` submits, polls, and downloads one clip on the cheapest model; log the real cost. *Done when:* a playable MP4 is on disk and cost is recorded.
4. **Multi-scene generation.** Parallel submit, retry, fallback model, optional webhook, optional frame chaining. *Done when:* a full storyboard yields all clips with failure handling tested (simulate a failed job).
5. **Audio and assembly.** TTS, SRT, `assemble.sh`. *Done when:* given fixture clips plus narration, a captioned `final.mp4` plays correctly at the target runtime (testable offline, no API spend).
6. **YouTube upload.** OAuth setup guide, resumable upload, thumbnail, synthetic-media flag. *Done when:* a **private** test video appears in YouTube Studio with correct metadata.
7. **End-to-end and scheduling.** Wire everything in n8n, error workflow, notifications, cost cap. *Done when:* 3 consecutive scheduled private runs succeed unattended.
8. **Go live.** Flip to public (or scheduled publish), review the first week of output manually, then tune prompts.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **YouTube "inauthentic / mass-produced content" policy** can demonetize or limit channels that post templated, low-effort uploads | Make each video genuinely informative, vary structure and visuals, add real narration and value, and review output early. Treat monetization as not guaranteed. |
| **AI disclosure** requirements | Always set `containsSyntheticMedia=true`; mention AI generation in the description. |
| Visual inconsistency and artifacts between AI clips | Shared `style_guide`, seed reuse, frame chaining, and a quick automated check (non-black frames, correct duration). Drop weak scenes where possible. |
| Factual errors in explanations | Keep topics well-known, ask the LLM for conservative claims, and consider a second LLM "fact-check" pass flagged in the log; manual spot checks in week one. |
| Cost surprises | Pre-run cost projection, `MAX_COST_PER_VIDEO_USD`, OpenRouter key credit limit, per-run cost log. |
| Model availability or API changes (video API is new) | Discover models at runtime, fallback model, pin nothing that the models endpoint can tell us. |
| Upload may be forced private if the Google project is treated as unverified | Test in Milestone 6; if so, apply for the YouTube API compliance audit. |
| OAuth refresh token expiry (apps in "Testing" mode expire tokens in 7 days) | Publish the OAuth consent screen to "In production" and document it in the README. |
| n8n host downtime | Run on an always-on VPS; add a heartbeat notification so a missed day is noticed. |
| Copyright (music, likenesses) | Royalty-free music only with license noted; forbid real people and trademarked characters in prompts. |

---

## 11. Open questions for the owner

1. **Niche** for the channel (the main missing input). Pick something you can stand behind on accuracy; the pipeline treats it as one setting.
2. **Where n8n will run** (VPS, home server, or n8n Cloud). n8n Cloud cannot run FFmpeg through Execute Command, so FFmpeg would have to move to a small separate service.
3. **TTS choice** (free local voice vs. paid higher-quality voice).
4. **Format:** Shorts only to start, or also long-form later?
5. **Monthly budget** for generation, to set the cost cap and pick the model tier.
6. **Notification channel** (email, Telegram, Slack).
7. **Publish timing** (immediately vs. a fixed daily slot, and the audience time zone).

---

## 12. Instructions for Claude Code

- Work milestone by milestone; do not start the next until the "done when" check passes and is committed.
- Anything that spends money (video generation, paid TTS) must be behind an explicit `--live` flag or env switch and respect `MAX_COST_PER_VIDEO_USD`. Default every test to fixtures or the cheapest model.
- Never hardcode secrets, model slugs, or per-model limits; read them from config or the `/videos/models` endpoint.
- Keep `PRIVACY_STATUS=private` until the owner approves going public.
- Document every manual setup step (OpenRouter key, Google Cloud project, OAuth consent screen, YouTube channel verification) in `README.md`.
