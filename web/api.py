"""
FastAPI-сервер для веб-интерфейса ИИ преподавателя по ТТД и ТМО
"""

from __future__ import annotations

import logging
import sys
import time
import re
import json
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from collections import defaultdict
from typing import Tuple, Dict, Optional

# Добавляем путь
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ВСТРОЕННАЯ СИСТЕМА БЕЗОПАСНОСТИ
# ============================================================================

class SecurityGuard:
    """Встроенная система безопасности"""
    
    def __init__(self):
        self.blocked_count = 0
        self.request_log = defaultdict(list)
    
    BLOCK_PATTERNS = [
        (r"(?i)(ignore|forget|disregard).*(instructions|rules|prompts?)", "prompt_injection"),
        (r"(?i)(system|admin).*(override|reset|ignore)", "prompt_injection"),
        (r"(?i)(reveal|show|print|display).*(system.*prompt)", "system_leak"),
        (r"(?i)(jailbreak|dan mode|aim mode)", "jailbreak"),
        (r"(?i)игнорируй.*инструкц", "prompt_injection"),
        (r"(?i)забудь.*предыдущ", "prompt_injection"),
        (r"(?i)системный промпт", "system_leak"),
        (r"(?i)покажи.*промпт", "system_leak"),
        (r"(?i)(готовые? ответы?|списать|сдуть)", "academic"),
        (r"(?i)(сделай за меня|напиши за меня)", "academic"),
        (r"(?i)(лабораторную за меня|курсовую за меня)", "academic"),
        (r"(?i)(ответы на экзамен)", "academic"),
        (r"(?i)как взломать", "dangerous"),
    ]
    
    PII_PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
        (r"\b\+?[78][\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b", "phone"),
        (r"\b\d{4}\s?\d{6}\b", "passport"),
        (r"\b\d{11}\b", "snils"),
    ]
    
    EDUCATIONAL_PATTERNS = [
        r"(?i)(термодинамик|тепломассообмен|энтропи|энтальпи)",
        r"(?i)(формула|расчет|вычисление|определение)",
        r"(?i)(лабораторн|практикум|эксперимент)",
        r"(?i)(закон|правило|принцип)",
        r"(?i)(первый закон|второй закон|третий закон)",
        r"(?i)(цикл карно|кпд|эффективность)",
        r"(?i)(идеальный газ|реальный газ)",
        r"(?i)(теплопроводность|конвекция|излучение)",
        r"(?i)(nusselt|reynolds|prandtl|fourier)",
    ]
    
    def check(self, message: str, session_id: str) -> Tuple[bool, str]:
        message_lower = message.lower()
        
        for pattern, category in self.BLOCK_PATTERNS:
            if re.search(pattern, message_lower):
                self.blocked_count += 1
                return False, self._get_message(category)
        
        for pattern, _ in self.PII_PATTERNS:
            if re.search(pattern, message):
                self.blocked_count += 1
                return False, "⚠️ Запрос содержит персональные данные. Пожалуйста, удалите их."
        
        now = time.time()
        requests = self.request_log[session_id]
        requests[:] = [t for t in requests if now - t < 60]
        if len(requests) >= 10:
            wait = 60 - (now - requests[0])
            return False, f"⏳ Слишком много запросов. Подождите {wait:.0f} секунд."
        requests.append(now)
        
        return True, ""
    
    def is_educational(self, message: str) -> bool:
        message_lower = message.lower()
        for pattern in self.EDUCATIONAL_PATTERNS:
            if re.search(pattern, message_lower):
                return True
        return False
    
    def clean_pii(self, text: str) -> str:
        for pattern, _ in self.PII_PATTERNS:
            text = re.sub(pattern, "[СКРЫТО]", text)
        return text
    
    def _get_message(self, category: str) -> str:
        messages = {
            "prompt_injection": "⛔ Запрос отклонен. Обнаружена попытка инъекции инструкций.",
            "system_leak": "🔒 Запрос отклонен. Системная информация не разглашается.",
            "jailbreak": "🚫 Запрос отклонен. Обнаружена попытка обхода безопасности.",
            "dangerous": "⚠️ Запрос отклонен. Вопрос нарушает политику безопасности.",
            "academic": "📚 Запрос отклонен. Я помогаю учиться, но не даю готовые ответы.",
        }
        return messages.get(category, "❌ Запрос отклонен.")

security = SecurityGuard()

