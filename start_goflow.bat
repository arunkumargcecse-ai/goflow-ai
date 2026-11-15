@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_goflow.bat first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo Missing .env. Run setup_goflow.bat first.
  pause
  exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
)
if "%GOFLOW_API_KEY%"=="" (
  echo GOFLOW_API_KEY is missing from .env. Run setup_goflow.bat again.
  pause
  exit /b 1
)
echo.
echo Starting local goflow.ai API at http://127.0.0.1:8000
echo Keep this window open while using Creator Studio.
echo.
echo In the Creator Studio Backend URL field, enter:
echo http://127.0.0.1:8000
echo In the Media API key field, paste this local key:
echo %GOFLOW_API_KEY%
echo.
start "" "%~dp0index.html"
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
