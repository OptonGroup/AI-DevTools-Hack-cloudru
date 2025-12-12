## Meeting Assistant Platform

Комплекс для работы с корпоративными встречами на Cloud.ru:
- A2A-агент (LangChain) с инструментами MCP.
- MCP Cloud.ru: S3 + Managed RAG (поиск/индексация).
- MCP Google Calendar: создание/получение событий.
- MCP FollowUp: запись и транскрибация созвонов.
- Telegram-бот: прокси к агенту.
- Demo App (Flask): отправка A2A-запросов в агента.

### Стек
- Python 3.12, LangChain, FastMCP, httpx/requests, Flask.
- Cloud.ru: Foundation Models (LLM), S3, Managed RAG, IAM.
- Google Calendar API (service account + OAuth), FollowUp API, Telegram Bot API.
- Docker + buildx (linux/amd64).

### Образы в реестре Cloud.ru
- Агент: `meeting-assistant.cr.cloud.ru/meeting-assistant-agent:latest` (v1.0.1).
- MCP Cloud.ru: `meeting-assistant.cr.cloud.ru/mcp-cloudru:latest`.

### Где взять секреты
- Все готовые `.env` с ключами лежат в архиве: https://disk.yandex.ru/d/AfNIXae-xX8vRQ  
  Внутри — по файлу `.env` на каждый сервис (агент, MCP, бот и т.д.) с нужными ключами и URL.

### Переменные окружения (основные)

**agent/.env.example**
- `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL` (префикс `hosted_vllm/` не нужен; в коде убирается автоматически).
- `FOLLOWUP_MCP_URL`, `GCALENDAR_MCP_URL`, `MANAGED_RAG_MCP_URL`.
- `PORT` (10000), `URL_AGENT`.

**mcp-cloudru/.env.example**
- `CLOUD_TENANT_ID`, `CLOUD_KEY_ID`, `CLOUD_SECRET`.
- `S3_BUCKET`, `S3_ENDPOINT`, `S3_REGION`.
- `RAG_PUBLIC_URL`, `RAG_VERSION_ID`.
- Индексация: `RAG_INDEXING_KEY_ID/SECRET`, `RAG_ID`, `PROJECT_ID`, `PRODUCT_INSTANCE_ID`, `S3_BUCKET_ID`.

**mcp-google-calendar/.env.example**
- Service Account: `GOOGLE_*` и `GOOGLE_CALENDAR_ID`.
- OAuth: `GOOGLE_OAUTH_CLIENT_ID/SECRET`.
- `PORT` (8001).

**mcp-followup/.env.example**
- `FOLLOWUP_EMAIL/PASSWORD` или `FOLLOWUP_API_KEY`.
- S3 для RAG синка: `CLOUD_RAG_S3_*`.
- `PORT` (8000).

**telegram-bot/.env.example**
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`.
- `AGENT_API_URL` — публичный A2A endpoint агента.

**demo-app/app.py**
- `BASE_URL` — A2A endpoint агента.
- `IAM_URL`, `IAM_CREDENTIALS` — keyId/secret Cloud.ru (вынесите в env в реальной среде).

### Быстрый локальный запуск (Python/uv)
Требуется Python 3.12+ и `uv` (или pip).
```bash
# MCP Cloud.ru
cd meeting-assistant/mcp-cloudru && uv run python -m src.server   # PORT=8000

# MCP Google Calendar
cd ../mcp-google-calendar && uv run python -m src.server          # PORT=8001

# MCP FollowUp
cd ../mcp-followup && uv run python -m src.server                 # PORT=8000 (поменяйте при конфликте)

# Агент
cd ../agent && uv run python -m src.start_a2a                     # PORT=10000

# Telegram-бот
cd ../telegram-bot && uv run python main.py

