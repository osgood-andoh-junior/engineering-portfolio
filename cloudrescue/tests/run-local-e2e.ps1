param(
    [Parameter(Mandatory)][string]$DatabaseUrl,
    [string]$BrowserChannel = 'msedge'
)

$ErrorActionPreference = 'Stop'
$uri = [uri]$DatabaseUrl
if ($uri.Host -notin @('127.0.0.1', 'localhost') -or
    $uri.AbsolutePath -notmatch '^/cloudrescue_e2e(?:_[a-z0-9_]+)?$') {
    throw 'Use a dedicated localhost database named cloudrescue_e2e or cloudrescue_e2e_<suffix>.'
}
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'
$logDir = Join-Path $root '.local-run'
$python = Join-Path $root '.venv/Scripts/python.exe'
$node = (Get-Command node.exe).Source
$next = Join-Path $frontend 'node_modules/next/dist/bin/next'
$processes = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()

function Start-LocalProcess($name, $file, $arguments, $directory) {
    $process = Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $directory `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir "$name.log") `
        -RedirectStandardError (Join-Path $logDir "$name.err.log")
    $processes.Add($process)
}

function Wait-LocalHttp($url) {
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "Timed out waiting for $url. See logs in $logDir."
}

foreach ($port in @(8101, 8102, 8103, 13000, 18000)) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
    try {
        $listener.Start()
    } catch {
        throw "Local test port $port is unavailable."
    } finally {
        $listener.Stop()
    }
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Push-Location $root
$variables = @{
    DATABASE_URL = $DatabaseUrl
    ADMIN_TOKEN = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    CLOUDRESCUE_API_URL = 'http://127.0.0.1:18000'
    CLOUDRESCUE_E2E_URL = 'http://127.0.0.1:13000'
    CLOUDRESCUE_BROWSER_CHANNEL = $BrowserChannel
    SIM_NETWORK = 'loopback'
    POLL_SECONDS = '1'
    MAX_BACKOFF_SECONDS = '2'
    RECOVERY_ENABLED = 'true'
}
$variables.CLOUDRESCUE_E2E_ADMIN_TOKEN = $variables.ADMIN_TOKEN
$previous = @{}
try {
    foreach ($key in $variables.Keys) {
        $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $variables[$key], 'Process')
    }
    & $python -m alembic upgrade head
    if ($LASTEXITCODE) { throw 'Migration failed.' }
    & $python -m alembic check
    if ($LASTEXITCODE) { throw 'The schema differs from the models.' }
    & $python -m backend.seed
    if ($LASTEXITCODE) { throw 'Seed failed.' }
    Start-LocalProcess 'simulator' $python '-m simulator.main' $root
    Wait-LocalHttp 'http://127.0.0.1:8101/health'
    Start-LocalProcess 'api' $python '-m uvicorn backend.api:app --host 127.0.0.1 --port 18000' $root
    Wait-LocalHttp 'http://127.0.0.1:18000/health'
    Start-LocalProcess 'worker' $python '-m backend.worker' $root
    $workerLog = Join-Path $logDir 'worker.err.log'
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Select-String -LiteralPath $workerLog -Pattern '"event": "health_check"' -Quiet) {
            break
        }
        Start-Sleep -Seconds 1
    }
    if ($attempt -eq 30) { throw 'Worker did not record a health check.' }
    $duplicate = & $python -m backend.worker 2>&1 | Out-String
    if ($LASTEXITCODE -or $duplicate -notmatch 'worker_skipped') {
        throw 'A second worker did not yield ownership.'
    }
    Start-LocalProcess 'dashboard' $node ('"' + $next + '" start --hostname 127.0.0.1 --port 13000') $frontend
    Wait-LocalHttp 'http://127.0.0.1:13000/'
    Set-Location $frontend
    npm.cmd run e2e
    if ($LASTEXITCODE) { throw 'Browser tests failed.' }
} finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) { Stop-Process -InputObject $process }
    }
    foreach ($key in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')
    }
    Pop-Location
}
