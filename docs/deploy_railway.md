# Проверка бота на Railway

## Перед деплоем

1. В Supabase выполнить SQL из `supabase/schema.sql`.
2. В Supabase Storage создать приватный bucket:

```text
player-uploads
```

3. В BotFather создать тестового бота и получить token.

## GitHub

Залей проект в GitHub. Файл `.env` не должен попадать в репозиторий.

## Railway

1. Создать новый проект в Railway.
2. Выбрать деплой из GitHub repository.
3. Указать этот репозиторий.
4. В Variables добавить:

```text
BOT_TOKEN=токен_бота_из_BotFather
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=service_role_key_из_Supabase
SUPABASE_UPLOAD_BUCKET=player-uploads
ADMIN_IDS=telegram_id_админов_через_запятую
STORY_FILE=content/story.yaml
MAX_UPLOAD_BYTES=10485760
```

5. Запустить deploy.

Railway возьмет команду запуска из `railway.json`:

```text
python -m src.main
```

## Как проверить сценарий

1. Открыть тестового бота в Telegram.
2. Отправить `/start`.
3. Пройти первый акт:
   - нажать `да, вроде того...`;
   - написать `1, 2, 3` или `123`;
   - нажать `кто ты?`;
   - выбрать `она помогла мне`;
   - написать имя;
   - пройти дальше по кнопкам.

## Важный момент

Пока бот запущен на Railway, не запускай локально этот же `BOT_TOKEN`. Для long polling должна работать одна активная копия бота.
