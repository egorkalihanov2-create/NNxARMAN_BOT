from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from html import escape
from pathlib import PurePosixPath

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from src.config import load_settings
from src.content import load_story, normalize_answer, normalize_digits
from src.keyboards import choice_keyboard, reply_choice_keyboard
from src.rendering import render_segment_messages
from src.storage import SupabaseStore

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}


settings = load_settings()
story = load_story(settings.story_file)
store = SupabaseStore(
    settings.supabase_url,
    settings.supabase_service_role_key,
    settings.upload_bucket,
)

bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def run_blocking(func, *args):
    return await asyncio.to_thread(func, *args)


async def delete_message_safely(chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass


async def delete_tracked_messages(messages: list[dict]) -> None:
    message_ids_by_chat: dict[int, list[int]] = {}
    seen: set[tuple[int, int]] = set()

    for item in messages:
        chat_id = item.get("chat_id")
        message_id = item.get("message_id")
        if not chat_id or not message_id:
            continue

        key = (int(chat_id), int(message_id))
        if key in seen:
            continue
        seen.add(key)
        message_ids_by_chat.setdefault(key[0], []).append(key[1])

    fallback_tasks = []
    for chat_id, message_ids in message_ids_by_chat.items():
        for offset in range(0, len(message_ids), 100):
            chunk = message_ids[offset : offset + 100]
            try:
                await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
            except AttributeError:
                fallback_tasks.extend(
                    delete_message_safely(chat_id=chat_id, message_id=message_id)
                    for message_id in chunk
                )
            except TelegramBadRequest:
                fallback_tasks.extend(
                    delete_message_safely(chat_id=chat_id, message_id=message_id)
                    for message_id in chunk
                )

    if fallback_tasks:
        await asyncio.gather(*fallback_tasks)


async def send_segment(
    message: Message,
    segment_id: str,
    clear_keyboard: bool = False,
    player_id: int | None = None,
    trigger_message_id: int | None = None,
    force_cleanup: bool = False,
) -> None:
    segment = story.segment(segment_id)
    act_id = segment["act"]
    interaction = segment.get("interaction", {})
    telegram_id = player_id or message.from_user.id
    mini_segment_id = segment.get("mini_segment", segment_id)

    variables = await run_blocking(store.get_state, telegram_id)
    active_messages = list(variables.get("_active_messages", []))
    previous_mini_segment_id = variables.get("_active_mini_segment")
    trigger_message = (
        {"chat_id": message.chat.id, "message_id": trigger_message_id}
        if trigger_message_id
        else None
    )

    should_cleanup = force_cleanup or (
        previous_mini_segment_id is not None
        and previous_mini_segment_id != mini_segment_id
        and segment.get("cleanup_previous", True)
    )

    cleanup_messages: list[dict] = []
    if should_cleanup:
        cleanup_messages = active_messages.copy()
        if trigger_message:
            cleanup_messages.append(trigger_message)
        active_messages = []
    elif trigger_message:
        active_messages.append(trigger_message)

    if should_cleanup:
        await delete_tracked_messages(cleanup_messages)
        await asyncio.sleep(float(segment.get("after_cleanup_delay_seconds", 0.6)))

    await run_blocking(store.set_current_segment, telegram_id, act_id, segment_id)
    await run_blocking(store.log_event, telegram_id, "segment_opened", act_id, segment_id)

    rendered_messages = render_segment_messages(segment, story.characters, variables)

    reply_markup = None
    if interaction.get("type") == "choice":
        reply_markup = choice_keyboard(segment_id, interaction.get("choices", []))
    elif interaction.get("type") == "reply_choice":
        reply_markup = reply_choice_keyboard(interaction.get("choices", []))

    for index, rendered_message in enumerate(rendered_messages):
        if index > 0:
            previous_message = rendered_messages[index - 1]
            await asyncio.sleep(min(max(len(previous_message) / 90, 2.0), 4.0))

        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await asyncio.sleep(min(max(len(rendered_message) / 700, 0.4), 2.2))

        is_last_message = index == len(rendered_messages) - 1
        message_reply_markup = reply_markup if is_last_message else None
        if clear_keyboard and index == 0 and message_reply_markup is None:
            message_reply_markup = ReplyKeyboardRemove()

        sent_message = await message.answer(
            rendered_message,
            reply_markup=message_reply_markup,
        )
        active_messages.append({"chat_id": sent_message.chat.id, "message_id": sent_message.message_id})

    await run_blocking(
        store.update_vars,
        telegram_id,
        {
            "_active_mini_segment": mini_segment_id,
            "_active_messages": active_messages,
        },
    )

    if interaction.get("type") == "auto":
        reading_delay = min(max(sum(len(item) for item in rendered_messages) / 350, 5.0), 7.0)
        await asyncio.sleep(max(float(interaction.get("delay_seconds", 0)), reading_delay))
        await send_segment(message, interaction["target"], player_id=telegram_id)


def find_choice(segment: dict, choice_id: str) -> dict | None:
    for choice in segment.get("interaction", {}).get("choices", []):
        if choice["id"] == choice_id:
            return choice
    return None


def find_reply_choice(segment: dict, text: str) -> dict | None:
    normalized_text = normalize_answer(text)
    for choice in segment.get("interaction", {}).get("choices", []):
        accepted_values = [choice.get("label", ""), choice.get("text", "")]
        accepted_values.extend(choice.get("aliases", []))
        if normalized_text in {normalize_answer(value) for value in accepted_values if value}:
            return choice

    return None


def is_expected_answer(interaction: dict, text: str) -> bool:
    answers = interaction.get("answers", [])
    if interaction.get("answer_mode") == "digits":
        return normalize_digits(text) in {normalize_digits(answer) for answer in answers}

    return normalize_answer(text) in {normalize_answer(answer) for answer in answers}


async def ensure_player(message: Message) -> None:
    player = await run_blocking(store.get_player, message.from_user.id)
    if player is None:
        await run_blocking(store.upsert_player, message.from_user, story.start_segment)


@dp.message(Command("start"))
async def start(message: Message) -> None:
    await run_blocking(store.upsert_player, message.from_user, story.start_segment)
    await run_blocking(store.log_event, message.from_user.id, "game_started")
    await send_segment(message, story.start_segment, force_cleanup=True)


@dp.callback_query(F.data.startswith("choice:"))
async def process_choice(callback: CallbackQuery) -> None:
    _, segment_id, choice_id = callback.data.split(":", 2)
    segment = story.segment(segment_id)
    choice = find_choice(segment, choice_id)

    if choice is None:
        await callback.answer("Этот вариант уже недоступен.", show_alert=True)
        return

    await callback.answer()
    await run_blocking(
        store.log_event,
        callback.from_user.id,
        "choice_selected",
        segment.get("act"),
        segment_id,
        {"choice_id": choice_id, "label": choice.get("label")},
    )

    await send_segment(callback.message, choice["target"], player_id=callback.from_user.id)


@dp.message(F.text)
async def process_text(message: Message) -> None:
    await ensure_player(message)
    player = await run_blocking(store.get_player, message.from_user.id)
    segment_id = player["current_segment"]
    segment = story.segment(segment_id)
    interaction = segment.get("interaction", {})

    if interaction.get("type") == "reply_choice":
        choice = find_reply_choice(segment, message.text)
        if choice is None:
            await message.answer("Выбери один из вариантов на клавиатуре.")
            return

        await run_blocking(
            store.log_event,
            message.from_user.id,
            "reply_choice_selected",
            segment.get("act"),
            segment_id,
            {"text": message.text, "choice_id": choice.get("id")},
        )
        await send_segment(message, choice["target"], clear_keyboard=True, trigger_message_id=message.message_id)
        return

    if interaction.get("type") == "capture_text":
        variable_name = interaction["variable"]
        value = message.text.strip()
        await run_blocking(store.update_vars, message.from_user.id, {variable_name: value})
        await run_blocking(
            store.log_event,
            message.from_user.id,
            "text_captured",
            segment.get("act"),
            segment_id,
            {"variable": variable_name, "value": value},
        )
        await send_segment(message, interaction["target"], trigger_message_id=message.message_id)
        return

    if interaction.get("type") != "text_input":
        await message.answer("Сейчас здесь нужен выбор кнопкой или другой тип действия.")
        return

    is_correct = is_expected_answer(interaction, message.text)
    event_type = "text_answer_correct" if is_correct else "text_answer_wrong"
    target = interaction["on_correct"] if is_correct else interaction.get("on_wrong", segment_id)

    await run_blocking(
        store.log_event,
        message.from_user.id,
        event_type,
        segment.get("act"),
        segment_id,
        {"text": message.text},
    )

    if not is_correct and interaction.get("wrong_text"):
        await message.answer(escape(interaction["wrong_text"]))

    await send_segment(message, target, trigger_message_id=message.message_id)


@dp.message(F.photo | F.document)
async def process_upload(message: Message) -> None:
    await ensure_player(message)
    player = await run_blocking(store.get_player, message.from_user.id)
    segment_id = player["current_segment"]
    segment = story.segment(segment_id)
    interaction = segment.get("interaction", {})

    if interaction.get("type") != "upload":
        await message.answer("Сейчас история не ждет файл. Продолжи текущий шаг.")
        return

    telegram_file_id = None
    telegram_file_unique_id = None
    file_size = None
    mime_type = "image/jpeg"
    original_name = None

    if message.document:
        telegram_file_id = message.document.file_id
        telegram_file_unique_id = message.document.file_unique_id
        file_size = message.document.file_size
        mime_type = message.document.mime_type or ""
        original_name = message.document.file_name
    elif message.photo:
        photo = message.photo[-1]
        telegram_file_id = photo.file_id
        telegram_file_unique_id = photo.file_unique_id
        file_size = photo.file_size
        original_name = f"{photo.file_unique_id}.jpg"

    if not telegram_file_id or not file_size:
        await message.answer("Не получилось прочитать файл. Попробуй отправить PNG или JPEG.")
        return

    if file_size > settings.max_upload_bytes:
        await run_blocking(
            store.log_event,
            message.from_user.id,
            "upload_rejected_size",
            segment.get("act"),
            segment_id,
            {"size_bytes": file_size},
        )
        await message.answer("Файл слишком большой. Максимум - 10 МБ.")
        return

    if mime_type not in ALLOWED_MIME_TYPES:
        await run_blocking(
            store.log_event,
            message.from_user.id,
            "upload_rejected_type",
            segment.get("act"),
            segment_id,
            {"mime_type": mime_type},
        )
        await message.answer("Подходит только PNG или JPEG.")
        return

    file = await bot.get_file(telegram_file_id)
    downloaded = await bot.download_file(file.file_path)
    data = downloaded.read()

    suffix = ".png" if mime_type == "image/png" else ".jpg"
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    storage_path = str(
        PurePosixPath(
            "uploads",
            str(message.from_user.id),
            f"{now}_{telegram_file_unique_id}{suffix}",
        )
    )

    await run_blocking(store.upload_bytes, storage_path, data, mime_type)
    await run_blocking(
        store.save_upload,
        {
            "telegram_id": message.from_user.id,
            "act_id": segment.get("act"),
            "segment_id": segment_id,
            "storage_bucket": settings.upload_bucket,
            "storage_path": storage_path,
            "original_name": original_name,
            "mime_type": mime_type,
            "size_bytes": len(data),
            "telegram_file_id": telegram_file_id,
            "telegram_file_unique_id": telegram_file_unique_id,
            "status": "accepted",
        },
    )
    await run_blocking(
        store.log_event,
        message.from_user.id,
        "upload_accepted",
        segment.get("act"),
        segment_id,
        {"storage_path": storage_path, "size_bytes": len(data), "mime_type": mime_type},
    )

    await message.answer("Файл принят и сохранен.")
    await send_segment(message, interaction["on_success"], trigger_message_id=message.message_id)


@dp.message()
async def process_unexpected(message: Message) -> None:
    await message.answer("Этот тип сообщения пока не подходит для текущего шага.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