# ============================================================================
# Загрузка бота
# ============================================================================

get_answer = None
web_search = None
knowledge_base = None
OLLAMA_MODEL = "qwen3:4b"

bot_local_path = ROOT_DIR / "bot-local.py"

if bot_local_path.exists():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bot_local", bot_local_path)
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)
        
        get_answer = getattr(bot_module, 'get_answer', None)
        web_search = getattr(bot_module, 'web_search', None)
        knowledge_base = getattr(bot_module, 'knowledge_base', None)
        OLLAMA_MODEL = getattr(bot_module, 'OLLAMA_MODEL', 'qwen3:4b')
        
        logger.info("✅ Загружен bot-local.py")
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")

if get_answer is None:
    def get_answer(question, session_id=None):
        return f"📚 **Вопрос:** {question}\n\n**Ответ:** Это тестовый режим. Для работы установите Ollama.", "⚠️ Тест"

# ============================================================================
# Модели
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    source: str
    processing_time: float

class ClearRequest(BaseModel):
    session_id: str

# ============================================================================
# Хранилище
# ============================================================================

class SessionStore:
    def __init__(self):
        self.sessions = {}
        self.history = {}
    
    def get_or_create(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = {"created": datetime.now(), "count": 0}
            self.history[session_id] = []
        return self.sessions[session_id]
    
    def add_message(self, session_id: str, role: str, content: str, source: str = None):
        if session_id not in self.history:
            self.history[session_id] = []
        self.history[session_id].append({
            "role": role, "content": content, "time": datetime.now().isoformat(), "source": source
        })
        if session_id in self.sessions:
            self.sessions[session_id]["count"] += 1
    
    def clear(self, session_id: str):
        if session_id in self.history:
            self.history[session_id] = []
        if session_id in self.sessions:
            self.sessions[session_id]["count"] = 0

store = SessionStore()

# ============================================================================
# FastAPI
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Запуск сервера")
    yield
    logger.info("👋 Остановка")

app = FastAPI(title="ИИ преподаватель по ТТД и ТМО", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API
# ============================================================================

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/api/stats")
def stats():
    kb_loaded = knowledge_base and hasattr(knowledge_base, '_loaded') and knowledge_base._loaded
    web_avail = web_search and hasattr(web_search, 'is_available') and web_search.is_available()
    
    return {
        "knowledge_base_loaded": kb_loaded,
        "web_search_available": web_avail,
        "web_search_engine": web_search.get_engine_name() if web_search else "Нет",
        "ollama_model": OLLAMA_MODEL,
        "ollama_available": True,
        "total_sessions": len(store.sessions)
    }

@app.post("/api/chat")
def chat(req: ChatRequest):
    logger.info(f"Запрос: {req.message[:50]}...")
    
    is_safe, error_msg = security.check(req.message, req.session_id)
    if not is_safe:
        logger.warning(f"Блокировка: {req.message[:50]}")
        return ChatResponse(
            reply=error_msg,
            session_id=req.session_id,
            source="🛡️ Безопасность",
            processing_time=0.0
        )
    
    if not security.is_educational(req.message) and len(req.message) > 10:
        return ChatResponse(
            reply="📚 Я специализируюсь на вопросах по **термодинамике (ТТД)** и **тепломассообмену (ТМО)**.\n\nПримеры вопросов:\n• Объясни первый закон термодинамики\n• Что такое число Нуссельта?\n• Как рассчитать КПД цикла Карно?",
            session_id=req.session_id,
            source="🎓 Совет",
            processing_time=0.0
        )
    
    clean_message = security.clean_pii(req.message)
    
    store.get_or_create(req.session_id)
    store.add_message(req.session_id, "user", clean_message)
    
    start = time.time()
    
    try:
        result = get_answer(clean_message, session_id=req.session_id)
        
        if isinstance(result, tuple):
            answer, source = result
        else:
            answer = result
            source = "🤖 Бот"
        
        answer = security.clean_pii(answer)
        elapsed = time.time() - start
        
        store.add_message(req.session_id, "assistant", answer, source)
        
        return ChatResponse(
            reply=answer,
            session_id=req.session_id,
            source=source,
            processing_time=elapsed
        )
    except Exception as e:
        logger.exception("Ошибка")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear")
def clear(req: ClearRequest):
    store.clear(req.session_id)
    return {"status": "ok"}

@app.get("/api/security/status")
def security_status():
    return {"blocked_count": security.blocked_count}

# ============================================================================
# HTML (исправленная версия с работающей кнопкой)
# ============================================================================

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ИИ преподаватель по ТТД и ТМО</title>
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\(', '\\)']],
                displayMath: [['$$', '$$'], ['\\[', '\\]']],
                processEscapes: true
            }
        };
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e); min-height: 100vh; padding: 20px; }
        .app { max-width: 1000px; margin: 0 auto; background: white; border-radius: 20px; overflow: hidden; display: flex; flex-direction: column; height: 90vh; }
        .header { background: linear-gradient(135deg, #1a1a2e, #0f3460); color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .header h1 { font-size: 1.2rem; display: flex; align-items: center; gap: 8px; }
        .badge { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; }
        .messages { flex: 1; overflow-y: auto; padding: 20px; background: #f0f2f5; display: flex; flex-direction: column; gap: 15px; }
        .message { display: flex; gap: 10px; animation: fadeIn 0.3s ease; }
        .message.user { justify-content: flex-end; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; flex-shrink: 0; }
        .message.user .avatar { background: #e94560; }
        .message.bot .avatar { background: #0f3460; }
        .bubble { max-width: 75%; padding: 12px 16px; border-radius: 18px; background: white; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .message.user .bubble { background: #e94560; color: white; }
        .bubble-text { line-height: 1.5; }
        .bubble-text p { margin-bottom: 8px; }
        .bubble-text pre { background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 8px; overflow-x: auto; }
        .bubble-text code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; }
        .bubble-text mjx-container { margin: 10px 0; overflow-x: auto; }
        .bubble-source { font-size: 0.7rem; margin-top: 6px; opacity: 0.7; }
        .input-area { padding: 15px 20px; background: white; border-top: 1px solid #e1e8ed; display: flex; gap: 10px; }
        textarea { flex: 1; padding: 10px 15px; border: 2px solid #e1e8ed; border-radius: 25px; resize: none; font-family: inherit; font-size: 0.95rem; outline: none; }
        textarea:focus { border-color: #e94560; }
        button { background: #e94560; color: white; border: none; padding: 10px 20px; border-radius: 25px; cursor: pointer; font-size: 0.95rem; transition: all 0.3s; }
        button:hover { background: #c73e56; transform: translateY(-1px); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .typing { padding: 10px 15px; color: #666; font-style: italic; display: flex; align-items: center; gap: 8px; background: white; border-radius: 18px; width: fit-content; }
        .dot { width: 6px; height: 6px; background: #666; border-radius: 50%; animation: bounce 1.4s infinite; }
        .dot:nth-child(2) { animation-delay: 0.2s; }
        .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }
        .clear-btn { background: rgba(255,255,255,0.2); margin-left: 8px; }
        .clear-btn:hover { background: rgba(255,255,255,0.3); transform: none; }
        @media (max-width: 768px) { .bubble { max-width: 85%; } .header h1 { font-size: 1rem; } }
    </style>
</head>
<body>
<div class="app">
    <div class="header">
        <h1><span>🔥</span> ИИ преподаватель по ТТД и ТМО</h1>
        <div style="display: flex; gap: 8px;">
            <div class="badge" id="kb">📚 RAG</div>
            <div class="badge" id="web">🌐 Поиск</div>
            <div class="badge" id="model">🤖 Модель</div>
            <button class="clear-btn" onclick="clearChat()">🗑️</button>
        </div>
    </div>
    <div class="messages" id="messages"></div>
    <div class="input-area">
        <textarea id="input" placeholder="Введите вопрос по термодинамике (ТТД) или тепломассообмену (ТМО)..." rows="1"></textarea>
        <button id="sendBtn" onclick="sendMessage()">📤 Отправить</button>
    </div>
</div>

<script>
    // Получение или создание sessionId
    let sessionId = localStorage.getItem('session_id');
    if (!sessionId) {
        sessionId = crypto.randomUUID();
        localStorage.setItem('session_id', sessionId);
    }
    
    let isWaiting = false;
    
    // Функция для рендеринга формул
    async function renderMath(element) {
        if (window.MathJax) {
            try {
                await MathJax.typesetPromise([element]);
            } catch(e) {
                console.log('MathJax error:', e);
            }
        }
    }
    
    // Форматирование контента
    function formatContent(text) {
        if (!text) return '';
        let formatted = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
            .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
            .replace(/\\n/g, '<br>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
        return formatted;
    }
    
    // Добавление сообщения в чат
    async function addMessage(role, content, source = null) {
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'message ' + role;
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = role === 'user' ? '👤' : '🤖';
        
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'bubble-text';
        textDiv.innerHTML = formatContent(content);
        bubble.appendChild(textDiv);
        
        if (source && role === 'bot') {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'bubble-source';
            sourceDiv.textContent = source;
            bubble.appendChild(sourceDiv);
        }
        
        div.appendChild(avatar);
        div.appendChild(bubble);
        container.appendChild(div);
        
        await renderMath(textDiv);
        container.scrollTop = container.scrollHeight;
    }
    
    // Показать индикатор печати
    function showTyping() {
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.id = 'typing';
        div.className = 'typing';
        div.innerHTML = '<div style="display:flex;gap:4px"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div><span>🤖 Преподаватель печатает...</span>';
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }
    
    // Скрыть индикатор печати
    function hideTyping() {
        const el = document.getElementById('typing');
        if (el) el.remove();
    }
    
    // Отправка сообщения
    window.sendMessage = async function() {
        const input = document.getElementById('input');
        const message = input.value.trim();
        
        if (!message) {
            console.log('Пустое сообщение');
            return;
        }
        
        if (isWaiting) {
            console.log('Уже отправляется');
            return;
        }
        
        // Очищаем поле
        input.value = '';
        input.style.height = 'auto';
        
        // Добавляем сообщение пользователя
        await addMessage('user', message);
        
        isWaiting = true;
        const sendBtn = document.getElementById('sendBtn');
        sendBtn.disabled = true;
        showTyping();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error('Ошибка сервера: ' + response.status);
            }
            
            const data = await response.json();
            hideTyping();
            await addMessage('bot', data.reply, data.source);
            
        } catch (error) {
            console.error('Ошибка:', error);
            hideTyping();
            await addMessage('bot', '❌ Ошибка: ' + error.message);
        } finally {
            isWaiting = false;
            sendBtn.disabled = false;
            input.focus();
        }
    };
    
    // Очистка чата
    window.clearChat = async function() {
        if (!confirm('Очистить историю диалога?')) return;
        
        try {
            await fetch('/api/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: sessionId })
            });
            
            document.getElementById('messages').innerHTML = '';
            await addMessage('bot', '🧹 История диалога очищена. Задайте новый вопрос!');
            
        } catch (error) {
            console.error('Ошибка очистки:', error);
            await addMessage('bot', '❌ Не удалось очистить историю');
        }
    };
    
    // Загрузка статуса
    async function loadStats() {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) return;
            const stats = await response.json();
            
            const kbEl = document.getElementById('kb');
            const webEl = document.getElementById('web');
            const modelEl = document.getElementById('model');
            
            if (kbEl) kbEl.innerHTML = stats.knowledge_base_loaded ? '📚 RAG ✅' : '📚 RAG ❌';
            if (webEl) webEl.innerHTML = stats.web_search_available ? '🌐 ' + (stats.web_search_engine || 'Поиск') + ' ✅' : '🌐 Поиск ❌';
            if (modelEl) modelEl.innerHTML = stats.ollama_available ? '🤖 ' + stats.ollama_model + ' ✅' : '🤖 Модель ❌';
        } catch(e) {
            console.log('Stats error:', e);
        }
    }
    
    // Обработчики событий
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Страница загружена');
        
        const textarea = document.getElementById('input');
        const sendBtn = document.getElementById('sendBtn');
        
        // Отправка по Enter
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Авто-изменение высоты
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
        
        // Загрузка статуса
        loadStats();
        setInterval(loadStats, 30000);
        
        // Приветственное сообщение
        setTimeout(function() {
            addMessage('bot', '👋 Здравствуйте! Я ИИ-преподаватель по **термодинамике (ТТД)** и **тепломассообмену (ТМО)**.\n\nЗадайте мне вопрос по:\n• 📚 Лабораторным работам\n• 📊 Обработке данных\n• 📖 Теоретическому материалу\n• 🔬 Подготовке к экзаменам\n\n**Пример формулы:**\n$$\\\\lambda = \\\\frac{Q \\\\cdot \\\\ln(r_2/r_1)}{2\\\\pi L \\\\cdot (t_1 - t_2)}$$');
        }, 500);
        
        textarea.focus();
    });
</script>
</body>
</html>"""

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_PAGE)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)