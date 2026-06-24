from __future__ import annotations

from html import escape
from itertools import cycle, islice
from typing import Any

FALLBACK_CUSTOM_EMOJI = "\U0001f5dd"
DEFAULT_CUSTOM_EMOJI_IDS = [
    "5321047528613915200",
    "5321462078857323645",
    "5321279864869791965",
    "5321232976711817313",
    "5321393247711435145",
    "5321512931270108410",
    "5321144569105000634",
    "5321455262744226265",
    "5321018477455125387",
]


def render_segment_messages(
    segment: dict[str, Any],
    characters: dict[str, Any],
    variables: dict[str, Any] | None = None,
) -> list[str]:
    variables = variables or {}

    if "messages" in segment:
        return [render_message(message, characters, variables) for message in segment["messages"]]

    text = segment.get("text", "")
    return [apply_template(text, variables)] if text else []


def render_message(message: dict[str, Any], characters: dict[str, Any], variables: dict[str, Any]) -> str:
    message_type = message.get("type", "text")

    if message_type == "text":
        return apply_template(message.get("text", ""), variables, escape_values=True)

    if message_type == "character":
        return render_character_message(message, characters, variables)

    if message_type == "placeholder":
        return render_placeholder(message, variables)

    if message_type == "player_line":
        return render_player_line(message, variables)

    raise ValueError(f"Unknown message type: {message_type}")


def render_character_message(
    message: dict[str, Any],
    characters: dict[str, Any],
    variables: dict[str, Any] | None = None,
) -> str:
    variables = variables or {}
    character = characters.get(message.get("character"), {})
    variant = message.get("variant", "compact")
    text = apply_template(message.get("text", ""), variables)

    if variant in {"intro", "first"}:
        emoji_ids = (
            message.get("intro_emoji_ids")
            or message.get("emoji_ids")
            or character.get("intro_emoji_ids")
            or character.get("emoji_ids")
            or DEFAULT_CUSTOM_EMOJI_IDS
        )
        return render_character_intro(
            emoji_ids=emoji_ids,
            label=apply_template(message.get("label", ""), variables),
            text=text,
        )

    if variant == "compact":
        emoji_id = (
            message.get("compact_emoji_id")
            or character.get("compact_emoji_id")
            or next(iter(character.get("emoji_ids", [])), DEFAULT_CUSTOM_EMOJI_IDS[0])
        )
        return render_character_compact(
            emoji_id=emoji_id,
            text=text,
        )

    if variant in {"default", "plain"}:
        return escape(text)

    raise ValueError(f"Unknown character message variant: {variant}")


def render_character_intro(emoji_ids: list[str], label: str, text: str) -> str:
    if len(label) > 15:
        raise ValueError(f"Character intro label must be 15 characters or shorter: {label}")

    emojis = list(islice(cycle(emoji_ids), 9))
    lines = [
        "".join(tg_emoji(emoji_id) for emoji_id in emojis[0:3]),
        f"{''.join(tg_emoji(emoji_id) for emoji_id in emojis[3:6])} {escape(label)}",
        "".join(tg_emoji(emoji_id) for emoji_id in emojis[6:9]),
    ]

    badge_quote = f"<blockquote>{'\n'.join(lines)}</blockquote>"
    text_quote = f"<blockquote>{escape(text)}</blockquote>"
    return f"{badge_quote}\n{text_quote}"


def render_character_compact(emoji_id: str, text: str) -> str:
    return f"<blockquote>{tg_emoji(emoji_id)} {escape(text)}</blockquote>"


def render_placeholder(message: dict[str, Any], variables: dict[str, Any]) -> str:
    label = apply_template(message.get("label", "заглушка"), variables)
    text = apply_template(message.get("text", ""), variables)
    if text:
        return f"<i>[{escape(label)}: {escape(text)}]</i>"

    return f"<i>[{escape(label)}]</i>"


def render_player_line(message: dict[str, Any], variables: dict[str, Any]) -> str:
    text = apply_template(message.get("text", ""), variables, escape_values=True)
    return f"- {text}"


def apply_template(text: str, variables: dict[str, Any], escape_values: bool = False) -> str:
    rendered = text
    for key, value in variables.items():
        replacement = str(value)
        if escape_values:
            replacement = escape(replacement)
        rendered = rendered.replace("{" + key + "}", replacement)
    return rendered


def tg_emoji(emoji_id: str) -> str:
    return f'<tg-emoji emoji-id="{escape(emoji_id, quote=True)}">{FALLBACK_CUSTOM_EMOJI}</tg-emoji>'
