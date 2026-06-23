# Формат сценария

Сюжет хранится в `content/story.yaml`.

## Обычный текст

```yaml
messages:
  - type: text
    text: |
      <b>Обычное сообщение</b>

      Можно использовать Telegram HTML.
```

## Первое появление персонажа

Этот тип собирается в две цитаты:

- первая цитата: 3 строки с custom emoji;
- вторая строка первой цитаты содержит короткую фразу до 15 символов;
- вторая цитата: основной текст реплики.

```yaml
messages:
  - type: character
    character: placeholder
    variant: intro
    label: "чего ждешь?"
    text: "свою очередь? так вот же кабинет, заходи!"
```

## Следующая реплика персонажа

Этот тип собирается в одну цитату:

```yaml
messages:
  - type: character
    character: placeholder
    variant: compact
    text: "чего ждешь? свою очередь?"
```

## Реплика без эмодзи

Этот тип отправляется обычным текстом без цитаты и без custom emoji:

```yaml
messages:
  - type: character
    character: masha
    variant: default
    text: "эй...эй..."
```

## Заглушка медиа или достижения

Пока нет реального `file_id`, можно ставить заглушку:

```yaml
messages:
  - type: placeholder
    label: "видеокружок"
    text: "трясущаяся камера, проявляется медсестра"
```

## Кнопка, которая отправляет текст

Для Reply Keyboard используется `reply_choice`. После нажатия Telegram отправит текст выбранной кнопки как обычное сообщение:

```yaml
interaction:
  type: reply_choice
  choices:
    - id: who_are_you
      label: "кто ты?"
      target: act1_who_are_you
```

## Проверка текстового ввода

Обычная проверка:

```yaml
interaction:
  type: text_input
  answers:
    - "пароль"
  on_correct: next_segment
  on_wrong: current_segment
```

Проверка цифр игнорирует пробелы, запятые и другую пунктуацию. Например, `1, 2, 3`, `1 2 3` и `123` будут одинаковыми:

```yaml
interaction:
  type: text_input
  answer_mode: digits
  answers:
    - "123"
  on_correct: next_segment
```

## Сохранение имени

```yaml
interaction:
  type: capture_text
  variable: player_name
  target: next_segment
```

После этого имя можно подставлять в текст:

```yaml
text: "приятно познакомиться, {player_name}."
```

## Эмодзи персонажа

Пока у персонажей стоят временные custom emoji из примера. Позже для каждого персонажа можно завести свой набор:

```yaml
characters:
  clerk:
    intro_emoji_ids:
      - "custom_emoji_id_1"
      - "custom_emoji_id_2"
      - "custom_emoji_id_3"
      - "custom_emoji_id_4"
      - "custom_emoji_id_5"
      - "custom_emoji_id_6"
      - "custom_emoji_id_7"
      - "custom_emoji_id_8"
      - "custom_emoji_id_9"
    compact_emoji_id: "single_custom_emoji_id"
```

Если в `intro_emoji_ids` меньше 9 emoji, рендерер повторит их до нужного количества.
Для `compact` используется `compact_emoji_id`.
