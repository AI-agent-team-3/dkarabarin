@echo off
echo ========================================
echo  Запуск бота-преподавателя
echo ========================================
echo.

REM Проверка .env
if not exist ".env" (
    echo [ОШИБКА] Файл .env не найден!
    echo Создайте .env на основе .env.example
    pause
    exit /b 1
)

REM Активация окружения
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ВНИМАНИЕ] Виртуальное окружение не найдено
)

REM Проверка Ollama
echo Проверка Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [ВНИМАНИЕ] Ollama не запущен!
    echo Запустите в другом окне: ollama serve
)

REM Запуск бота
echo Запуск бота...
python bot-local.py

pause