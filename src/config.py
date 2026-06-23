from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    supabase_url: str
    supabase_service_role_key: str
    upload_bucket: str
    admin_ids: set[int]
    story_file: str
    max_upload_bytes: int


def _parse_admin_ids(value: str) -> set[int]:
    result: set[int] = set()
    for raw_id in value.split(","):
        raw_id = raw_id.strip()
        if raw_id:
            result.add(int(raw_id))
    return result


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.environ["BOT_TOKEN"]
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    return Settings(
        bot_token=bot_token,
        supabase_url=supabase_url,
        supabase_service_role_key=supabase_key,
        upload_bucket=os.getenv("SUPABASE_UPLOAD_BUCKET", "player-uploads"),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        story_file=os.getenv("STORY_FILE", "content/story.yaml"),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", "10485760")),
    )
