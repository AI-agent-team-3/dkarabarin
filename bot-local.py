"""
Локальная RAG система для работы с PDF-документами по термодинамике
Работает напрямую с Ollama, без Telegram
"""

import os
import sys
import logging
import warnings
from pathlib import Path
from typing import Optional
import time

from dotenv import load_dotenv

# LangChain для Ollama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Tavily для веб-поиска
from tavily import TavilyClient

# Наш RAG модуль
from rag import ThermodynamicsKnowledgeBase

# Отключаем предупреждения
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================================
# Конфигурация
# ============================================================================

BOOKS_DIR = Path("./books")

# Ollama (локальная модель)
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Параметры RAG
K_RETRIEVAL = 5
MAX_HISTORY = 10

# Системный промпт
SYSTEM_PROMPT = """Ты — преподаватель по технической термодинамике. Твоя задача — помогать студентам с выполнением лабораторных работ, обработкой значений, подготовкой к экзамену и ответами на вопросы.

ПРИОРИТЕТ ИСТОЧНИКОВ:
1. В ПЕРВУЮ ОЧЕРЕДЬ используй материал из PDF-документов в папке books/
2. Если информации недостаточно — используй Tavily веб-поиск
3. Не придумывай факты. Если ответа нет — честно скажи об этом

Твои обязанности:
1. Консультировать по выполнению лабораторных работ
2. Помогать с обработкой экспериментальных значений
3. Объяснять теоретический материал для экзамена
4. Отвечать на вопросы по термодинамике

Отвечай на языке вопроса. Будь строгим, но вежливым.
"""


# ============================================================================
# Веб-поиск через Tavily
# ============================================================================

class TavilySearch:
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key) if api_key else None
        self._available = self.client is not None

    def search(self, query: str, max_results: int = 3) -> Optional[str]:
        if not self._available:
            return None
        try:
            response = self.client.search(
                query, search_depth="basic",
                include_answer=False, max_results=max_results,
            )
            results = response.get("results", [])
            if not results:
                return "По вашему запросу ничего не найдено."
            formatted = []
            for r in results[:max_results]:
                title = r.get("title", "Без названия")
                content = r.get("content", "")
                url = r.get("url", "")
                score = r.get("score", 0)
                formatted.append(
                    f"📄 **{title}** (релевантность: {score:.2f})\n"
                    f"{content[:500]}\n🔗 {url}"
                )
            return "\n\n---\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Ошибка Tavily: {e}")
            return None

    def is_available(self) -> bool:
        return self._available


# ============================================================================
# Инициализация
# ============================================================================

# LLM (локальный через Ollama)
llm = ChatOpenAI(
    openai_api_key="fake_key",
    openai_api_base=OLLAMA_BASE,
    model_name=OLLAMA_MODEL,
    temperature=0.7,
    max_tokens=1024,
)

# Tavily
tavily = TavilySearch(TAVILY_API_KEY)

# База знаний
knowledge_base = ThermodynamicsKnowledgeBase(BOOKS_DIR)
knowledge_base.load()


# ============================================================================
# Основные функции
# ============================================================================

def answer_from_pdf(question: str) -> Optional[str]:
    """Отвечает на вопрос из PDF-документов."""
    if not knowledge_base.vectorstore:
        return None
    
    context_chunks = knowledge_base.get_relevant_chunks(question, k=K_RETRIEVAL)
    if not context_chunks:
        return None
    
    context = "\n\n---\n\n".join(context_chunks)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        SystemMessage(content=f"\n\n--- ИЗ PDF-ДОКУМЕНТОВ ---\n{context}"),
        HumanMessage(content=question),
    ]
    
    try:
        response = llm.invoke(messages)
        answer = response.content
        
        # Добавляем источники
        sources = []
        for chunk in context_chunks[:3]:
            if len(chunk) > 50:
                sources.append(chunk[:50].replace("\n", " ") + "...")
        if sources:
            answer += f"\n\n📚 Источники:\n" + "\n".join([f"  • {s}" for s in sources])
        
        return answer
    except Exception as e:
        logger.error(f"Ошибка RAG: {e}")
        return None


def answer_from_web(question: str) -> Optional[str]:
    """Отвечает на вопрос через веб-поиск."""
    if not tavily.is_available():
        return None
    
    search_results = tavily.search(question, max_results=3)
    if not search_results:
        return None
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        SystemMessage(content=f"\n\n--- ВЕБ-ПОИСК (Tavily) ---\n{search_results}"),
        HumanMessage(content=question),
    ]
    
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        logger.error(f"Ошибка веб-ответа: {e}")
        return None


def answer_direct(question: str) -> str:
    """Отвечает без контекста (только LLM)."""
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
    response = llm.invoke(messages)
    return response.content


