@echo off
echo ========================================
echo  Установка бота-преподавателя
echo ========================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не установлен!
    echo Скачайте Python 3.11 с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Создание виртуального окружения...
python -m venv venv

echo [2/5] Активация...
call venv\Scripts\activate.bat

echo [3/5] Обновление pip...
python -m pip install --upgrade pip

echo [4/5] Установка зависимостей...
pip install -r requirements.txt

echo [5/5] Создание папки books...
if not exist "books" mkdir books

echo.
echo ========================================
echo  Установка завершена!
echo ========================================
echo.
echo Для запуска бота:
echo   venv\Scripts\activate.bat
echo   python bot-local.py
echo.
pause