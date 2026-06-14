$result = ruff check src/ 2>&1
if ($LASTEXITCODE -ne 0) {
    $result | ForEach-Object { [Console]::Error.WriteLine($_) }
    exit 2
}
exit 0
