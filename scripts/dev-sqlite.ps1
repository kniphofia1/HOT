$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$DatabasePath = (Join-Path $Backend "dev-preview.db").Replace("\", "/")
$BackendPython = Join-Path $Backend ".venv/Scripts/python.exe"
$Alembic = Join-Path $Backend ".venv/Scripts/alembic.exe"
$EnvFile = Join-Path $Root ".env"

$loadedEnvKeys = 0
if (Test-Path $EnvFile) {
  foreach ($rawLine in Get-Content $EnvFile) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
      continue
    }
    $name, $value = $line.Split("=", 2)
    $name = $name.Trim()
    if ($name -eq "DATABASE_URL") {
      continue
    }
    [Environment]::SetEnvironmentVariable($name, $value.Trim(), "Process")
    $script:loadedEnvKeys += 1
  }
}

$env:DATABASE_URL = "sqlite:///$DatabasePath"
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"

Push-Location $Backend
try {
  & $Alembic upgrade head
}
finally {
  Pop-Location
}

Start-Process `
  -FilePath $BackendPython `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
  -WorkingDirectory $Backend `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $Backend "dev-sqlite-backend.log") `
  -RedirectStandardError (Join-Path $Backend "dev-sqlite-backend.err.log")

Start-Process `
  -FilePath "npm.cmd" `
  -ArgumentList "run", "dev" `
  -WorkingDirectory $Frontend `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $Frontend "dev-sqlite-frontend.log") `
  -RedirectStandardError (Join-Path $Frontend "dev-sqlite-frontend.err.log")

Write-Host "SQLite database: $DatabasePath"
Write-Host "Loaded environment values from .env: $loadedEnvKeys"
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:3000"
