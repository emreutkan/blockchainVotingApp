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
echo You can now start the app by typing
echo python app.py --port=5001 (Note: Replace 5001 with the desired port number for each node (5002, 5003, etc.).)
REM start the app
python app.py --port=5001
