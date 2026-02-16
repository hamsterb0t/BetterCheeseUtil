@echo off
cd /d "%~dp0"
echo Building with virtual environment...
".venv\Scripts\python.exe" -m PyInstaller --clean main.spec
echo Build complete.
pause