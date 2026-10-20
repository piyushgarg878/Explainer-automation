# Build conventions

- Follow PLAN.md section 12: one milestone at a time, commit when its "done when" check passes.
- Keep logic in `scripts/` (unit-testable); n8n only orchestrates. Export workflow JSON to `workflows/` after every change.
- Paid calls (video, paid TTS) only behind `LIVE=true`/`--live` and `MAX_COST_PER_VIDEO_USD`. Default tests to fixtures.
- Never hardcode secrets, model slugs, or per-model limits. Never commit `.env`.
- Keep `PRIVACY_STATUS=private` until the owner approves.
- Run `pytest` before committing.
