"""Central config: every script reads settings from here (env vars), never hardcodes them."""
import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Config:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base: str = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
    text_model: str = os.getenv("TEXT_MODEL", "")
    video_model_primary: str = os.getenv("VIDEO_MODEL_PRIMARY", "")
    video_model_fallback: str = os.getenv("VIDEO_MODEL_FALLBACK", "")
    resolution: str = os.getenv("VIDEO_RESOLUTION", "720p")
    aspect_ratio: str = os.getenv("ASPECT_RATIO", "9:16")
    scene_seconds: int = int(os.getenv("SCENE_SECONDS", "5"))
    max_scenes: int = int(os.getenv("MAX_SCENES", "12"))
    generate_audio: bool = _bool("GENERATE_AUDIO")
    parallel_scenes: int = int(os.getenv("PARALLEL_SCENES", "3"))
    channel_niche: str = os.getenv("CHANNEL_NICHE", "")
    privacy_status: str = os.getenv("PRIVACY_STATUS", "private")
    max_cost_usd: float = float(os.getenv("MAX_COST_PER_VIDEO_USD") or 0)
    live: bool = _bool("LIVE")  # gate for anything that spends money
    data_dir: str = os.getenv("DATA_DIR", "/data")
