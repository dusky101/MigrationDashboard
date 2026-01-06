@echo off
cd /d "%~dp0"

:: 1. Check if venv exists, if not create it
if not exist .venv (
    echo Setting up the app for the first time...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

:: 2. Run the App
streamlit run app.py
pause