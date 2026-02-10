@echo off
echo 🚀 Launching Migration Mission Control...
echo ----------------------------------------
cd /d "%~dp0"
python -m streamlit run app.py --global.developmentMode=false
pause