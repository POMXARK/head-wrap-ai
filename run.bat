@echo off
rem The panel of head-wrap-ai (pipeline, review, model): opens http://127.0.0.1:8770/pipeline and stays open.
cd /d "%~dp0"
start "" http://127.0.0.1:8770/pipeline
python app.py
pause
