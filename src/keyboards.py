from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def choice_keyboard(segment_id: str, choices: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for choice in choices:
        callback_data = f"choice:{segment_id}:{choice['id']}"
        rows.append([InlineKeyboardButton(text=choice["label"], callback_data=callback_data)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reply_choice_keyboard(choices: list[dict]) -> ReplyKeyboardMarkup:
    rows = []
    for choice in choices:
        rows.append([KeyboardButton(text=choice["label"])])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выбери вариант",
    )
