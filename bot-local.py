"""
Локальная RAG система для работы с PDF-документами по термодинамике
С интеграцией Langfuse для мониторинга и трассировки
"""

import os
import sys
import logging
import warnings
from pathlib import Path
from typing import Optional
import time
from datetime import datetime

from dotenv import load_dotenv

# LangChain для Ollama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Tavily для веб-поиска
from tavily import TavilyClient

# Langfuse для наблюдаемости
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

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

# Langfuse
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_ENABLED = False

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
# Инициализация Langfuse
# ============================================================================

langfuse = None
if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    try:
        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        # Проверка подключения
        langfuse.auth_check()
        LANGFUSE_ENABLED = True
        print("✅ Langfuse инициализирован")
        print(f"   URL: {LANGFUSE_HOST}")
    except Exception as e:
        print(f"⚠️ Langfuse не инициализирован: {e}")
        print("   Продолжаем работу без трассировки")
else:
    print("⚠️ Langfuse отключен (нет ключей в .env)")


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
# Функции с трассировкой Langfuse
# ============================================================================

@observe()
def answer_from_pdf(question: str, trace_id: str = None) -> Optional[str]:
    """Отвечает на вопрос из PDF-документов с трассировкой."""
    if not knowledge_base.vectorstore:
        return None
    
    # Обновляем метаданные трассировки
    if LANGFUSE_ENABLED:
        langfuse_context.update_current_observation(
            metadata={"source": "pdf", "k_retrieval": K_RETRIEVAL}
        )
    
    context_chunks = knowledge_base.get_relevant_chunks(question, k=K_RETRIEVAL)
    if not context_chunks:
        return None
    
    # Сохраняем найденные чанки в трассировку
    if LANGFUSE_ENABLED:
        langfuse_context.update_current_observation(
            metadata={
                "chunks_found": len(context_chunks),
                "chunks_preview": [c[:200] for c in context_chunks[:3]]
            }
        )
    
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
        
        # Сохраняем метрики
        if LANGFUSE_ENABLED:
            langfuse_context.update_current_observation(
                output=answer,
                metadata={"answer_length": len(answer), "sources_count": len(sources)}
            )
        
        return answer
    except Exception as e:
        logger.error(f"Ошибка RAG: {e}")
        if LANGFUSE_ENABLED:
            langfuse_context.update_current_observation(
                level="ERROR",
                status_message=str(e)
            )
        return None


@observe()
def answer_from_web(question: str, trace_id: str = None) -> Optional[str]:
    """Отвечает на вопрос через веб-поиск с трассировкой."""
    if not tavily.is_available():
        return None
    
    if LANGFUSE_ENABLED:
        langfuse_context.update_current_observation(
            metadata={"source": "web", "search_engine": "tavily"}
        )
    
    search_results = tavily.search(question, max_results=3)
    if not search_results:
        return None
    
    if LANGFUSE_ENABLED:
        langfuse_context.update_current_observation(
            metadata={"search_results_length": len(search_results)}
        )
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        SystemMessage(content=f"\n\n--- ВЕБ-ПОИСК (Tavily) ---\n{search_results}"),
        HumanMessage(content=question),
    ]
    
    try:
        response = llm.invoke(messages)
        answer = response.content
        
        if LANGFUSE_ENABLED:
            langfuse_context.update_current_observation(
                output=answer,
                metadata={"answer_length": len(answer)}
            )
        
        return answer
    except Exception as e:
        logger.error(f"Ошибка веб-ответа: {e}")
        if LANGFUSE_ENABLED:
            langfuse_context.update_current_observation(
                level="ERROR",
                status_message=str(e)
            )
        return None


@observe()
def answer_direct(question: str, trace_id: str = None) -> str:
    """Отвечает без контекста (только LLM) с трассировкой."""
    if LANGFUSE_ENABLED:
        langfuse_context.update_current_observation(
            metadata={"source": "llm_only", "model": OLLAMA_MODEL}
        )
    
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
    
    try:
        response = llm.invoke(messages)
        answer = response.content
        
        if LANGFUSE_ENABLED:
            langfuse_context.update_current_observation(
                output=answer,
                metadata={"answer_length": len(answer)}
            )
        
        return answer
    except Exception as e:
        logger.error(f"Ошибка LLM: {e}")
        if LANGFUSE_ENABLED:
            langfuse_context.update_current_observation(
                level="ERROR",
                status_message=str(e)
            )
        return f"Ошибка: {e}"


