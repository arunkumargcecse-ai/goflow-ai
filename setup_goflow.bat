@echo off
setlocal
cd /d "%~dp0"
echo.
echo  goflow.ai - Windows first-time setup
echo  This installs Python packages only. No AI model weights are downloaded.
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher not found.
  echo Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
  echo During installation, enable "Add python.exe to PATH".
  pause
  exit /b 1
)

py -3.12 --version >nul 2>nul
if not errorlevel 1 (
  set "PYTHON=py -3.12"
) else (
  py -3.11 --version >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python 3.11 or 3.12 is required.
    pause
    exit /b 1
  )
  set "PYTHON=py -3.11"
)

if not exist ".venv\Scripts\python.exe" (
  %PYTHON% -m venv .venv
  if errorlevel 1 goto :failed
)

.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 goto :failed

if not exist ".env" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$bytes=New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Fill($bytes); $key=[Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_'); Set-Content -Encoding ASCII -Path '.env' -Value ('GOFLOW_API_KEY='+$key)"
  if errorlevel 1 goto :failed
)

echo.
echo Setup complete.
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo WARNING: FFmpeg was not found. Install FFmpeg and add its bin folder to PATH.
) else (
  echo FFmpeg found.
)
where ffprobe >nul 2>nul
if errorlevel 1 echo WARNING: ffprobe was not found. Reference-video analysis and quality checks need it.
echo.
echo Next: double-click start_goflow.bat
pause
exit /b 0

:failed
echo.
echo Setup failed. Check the error above and retry.
pause
exit /b 1
