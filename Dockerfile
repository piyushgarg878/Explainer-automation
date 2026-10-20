FROM docker.n8n.io/n8nio/n8n:latest
USER root
# ffmpeg + python for scripts/; TTS engine (piper) is added in Milestone 5.
RUN apk add --no-cache ffmpeg python3 py3-pip py3-jsonschema py3-requests
USER node