@observe()
def get_answer(question: str, session_id: str = None) -> tuple[str, str]:
    """
    Получает ответ с указанием источника.
    Вся функция трассируется как единый span.
    """
    if LANGFUSE_ENABLED:
        langfuse_context.update_current_trace(
            name="question_answer",
            user_id="local_user",
            session_id=session_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
            tags=["thermodynamics", "local_rag"],
            metadata={"question": question, "model": OLLAMA_MODEL}
        )
    
    # Пробуем PDF
    print("  🔍 Поиск в PDF...")
    answer = answer_from_pdf(question)
    if answer:
        if LANGFUSE_ENABLED:
            langfuse_context.score_current_trace(
                name="source",
                value=1.0,
                comment="Ответ найден в PDF"
            )
        return answer, "📚 PDF"
    
    # Пробуем веб-поиск
    print("  🌐 Поиск в интернете (Tavily)...")
    answer = answer_from_web(question)
    if answer:
        if LANGFUSE_ENABLED:
            langfuse_context.score_current_trace(
                name="source",
                value=0.7,
                comment="Ответ найден через веб-поиск"
            )
        return answer, "🌐 Интернет"
    
    # Используем LLM
    print("  🤖 Использование LLM...")
    answer = answer_direct(question)
    if LANGFUSE_ENABLED:
        langfuse_context.score_current_trace(
            name="source",
            value=0.3,
            comment="Ответ из LLM (нет в базе знаний)"
        )
    return answer, "🤖 LLM"


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
    print(f"📊 Langfuse: {'✅ активен' if LANGFUSE_ENABLED else '❌ неактивен'}")
    print("="*70)
    print()
    print("💡 Введите вопрос по термодинамике или команду:")
    print("   /clear  - очистить историю")
    print("   /stats  - статистика")
    print("   /ollama - статус Ollama")
    print("   /langfuse - статус Langfuse")
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
    print(f"Langfuse: {'✅ активен' if LANGFUSE_ENABLED else '❌ неактивен'}")
    if LANGFUSE_ENABLED:
        print(f"Langfuse URL: {LANGFUSE_HOST}")
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


def print_langfuse_status():
    """Выводит статус Langfuse."""
    print("\n" + "="*70)
    print("📊 СТАТУС LANGFUSE")
    print("="*70)
    
    if LANGFUSE_ENABLED:
        print("✅ Langfuse активен")
        print(f"   URL: {LANGFUSE_HOST}")
        print()
        print("Для просмотра трассировок:")
        print(f"  Откройте: {LANGFUSE_HOST}")
        print("  Перейдите в раздел Traces")
        print()
        print("Что трассируется:")
        print("  • Каждый вопрос пользователя")
        print("  • Источник ответа (PDF/Web/LLM)")
        print("  • Время выполнения")
        print("  • Количество найденных чанков")
        print("  • Длина ответа")
        print("  • Ошибки (если есть)")
    else:
        print("❌ Langfuse не активен")
        print()
        print("Для активации добавьте в .env:")
        print("  LANGFUSE_PUBLIC_KEY=pk-...")
        print("  LANGFUSE_SECRET_KEY=sk-...")
        print("  LANGFUSE_HOST=http://localhost:3000")
        print()
        print("Запустите Langfuse:")
        print("  docker compose up -d")
    print("="*70)


def check_ollama():
    """Проверяет доступность Ollama."""
    try:
        import requests
        response = requests.get(f"{OLLAMA_BASE}/models", timeout=5)
        return response.status_code == 200
    except:
        return False


def flush_langfuse():
    """Отправляет все данные в Langfuse."""
    if LANGFUSE_ENABLED and langfuse:
        langfuse.flush()
        print("✅ Данные отправлены в Langfuse")


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
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    history = []
    
    while True:
        try:
            # Ввод вопроса
            user_input = input("❓ Ваш вопрос: ").strip()
            
            if not user_input:
                continue
            
            # Обработка команд
            if user_input.lower() == '/quit':
                flush_langfuse()
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
            elif user_input.lower() == '/langfuse':
                print_langfuse_status()
                print()
                continue
            elif user_input.lower() == '/help':
                print_header()
                continue
            
            # Получение ответа с трассировкой
            print("\n⏳ Думаю...")
            start_time = time.time()
            
            answer, source = get_answer(user_input, session_id)
            
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
            
            # Периодическая отправка в Langfuse
            if LANGFUSE_ENABLED and len(history) % 5 == 0:
                flush_langfuse()
            
        except KeyboardInterrupt:
            flush_langfuse()
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            if LANGFUSE_ENABLED:
                try:
                    trace = langfuse.trace(name="error", metadata={"error": str(e)})
                    trace.event(name="exception", metadata={"error": str(e)})
                    langfuse.flush()
                except:
                    pass


# ============================================================================
# Запуск
# ============================================================================

if __name__ == "__main__":
    main()