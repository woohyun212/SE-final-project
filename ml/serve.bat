@echo off
chcp 65001 > nul
cd /d %~dp0
echo ML 추론 서버 시작 중 (port 8001)...
.venv\Scripts\python.exe -m uvicorn serve.app:app --host 0.0.0.0 --port 8001
pause
