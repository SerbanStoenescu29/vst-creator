# Start the triage agent from the project venv, creating the venv if it's missing.
#
#   .\run.ps1                 -> opens the web UI
#   .\run.ps1 TICKET-001      -> runs one ticket in the terminal

param([string]$Ticket)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Host 'No .venv here yet - creating it and installing requirements.' -ForegroundColor Yellow
    python -m venv (Join-Path $root '.venv')
    & $py -m pip install --quiet --upgrade pip
    & $py -m pip install --quiet -r (Join-Path $root 'requirements.txt')
    Write-Host 'Venv ready.' -ForegroundColor Green
}

if ($Ticket) {
    & $py (Join-Path $root 'main.py') $Ticket
} else {
    Write-Host 'Opening http://localhost:8501' -ForegroundColor Cyan
    & $py -m streamlit run (Join-Path $root 'app.py')
}