# Demo App
cd ../demo-app && pip install -r requirements.txt && python app.py  # порт 5000
```

### Docker (локально)
- Агент: `cd meeting-assistant/agent && docker buildx build --platform linux/amd64 -t meeting-assistant-agent:local .`
- MCP Cloud.ru: `cd meeting-assistant/mcp-cloudru && docker buildx build --platform linux/amd64 -t mcp-cloudru:local .`
Аналогично для остальных MCP/бота. Перед `docker run` пробросьте `.env`.

### Деплой на Cloud.ru
1) `docker login meeting-assistant.cr.cloud.ru -u <key_id> -p <key_secret>`
2) Теги и пуш (пример агента):  
   `docker tag meeting-assistant-agent:local meeting-assistant.cr.cloud.ru/meeting-assistant-agent:latest`  
   `docker push meeting-assistant.cr.cloud.ru/meeting-assistant-agent:latest`
3) MCP Cloud.ru аналогично (`mcp-cloudru:latest`).
4) В платформе A2A укажите образ агента и переменные окружения.
5) В MCP Cloud.ru настройте переменные для S3/RAG.

#### Деплой остальных MCP на Cloud.ru (аналогично)
1) Соберите и запушьте образы (пример для Google Calendar):
   ```bash
   cd meeting-assistant/mcp-google-calendar
   docker buildx build --platform linux/amd64 -t meeting-assistant.cr.cloud.ru/mcp-google-calendar:latest --push .
   ```
   Для FollowUp:
   ```bash
   cd meeting-assistant/mcp-followup
   docker buildx build --platform linux/amd64 -t meeting-assistant.cr.cloud.ru/mcp-followup:latest --push .
   ```
2) В консоли Cloud.ru для каждого MCP-сервера выберите загруженный образ и пропишите env:
   - **MCP Cloud.ru**: `CLOUD_TENANT_ID`, `CLOUD_KEY_ID`, `CLOUD_SECRET`, `S3_BUCKET`, `S3_ENDPOINT`, `S3_REGION`, `RAG_PUBLIC_URL`, `RAG_VERSION_ID`, `RAG_INDEXING_KEY_ID/SECRET`, `RAG_ID`, `PROJECT_ID`, `PRODUCT_INSTANCE_ID`, `S3_BUCKET_ID`, `PORT` (если нужно).
   - **MCP Google Calendar**: `GOOGLE_*` (service account), `GOOGLE_CALENDAR_ID`, `GOOGLE_OAUTH_CLIENT_ID/SECRET`, `PORT` (по умолчанию 8001).
   - **MCP FollowUp**: `FOLLOWUP_EMAIL/PASSWORD` или `FOLLOWUP_API_KEY`, `FOLLOWUP_API_URL`, `CLOUD_RAG_S3_*`, `PORT`.
3) После старта MCP укажите их URL в переменных агента: `FOLLOWUP_MCP_URL`, `GCALENDAR_MCP_URL`, `MANAGED_RAG_MCP_URL`.

### RAG поток (MCP Cloud.ru)
1) Залить файлы в S3 (через инструмент `s3_upload_text` или вне MCP).
2) `rag_start_indexing` — запускает индексацию.
3) `rag_get_versions` — список версий (из S3 ArtifactsManagedRAG).
4) `rag_update_version` — переключает клиента на последнюю READY версию.
5) `rag_search` / `rag_search_advanced` — поиск по базе знаний.

### Google Calendar MCP
Инструменты: `create_calendar_event`, `get_events_for_date`, `get_upcoming_events`, `get_current_time_moscow`. Требуется настроенный сервисный аккаунт + OAuth для приглашения гостей/Meet.

### FollowUp MCP
Позволяет писать/транскрибировать созвоны и синхронизировать в RAG S3. Настройте `FOLLOWUP_EMAIL/PASSWORD` или `FOLLOWUP_API_KEY`.

### Telegram-бот
Использует `AGENT_API_URL` для проксирования запросов в агента. Запустите после поднятия агента.
- Локальный запуск:  
  ```bash
  cd meeting-assistant/telegram-bot
  uv run python main.py
  ```
- `AGENT_API_URL` у бота должен указывать на ваш публичный A2A endpoint агента (тот же URL используйте в demo-app, чтобы тестировать одно и то же подключение).

### Demo App
Flask-приложение, отправляет A2A-запросы в агента, показывает запрос/ответ. Укажите свой `BASE_URL` и креды IAM.
- Запуск локально:  
  ```bash
  cd meeting-assistant/demo-app
  pip install -r requirements.txt
  python app.py  # порт 5000
  ```
  В `app.py` задайте `BASE_URL` (A2A endpoint агента) и IAM креды (лучше вынести в env).

### Полезные скрипты и тесты
- `agent/scripts/test_cloudru_api.py` — проверка Cloud.ru LLM (убирает `hosted_vllm/` префикс автоматически).
- `apis_tests/` — примеры вызовов MCP (S3/RAG и др.).
- `demo-app/` — интерактивная проверка A2A.

### Архитектура (упрощённо)
- A2A агент (LangChain) ⇄ MCP Cloud.ru (S3/RAG) ⇄ Cloud.ru сервисы  
                         ⇄ MCP Google Calendar ⇄ Google APIs  
                         ⇄ MCP FollowUp ⇄ FollowUp API  
                         ⇄ Telegram Bot (клиент)  
                         ⇄ Demo App (клиент)

