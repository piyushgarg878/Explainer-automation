# Explainer Automation

Daily AI explainer video -> YouTube, orchestrated by n8n with OpenRouter. See [PLAN.md](PLAN.md) for the full plan and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design.

## Status

Milestone 1 (scaffold) in progress. Pipeline stages are stubs except storyboard validation.

## Quick start

```bash
cp .env.example .env      # fill in OPENROUTER_API_KEY and N8N_ENCRYPTION_KEY
docker compose up -d --build
docker compose exec n8n ffmpeg -version
# n8n UI: http://localhost:5678
```

Run tests locally:

```bash
pip install -r scripts/requirements.txt pytest
pytest
```

## Manual setup steps (to be expanded per milestone)

- OpenRouter: create API key, set a credit limit on it.
- Google Cloud: project, YouTube Data API v3, OAuth consent screen (publish to "In production" so refresh tokens don't expire in 7 days).
- YouTube: verify the channel (needed for custom thumbnails).
