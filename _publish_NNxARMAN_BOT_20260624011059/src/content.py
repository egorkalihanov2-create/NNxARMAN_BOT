from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class StoryContent:
    start_segment: str
    acts: dict[str, Any]
    characters: dict[str, Any]
    segments: dict[str, Any]

    def segment(self, segment_id: str) -> dict[str, Any]:
        try:
            return self.segments[segment_id]
        except KeyError as exc:
            raise KeyError(f"Unknown segment: {segment_id}") from exc


def load_story(path: str) -> StoryContent:
    story_path = Path(path)
    with story_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    return StoryContent(
        start_segment=raw["start_segment"],
        acts=raw.get("acts", {}),
        characters=raw.get("characters", {}),
        segments=raw["segments"],
    )


def normalize_answer(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def normalize_digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())
