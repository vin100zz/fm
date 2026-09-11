@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Environnement virtuel introuvable dans .venv\ — voir CLAUDE.md pour l'installation.
    pause
    exit /b 1
)

echo Demarrage de Football Manager Light sur http://localhost:8000 ...
echo (Ctrl+C dans cette fenetre pour arreter le serveur)

start "" cmd /c "timeout /t 2 >nul & start http://localhost:8000"

.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir src --port 8000
