# Интерактивный учебник по Langfuse

Практический курс по наблюдаемости (observability) LLM-приложений с фокусом на AI Safety и LLMSecOps.

Часть серии для обучения LLM-инженеров. Предполагает знакомство с RAG и ИИ-агентами (см. `common_ai_agents`).

> Этот учебный проект зафиксирован на стеке **Langfuse 2.x + локальный Docker Compose**.
> Если вы сверяетесь с актуальной документацией Langfuse 3.x/4.x, архитектура self-hosted может отличаться.

## Что вы изучите

- Трассировка LLM-вызовов с помощью Langfuse
- Декоратор `@observe()`, Spans, Generations, Events
- Интеграция с OpenRouter и LangChain
- Управление промптами (версионирование, A/B-тесты)
- Оценка и скоринг качества LLM
- Датасеты и эксперименты
- Трассировка ИИ-агента с RAG и Web-search
- LLMSecOps: мониторинг безопасности, PII-фильтрация, детекция prompt injection

## Быстрый старт

### 1. Поднять локальный Langfuse

```bash
docker compose up -d
```

Откройте http://localhost:3000, создайте аккаунт и проект. Скопируйте ключи API.

### 2. Настроить окружение

```bash
# Рекомендуемая версия Python: 3.10-3.12
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Настроить API-ключи

```bash
cp .env.example .env
# Заполните .env своими ключами
# При необходимости зафиксируйте модель:
# OPENROUTER_MODEL=openai/gpt-oss-20b:free
# OPENROUTER_AGENT_MODEL=openrouter/free
```

### 4. Запустить ноутбук

```bash
jupyter notebook langfuse_notebook.ipynb
```

## Необходимые API-ключи

| Ключ | Где получить | Обязательно |
|------|-------------|-------------|
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys | Да |
| `LANGFUSE_PUBLIC_KEY` | Локальный Langfuse → Settings → API Keys | Да |
| `LANGFUSE_SECRET_KEY` | Локальный Langfuse → Settings → API Keys | Да |

## Системные требования

- Python 3.10-3.12
- Docker и Docker Compose (для локального Langfuse)
- 4-8 GB RAM
- Доступ в интернет (для OpenRouter API, Hugging Face и веб-поиска)

## Preflight checklist

- `docker compose up -d` завершился успешно, а Langfuse доступен на `http://localhost:3000`
- В `.env` заполнены `OPENROUTER_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
- При первом запуске раздела 8 будет скачана embedding-модель `sentence-transformers/all-MiniLM-L6-v2`
- Если нужен полностью воспроизводимый запуск, задайте `OPENROUTER_MODEL` и `OPENROUTER_AGENT_MODEL` явно

## Структура проекта

```
├── langfuse_notebook.ipynb   # Основной учебник
├── docker-compose.yml        # Локальный Langfuse
├── requirements.txt          # Зависимости Python
├── data/                     # Учебные документы для RAG
```

## Лицензия

MIT
