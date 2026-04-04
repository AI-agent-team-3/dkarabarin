## 🚀 Быстрый старт

### 1. Установка Python 3.11+

### 2. Установка Ollama
```bash
# Загрузите модель
ollama pull qwen3:4b
3. Получение API ключей
Tavily API (веб-поиск):
Зарегистрируйтесь на app.tavily.com

Получите бесплатный API ключ (1000 запросов/мес)

Langfuse (опционально, для наблюдаемости):
Запустите локально через Docker или используйте cloud.langfuse.com

4. Клонирование и установка
bash
git clone <repository-url>
cd thermodynamics-rag
python -m venv venv

# Активация виртуальной среды:
# Windows
venv\Scripts\activate.bat
# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt
5. Настройка окружения
bash
cp .env.example .env
# Отредактируйте .env и вставьте ваши ключи API
6. Подготовка базы знаний
bash
mkdir books
# Поместите PDF-файлы по термодинамике в папку books/
7. Запуск Langfuse (опционально)
bash
docker compose up -d
8. Запуск ассистента
Консольная версия:
bash
python bot-local.py
Веб-версия (новая!):
bash
python -m uvicorn web.api:app --reload --host 0.0.0.0 --port 8000
Затем откройте в браузере: http://localhost:8000
