# 🔥 Thermodynamics RAG Assistant

Локальный ИИ-ассистент для изучения технической термодинамики с поддержкой RAG (Retrieval-Augmented Generation), веб-поиска через Tavily и полной наблюдаемостью через Langfuse.

## 📚 Особенности

- **RAG на PDF-документах** — загружайте учебники и методички в папку `books/`
- **Локальная LLM через Ollama** — бесплатно, без интернета
- **Веб-поиск через Tavily** — актуальная информация из интернета
- **Полная наблюдаемость через Langfuse** — трассировка всех запросов
- **Гибридный поиск** — сначала PDF, затем веб-поиск, затем LLM
- **Консольный интерфейс** — удобная работа без Telegram

## 🚀 Быстрый старт

### 1. Установка Python 3.11

**Windows:**
- Скачайте Python 3.11 с [python.org](https://www.python.org/downloads/release/python-3110/)
- При установке поставьте галочку "Add Python to PATH"

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.11 python3.11-venv

# Mac
brew install python@3.11
