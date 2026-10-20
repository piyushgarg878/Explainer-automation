# Architecture

n8n is a thin **orchestrator**. Heavy logic lives in `scripts/` (testable without n8n); n8n schedules, branches, retries and notifies.

```
Schedule ─► Topic ─► Storyboard ─► Gate ─► Scenes (parallel) ─► Poll/Download
                                                                    │
 Notify ◄─ Log ◄─ YouTube upload ◄─ FFmpeg assemble ◄─ TTS + SRT ◄──┘
   ▲
   └── Error workflow (any failure) ── marks run `failed`, re-runnable
```

## Components

| Layer | Piece | Responsibility | Lives in |
|---|---|---|---|
| Orchestration | n8n `daily-explainer` workflow | Trigger, sequencing, retries, parallel cap | `workflows/` |
| Orchestration | n8n `error-handler` workflow | Notify, mark run failed | `workflows/` |
| LLM | Topic + storyboard prompts | Via OpenRouter chat API, JSON output | `prompts/`, `schemas/` |
| Gate | `validate_storyboard.py` | Schema, scene cap, runtime match | `scripts/` |
| Video | `openrouter_video.py` | Discover models, cost projection, submit/poll/download | `scripts/` |
| Audio | TTS + `make_srt.py` | Per-scene audio, measured durations, SRT | `scripts/` |
| Assembly | `assemble.sh` | Normalize, concat, mix, captions, thumbnail | `scripts/` |
| Publish | n8n YouTube node / resumable upload | Upload with explicit privacy + synthetic-media flag | n8n |
| State | `topics_history` + per-run folder | Dedup, cost log, idempotent re-runs | `data/` |

## Contracts between stages

Each stage reads/writes files in a per-run directory, so any stage can be re-run alone:

```
data/runs/<YYYY-MM-DD>/
  topic.json          # {topic, angle}
  storyboard.json     # validated against schemas/storyboard.schema.json
  scenes/scene_<n>.mp4
  audio/scene_<n>.wav
  captions.srt
  final.mp4, thumb.jpg
  run.json            # status, per-stage cost (usage.cost), video_id, timings
```

`run.json.status`: `pending → generating → assembling → uploaded | failed`.

## Cross-cutting rules

- **Config:** all settings come from env (`.env.example`, `scripts/config.py`); no hardcoded secrets, model slugs or per-model limits.
- **Cost safety:** anything that spends money requires `LIVE=true` and a projected cost <= `MAX_COST_PER_VIDEO_USD`.
- **Privacy:** `PRIVACY_STATUS=private` until the owner approves going public; `containsSyntheticMedia=true` always.
- **Niche:** a single value, `CHANNEL_NICHE`, injected into the topic prompt.
- **Idempotency:** a run is keyed by date; re-running skips stages whose outputs already exist.

## Open decisions (from PLAN.md section 11)

TTS provider, Shorts vs long-form, budget, notification channel, publish timing.

## Decisions made

- **Niche:** health / human body explainers (`CHANNEL_NICHE`).
- **Hosting:** runs on the owner's PC first via Docker Desktop, then moves to a server. The Docker setup is identical in both; only `.env` and the `data/` volume move. Note a PC that sleeps will miss the daily run.
- **Channel:** new dedicated YouTube channel (OAuth must be done with the account that owns it; pick that channel at consent time).

## Health-niche safeguards

Health content is sensitive for YouTube policy and for viewers. The pipeline therefore adds:
1. Prompt rules: well-established science only, hedged wording, no medical advice, closing "general education" line.
2. Gate step (milestone 2): second LLM pass that lists factual claims and flags risky ones (cures, dosages, absolutes); flagged storyboards fail the run for manual review.
3. Description always includes a not-medical-advice disclaimer and the AI-generated disclosure.
4. Week-one manual review of every video before `PRIVACY_STATUS=public`.
