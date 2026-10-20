<!-- Storyboard prompt. Variables: {{TOPIC}}, {{ANGLE}}, {{MAX_SCENES}}, {{SCENE_SECONDS}} -->
Write a short explainer script and storyboard for: {{TOPIC}} ({{ANGLE}}).
Return JSON matching schemas/storyboard.schema.json. Rules:
- At most {{MAX_SCENES}} scenes of about {{SCENE_SECONDS}}s each.
- Conservative, accurate claims only.
- visual_prompt must be self-contained; no real people or trademarked characters.
- One shared style_guide used across all scenes.
