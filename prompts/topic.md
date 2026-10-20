<!-- Topic picker prompt. Variables: {{CHANNEL_NICHE}}, {{RECENT_TOPICS}} -->
You choose one new, specific, explainable topic for a short explainer video.
Niche: {{CHANNEL_NICHE}}
Do not repeat or closely resemble any of these recent topics:
{{RECENT_TOPICS}}
Return JSON: {"topic": "...", "angle": "one line"}

Health-niche rules:
- Educational physiology/nutrition/"what happens when" topics only (e.g. how the heart pumps, what sugar does to the body).
- No diagnosis, treatment advice, miracle cures, dosage guidance, or fear-based claims.
- Prefer well-established science over new or contested studies.
