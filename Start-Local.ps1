param(
    [ValidateRange(1024, 65515)]
    [int]$Port = 8080
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$runner = Join-Path $root 'scripts\serve-local.py'
$logs = Join-Path $root '.local'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'The local Python environment is missing. Install backend/requirements.txt in .venv first.'
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'web\dist\index.html'))) {
    throw 'The frontend build is missing. Run pnpm run build from the web folder first.'
}

New-Item -ItemType Directory -Path $logs -Force | Out-Null
$lastPort = $Port + 20
while ($Port -le $lastPort) {
    $url = "http://127.0.0.1:$Port"
    try {
        $health = Invoke-RestMethod -Uri "$url/_local/health" -TimeoutSec 2
        if ($health.application -eq 'SmartTodo' -and $health.mode -eq 'local') {
            Write-Output "SmartTodo is already running: $url"
            exit 0
        }
    } catch {
        # An unused port will not have a health endpoint.
    }

    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback, $Port
    )
    try {
        $listener.Start()
        $listener.Stop()
        break
    } catch {
        $listener.Stop()
        $Port++
    }
}
if ($Port -gt $lastPort) {
    throw 'No free local port was found.'
}

$stdout = Join-Path $logs "server-$Port.stdout.log"
$stderr = Join-Path $logs "server-$Port.stderr.log"
$env:PYTHONUTF8 = '1'
$env:ENV = 'DEV'
$process = Start-Process -FilePath $python `
    -ArgumentList @('-X', 'utf8', "`"$runner`"", '--port', "$Port") `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "$url/_local/health" -TimeoutSec 2
        if ($health.application -eq 'SmartTodo') {
            Write-Output "SmartTodo is ready: $url"
            Write-Output "Local mode: no login required."
            Write-Output "Logs: $logs"
            exit 0
        }
    } catch {
        if ($process.HasExited) {
            Get-Content -LiteralPath $stderr -ErrorAction SilentlyContinue
            throw 'SmartTodo could not start. See the log above.'
        }
        Start-Sleep -Milliseconds 500
    }
}
throw "SmartTodo did not become ready. Check $stderr"
