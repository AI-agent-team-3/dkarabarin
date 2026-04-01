# 🔥 Thermodynamics RAG Assistant

Локальный ИИ-ассистент для изучения технической термодинамики с поддержкой RAG (Retrieval-Augmented Generation), веб-поиска через Tavily и полной наблюдаемостью через Langfuse.

---

## 📚 Особенности
- **RAG на PDF-документах** — загружайте учебники и методички в папку `books/`.
- **Локальная LLM через Ollama** — бесплатно, без интернета.
- **Веб-поиск через Tavily** — актуальная информация из интернета.
- **Полная наблюдаемость через Langfuse** — трассировка всех запросов.
- **Гибридный поиск** — сначала PDF, затем веб, затем LLM.
- **Консольный интерфейс** — удобная работа без Telegram.

---

## 🚀 Быстрый старт

### 1. Установка Python 3.11
- **Windows:**
  - Скачайте с [python.org](https://python.org)
  - При установке поставьте галочку "Add Python to PATH"
- **Linux / Mac:**
  - Ubuntu/Debian:  
    ```bash
    sudo apt update && sudo apt install python3.11 python3.11-venv
    ```
  - Mac:  
    ```bash
    brew install python@3.11
    ```

### 2. Установка Ollama
- **Windows:**  
  Скачайте с [ollama.ai/download/windows](https://ollama.ai/download/windows), установите и запустите.
- **Linux / Mac:**  
  ```bash
  curl -fsSL https://ollama.ai/install.sh | sh
  ollama pull qwen3:4b
### 3. Получение API ключей
- **Tavily API (веб-поиск):**  
  - Зарегистрируйтесь на [app.tavily.com](https://app.tavily.com)  
  - Получите бесплатный API-ключ (1000 запросов/месяц).
- **Langfuse (опционально, для наблюдаемости):**  
  - Запустите локально через Docker или используйте [cloud.langfuse.com](https://cloud.langfuse.com).
### 4. Клонирование и установка
```bash
git clone https://github.com/yourusername/thermodynamics-rag.git
cd thermodynamics-rag
python -m venv venv
# Активируйте виртуальное окружение:
# Linux/Mac: venv/bin/activate
# Windows: venv\Scripts\activate.bat
pip install -r requirements.txt
