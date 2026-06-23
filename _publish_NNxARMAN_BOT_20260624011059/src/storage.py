from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client


class SupabaseStore:
    def __init__(self, url: str, service_role_key: str, upload_bucket: str) -> None:
        self.client: Client = create_client(url, service_role_key)
        self.upload_bucket = upload_bucket

    def upsert_player(self, user: Any, start_segment: str) -> None:
        payload = {
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "current_segment": start_segment,
        }
        self.client.table("players").upsert(payload, on_conflict="telegram_id").execute()
        self.client.table("player_state").upsert(
            {"telegram_id": user.id},
            on_conflict="telegram_id",
        ).execute()

    def get_player(self, telegram_id: int) -> dict[str, Any] | None:
        response = (
            self.client.table("players")
            .select("*")
            .eq("telegram_id", telegram_id)
            .maybe_single()
            .execute()
        )
        return response.data

    def get_state(self, telegram_id: int) -> dict[str, Any]:
        response = (
            self.client.table("player_state")
            .select("*")
            .eq("telegram_id", telegram_id)
            .maybe_single()
            .execute()
        )
        if response.data is None:
            return {}

        return response.data.get("vars") or {}

    def update_vars(self, telegram_id: int, values: dict[str, Any]) -> None:
        current_vars = self.get_state(telegram_id)
        current_vars.update(values)
        self.client.table("player_state").upsert(
            {
                "telegram_id": telegram_id,
                "vars": current_vars,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="telegram_id",
        ).execute()

    def set_current_segment(self, telegram_id: int, act_id: str, segment_id: str) -> None:
        self.client.table("players").update(
            {
                "current_act": act_id,
                "current_segment": segment_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("telegram_id", telegram_id).execute()

    def log_event(
        self,
        telegram_id: int,
        event_type: str,
        act_id: str | None = None,
        segment_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.client.table("events").insert(
            {
                "telegram_id": telegram_id,
                "event_type": event_type,
                "act_id": act_id,
                "segment_id": segment_id,
                "payload": payload or {},
            }
        ).execute()

    def upload_bytes(self, path: str, data: bytes, content_type: str) -> None:
        self.client.storage.from_(self.upload_bucket).upload(
            path,
            data,
            file_options={"content-type": content_type},
        )

    def save_upload(self, payload: dict[str, Any]) -> None:
        self.client.table("uploads").insert(payload).execute()
