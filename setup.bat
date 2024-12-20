@echo off

REM Create virtual environment
python -m venv venv

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
pip install --upgrade pip

REM Install dependencies
pip install Flask requests

REM Generate requirements.txt
pip freeze > requirements.txt

echo Virtual environment setup complete and activated.
pause