def get_answer(question: str) -> tuple[str, str]:
    """Получает ответ с указанием источника."""
    print("  🔍 Поиск в PDF...")
    answer = answer_from_pdf(question)
    if answer:
        return answer, "📚 PDF"
    
    print("  🌐 Поиск в интернете (Tavily)...")
    answer = answer_from_web(question)
    if answer:
        return answer, "🌐 Интернет"
    
    print("  🤖 Использование LLM...")
    answer = answer_direct(question)
    return answer, "🤖 LLM"


def check_ollama():
    """Проверяет доступность Ollama."""
    try:
        import requests
        response = requests.get(f"{OLLAMA_BASE}/models", timeout=5)
        return response.status_code == 200
    except:
        return False


# ============================================================================
# Консольный интерфейс
# ============================================================================

def clear_screen():
    """Очищает экран."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Выводит заголовок."""
    print("="*70)
    print("🔥  ЛОКАЛЬНЫЙ КОНСУЛЬТАНТ ПО ТЕРМОДИНАМИКЕ  🔥")
    print("="*70)
    
    stats = knowledge_base.get_stats()
    if stats.get("loaded"):
        print(f"📚 База знаний: {stats.get('vectors', 0)} векторов из {stats.get('total_pages', 0)} страниц")
    else:
        print("📚 База знаний: не загружена (добавьте PDF в папку books/)")
    
    print(f"🤖 Модель: {OLLAMA_MODEL}")
    print(f"🌐 Веб-поиск: {'✅ доступен' if tavily.is_available() else '❌ недоступен'}")
    print("="*70)
    print()
    print("💡 Введите вопрос по термодинамике или команду:")
    print("   /clear  - очистить историю")
    print("   /stats  - статистика")
    print("   /ollama - статус Ollama")
    print("   /quit   - выход")
    print()


def print_stats():
    """Выводит статистику."""
    stats = knowledge_base.get_stats()
    print("\n" + "="*70)
    print("📊 СТАТИСТИКА")
    print("="*70)
    print(f"База знаний: {'✅ загружена' if stats.get('loaded') else '❌ не загружена'}")
    print(f"Векторов: {stats.get('vectors', 0)}")
    print(f"Страниц: {stats.get('total_pages', 0)}")
    print(f"Чанков: {stats.get('total_chunks', 0)}")
    print(f"Модель эмбеддингов: {stats.get('embedding_model', 'N/A')}")
    print(f"Веб-поиск: {'✅ доступен' if tavily.is_available() else '❌ недоступен'}")
    print(f"Ollama: {'✅ доступен' if check_ollama() else '❌ недоступен'}")
    print("="*70)


def print_ollama_status():
    """Выводит статус Ollama."""
    print("\n" + "="*70)
    print("🤖 СТАТУС OLLAMA")
    print("="*70)
    
    if check_ollama():
        print(f"✅ Ollama доступен")
        print(f"   Модель: {OLLAMA_MODEL}")
        print(f"   URL: {OLLAMA_BASE}")
        print()
        print("Управление моделями:")
        print("  ollama list          - список моделей")
        print(f"  ollama pull {OLLAMA_MODEL} - загрузка модели")
        print("  ollama serve         - запуск сервера")
    else:
        print("❌ Ollama не доступен!")
        print()
        print("Для установки Ollama:")
        print("  1. Скачайте с https://ollama.ai/")
        print("  2. Запустите: ollama serve")
        print(f"  3. Загрузите модель: ollama pull {OLLAMA_MODEL}")
    print("="*70)


# ============================================================================
# Главный цикл
# ============================================================================

def main():
    """Главная функция."""
    clear_screen()
    print_header()
    
    # Проверка Ollama
    if not check_ollama():
        print("⚠️  ВНИМАНИЕ: Ollama не доступен!")
        print("   Бот будет работать, но локальная LLM недоступна.")
        print("   Запустите 'ollama serve' в отдельном окне.")
        print("="*70)
        print()
    
    history = []
    
    while True:
        try:
            # Ввод вопроса
            user_input = input("❓ Ваш вопрос: ").strip()
            
            if not user_input:
                continue
            
            # Обработка команд
            if user_input.lower() == '/quit':
                print("\n👋 До свидания!")
                break
            elif user_input.lower() == '/clear':
                history = []
                print("🧹 История очищена!\n")
                continue
            elif user_input.lower() == '/stats':
                print_stats()
                print()
                continue
            elif user_input.lower() == '/ollama':
                print_ollama_status()
                print()
                continue
            elif user_input.lower() == '/help':
                print_header()
                continue
            
            # Получение ответа
            print("\n⏳ Думаю...")
            start_time = time.time()
            
            answer, source = get_answer(user_input)
            
            elapsed = time.time() - start_time
            
            # Вывод ответа
            print("\n" + "="*70)
            print(f"{source} ОТВЕТ:")
            print("="*70)
            print(answer)
            print("="*70)
            print(f"⏱️  Время: {elapsed:.1f} сек")
            print()
            
            # Сохранение в историю
            history.append((user_input, answer))
            if len(history) > MAX_HISTORY:
                history.pop(0)
            
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            print()


# ============================================================================
# Запуск
# ============================================================================

if __name__ == "__main__":
    main()