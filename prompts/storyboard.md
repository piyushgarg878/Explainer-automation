<!-- Storyboard prompt. Variables: {{TOPIC}}, {{ANGLE}}, {{MAX_SCENES}}, {{SCENE_SECONDS}} -->
Write a short explainer script and storyboard for: {{TOPIC}} ({{ANGLE}}).
Return JSON matching schemas/storyboard.schema.json. Rules:
- At most {{MAX_SCENES}} scenes of about {{SCENE_SECONDS}}s each.
- Conservative, accurate claims only.
- visual_prompt must be self-contained; no real people or trademarked characters.
- One shared style_guide used across all scenes.
- Health content: state only well-established science; use hedged wording ("can", "tends to") where effects vary by person.
- Never give medical advice, diagnoses, or dosages. Final scene must say this is general education, not medical advice.
- Visuals: stylized/educational anatomy only; no graphic gore, real patients, or branded food/drug products.
