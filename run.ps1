$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
$venv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$exe = if (Test-Path $venv) { $venv } else { "python" }
Start-Process -FilePath $exe -ArgumentList (@("-m", "skill_scan") + $args) -WorkingDirectory $PSScriptRoot
