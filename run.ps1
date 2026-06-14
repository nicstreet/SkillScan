$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
$venv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venv) {
    & $venv -m skill_scan @args
} else {
    python -m skill_scan @args
}
