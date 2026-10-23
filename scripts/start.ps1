# Загружает локальные настройки и запускает Django вместе с собранным сайтом.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Command)
$projectRoot = Split-Path -Parent $PSScriptRoot
$settingsFile = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $settingsFile)) { throw 'Create .env from .env.example first.' }
Get-Content -LiteralPath $settingsFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        $parts = $line.Split('=', 2)
        if ($parts.Count -eq 2) { [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process') }
    }
}
if ($Command.Count -gt 0) {
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $projectRoot 'manage.py') @Command
} else {
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $projectRoot 'manage.py') runserver 127.0.0.1:8765
}
exit $LASTEXITCODE
