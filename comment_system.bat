@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python comment_system.py %*
pause