$found = Get-ChildItem -Path "src" -Filter "*.py" -Recurse |
    Select-String -Pattern "#\s*(XXX|SECURITY):"

if ($found) {
    $lines = ($found | ForEach-Object {
        "  $($_.Filename):$($_.LineNumber): $($_.Line.Trim())"
    }) -join "`n"

    $context = "Blocking markers still present in src/:`n$lines`nResolve all XXX and SECURITY markers before this task is complete."

    $json = "{`"hookSpecificOutput`":{`"hookEventName`":`"Stop`",`"additionalContext`":`"$($context -replace '\\','\\\\' -replace '"','\"' -replace "`n",'\n')`"}}"
    Write-Output $json
}
exit 0
