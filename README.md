```markdown
# 🔥 Thermodynamics RAG Assistant

## Основные возможности
- RAG на PDF-учебниках
- Локальная LLM через Ollama
- Веб-поиск через Tavily
- Трассировка через Langfuse
- Гибридный поиск: PDF → интернет → LLM
- Консольный интерфейс

## Быстрый старт
1. Установите Python 3.11  
2. Установите Ollama, скачав или через команду: `curl -fsSL https://ollama.ai/install.sh | sh`  
3. Загрузите модель: `ollama pull qwen3:4b`  
4. Получите API ключи Tavily и Langfuse  
5. Клонируйте проект:  
```bash
git clone https://github.com/yourusername/thermodynamics-rag.git
cd thermodynamics-rag
python -m venv venv
```
6. Активируйте виртуальное окружение и установите зависимости:  
```bash
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate.bat # Windows
pip install -r requirements.txt
```
7. Настройте `.env`, добавьте API-ключи  
8. Добавьте PDF-файлы в папку `books/`  
9. При необходимости запустите Langfuse: `docker compose up -d`  
10. Запустите ассистента: `python local_rag.py`

---

**Следующий вопрос:**
```# 🔥 Thermodynamics RAG Assistant

# Локальный ИИ-ассистент для изучения технической термодинамики с поддержкой RAG (Retrieval-Augmented Generation).


# 📚 Основные возможности
• RAG на PDF-документах: загружайте учебники и методички в папку `books/`.
• Локальная LLM через Ollama: запуск без интернета, бесплатно.
• Веб-поиск через Tavily: получает актуальную информацию из интернета.
• Полная наблюдаемость через Langfuse: трассировка всех запросов.
• Гибридный поиск: сначала ищет в PDF, затем — в интернете, затем — в LLM.
• Консольный интерфейс: удобно и без Telegram.


# 🚀 Быстрый старт

## 1. Установка Python 3.11

## 2. Установка Ollama
Windows:  
• Скачайте с ollama.ai/download/windows  
• Установите и запустите.

Linux/Mac:
curl -fsSL https://ollama.ai/install.sh | sh

Загрузите модель:
ollama pull qwen3:4b


## 3. Получение API ключей
• Tavily API: зарегистрируйтесь на app.tavily.com, получите бесплатный API-ключ (1000 запросов/мес).
• Langfuse: запустите локально через Docker или используйте cloud.langfuse.com.

## 4. Установка проекта
git clone https://github.com/yourusername/thermodynamics-rag.git
cd thermodynamics-rag
python -m venv venv

Linux/Mac:
source venv/bin/activate

Windows:
venv\Scripts\activate.bat
pip install -r requirements.txt


## 5. Настройка окружения
cp .env.example .env
Отредактируйте .env, добавьте API-ключи


## 6. Подготовка базы знаний
mkdir books
добавьте PDF-файлы по термодинамике в папку books/

## 7. Запуск Langfuse (опционально)
docker compose up -d

## 8. Запуск ассистента
python local_rag.py

# 📖 Использование
Запросы вводите в консоль — ассистент ищет ответы по PDF, интернету и модели.

# 🔥 ЛОКАЛЬНЫЙ КОНСУЛЬТАНТ ПО ТЕРМОДИНАМИКЕ 🔥
### ======================================================================
### 📚 База знаний: 487 векторов из 195 страниц
### 🤖 Модель: qwen3:4b
### 🌐 Веб-поиск: ✅ доступен
### 📊 Langfuse: ✅ активен
======================================================================
### 💡 Введите вопрос по термодинамике или команду:
### /clear - очистить историю
### /stats - статистика
### /ollama - статус Ollama
### /langfuse - статус Langfuse
### /quit  - выход
### ❓ Ваш вопрос: Что такое энтропия?
### ⏳ Думаю...
###  🔍 Поиск в PDF...
======================================================================
### 📚 PDF ОТВЕТ:
======================================================================
### Энтропия — это мера беспорядка или хаоса в термодинамической системе. 
### Согласно второму закону термодинамики, энтропия изолированной системы 
### не может уменьшаться, она может только возрастать или оставаться 
### постоянной в обратимых процессах.
### Формула: dS = δQ/T, где:
### • dS — изменение энтропии
### • δQ — количество теплоты
### • T — абсолютная температура
### 📚 Источники:
  ### Энтропия — это мера беспорядка в системе...
  ### Второй закон термодинамики: энтропия изолированной системы...
======================================================================
### ⏱️  Время: 2.3 сек
# 📁 Структура проекта

### thermodynamics-rag/
### ├── books/                      # Папка с PDF-файлами
### ├── local_rag.py                # Основной консольный ассистент
### ├── rag.py                      # RAG модуль (эмбеддинги, поиск)
### ├── requirements.txt            # Зависимости
### ├── .env.example                # Пример переменных окружения
### ├── docker-compose.yml          # Для Langfuse
### └── README.md                   # Документация
# 🔧 Конфигурация
.env файл
  
### Ollama (локальная модель)
OLLAMA_BASE=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:4b

### Tavily API (веб-поиск)
TAVILY_API_KEY=tvly-...

### Langfuse (опционально)
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3000

### Модель эмбеддингов
EMBEDDING_MODEL=e5-base  # e5-base, bge-m3, minilm, rubert

## Параметры RAG в rag.py
### python
### CHUNK_SIZE = 800          # Размер чанка (символы)
### CHUNK_OVERLAP = 150       # Перекрытие между чанками
### K_RETRIEVAL = 5           # Количество документов для поиска
### EMBEDDING_MODEL = "BAAI/bge-m3"  # Модель эмбеддингов
# 📊 Модели эмбеддингов
| Модель | Размер | RAM | Качество | Рекомендация |
| --- | --- | --- | --- | --- |
| intfloat/multilingual-e5-base | 278M | 1.5GB | Отличное | Лучший выбор |
| BAAI/bge-m3 | 568M | 2.5GB | Максимальное | Для мощных ПК |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 118M | 500MB | Хорошее | Для слабых ПК |
| ai-forever/sbert_large_mt_nlu_ru | 560M | 2.2GB | Отличное | Для русского языка |

🐛 Устранение проблем
Ollama не доступен
bash
# Проверьте статус
ollama list

# Запустите сервер
ollama serve

# Загрузите модель
ollama pull qwen3:4b
Langfuse не подключается
bash
# Проверьте Docker
docker ps

# Запустите Langfuse
docker compose up -d

# Проверьте доступность
curl http://localhost:3000/api/health
Нет PDF файлов
bash
# Создайте папку
mkdir books

# Добавьте PDF-файлы
# Поддерживаются любые PDF с русским или английским текстом
Проблемы с памятью
Уменьшите параметры в rag.py:

python
CHUNK_SIZE = 500      # вместо 800
CHUNK_OVERLAP = 100   # вместо 150
K_RETRIEVAL = 3       # вместо 5
📊 Langfuse Dashboard
После запуска Langfuse, откройте http://localhost:3000 для просмотра:

Traces — все запросы с временем выполнения

Sessions — группировка запросов по сессиям

Scores — оценки качества ответов

Metrics — статистика использования

🛡️ Безопасность
Все данные хранятся локально

PDF-файлы не отправляются в облако

Веб-поиск только по вашему запросу

Langfuse можно запустить локально

📄 Лицензия
MIT License

🙏 Благодарности
LangChain — фреймворк для LLM

FAISS — векторный поиск

Ollama — локальный запуск LLM

Tavily — поиск для AI

Langfuse — наблюдаемость LLM

BAAI/bge-m3 — мультиязычные эмбеддинги

📝 TODO
Добавить поддержку большего количества LLM (Llama, Mistral)

Улучшить чанкование для технических текстов

Добавить кэширование эмбеддингов

Реализовать HyDE (Hypothetical Document Embeddings)

Добавить реранкинг через cross-encoder

Создать веб-интерфейс
