$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  Write-Output "ERROR: .venv not found. Create it first:"
  Write-Output "  python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
  exit 1
}

& $python bot.py
