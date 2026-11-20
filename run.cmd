@echo off
REM Start the triage agent from the project venv, creating the venv if missing.
REM
REM   run.cmd                -> opens the web UI
REM   run.cmd TICKET-001     -> runs one ticket in the terminal

setlocal
cd /d "%~dp0"

set PY=.venv\Scripts\python.exe

if not exist "%PY%" (
  echo No .venv here yet - creating it and installing requirements.
  python -m venv .venv || goto :fail
  "%PY%" -m pip install --quiet --upgrade pip || goto :fail
  "%PY%" -m pip install --quiet -r requirements.txt || goto :fail
  echo Venv ready.
)

if "%~1"=="" (
  echo Opening http://localhost:8501
  "%PY%" -m streamlit run app.py
) else (
  "%PY%" main.py %1
)
goto :eof

:fail
echo Setup failed. Check that "python" is on your PATH.
exit /b 1
