<#
RepoPilot local launcher for Windows PowerShell 5.1 and WSL Ubuntu.
Place in scripts/start-local.ps1. Requires the existing configured project,
Windows Node/npm and ~/repopilot-venv in Ubuntu. No installation or migrations.
Stop existing Django, Celery and frontend terminals before running.
Celery can resume queued jobs, which may use configured paid services.
Stop: Ctrl+C in Celery, wait for shutdown, then Ctrl+C in Django and frontend.
PostgreSQL and Redis remain running for other local users of those services.
#>
[CmdletBinding()]
param([string]$Distribution = 'Ubuntu')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot 'frontend'

function Quote-PS([string]$Value) {
    return "'" + $Value.Replace("'", "''") + "'"
}
function Assert-NativeSuccess([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}
function Open-ServiceTerminal([string]$Title, [string]$Command) {
    $body = '$Host.UI.RawUI.WindowTitle = ' + (Quote-PS $Title) + "`r`n" +
        '$ErrorActionPreference = ''Stop''' + "`r`n" +
        'try {' + "`r`n" + $Command + "`r`n" +
        'Write-Host "Process exited with code $LASTEXITCODE."' + "`r`n" +
        '} catch { Write-Host $_.Exception.Message -ForegroundColor Red }'
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($body))
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-NoExit', '-EncodedCommand', $encoded
    ) | Out-Null
}

try {
    foreach ($tool in @('wsl.exe', 'node.exe', 'npm.cmd')) {
        Get-Command $tool -ErrorAction Stop | Out-Null
    }
    foreach ($file in @('backend/manage.py', 'backend/.env', 'frontend/.env.local',
                         'frontend/node_modules/next/package.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $file))) {
            throw "Missing $file. Complete local setup before using this launcher."
        }
    }
    foreach ($port in @(3000, 8000)) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $pending = $client.ConnectAsync('127.0.0.1', $port)
            try { $null = $pending.Wait(500) } catch { }
            if ($client.Connected) {
                throw "Port $port is occupied. Stop the existing development server first."
            }
        } finally { $client.Dispose() }
    }
    $linuxRoot = & wsl.exe -d $Distribution --exec wslpath -a $repoRoot
    Assert-NativeSuccess 'Could not resolve the project path inside WSL.'
    $linuxRoot = ($linuxRoot -join "`n").Trim()
    $linuxUserHome = & wsl.exe -d $Distribution --exec printenv HOME
    Assert-NativeSuccess 'Could not read the WSL user home directory.'
    $linuxUserHome = ($linuxUserHome -join "`n").Trim()
    $pythonPath = "$linuxUserHome/repopilot-venv/bin/python"
    $celeryPath = "$linuxUserHome/repopilot-venv/bin/celery"
    foreach ($binary in @($pythonPath, $celeryPath)) {
        & wsl.exe -d $Distribution --exec test -x $binary
        Assert-NativeSuccess "Missing executable: $binary"
    }

    Write-Host 'Starting PostgreSQL and Redis. Ubuntu may ask for your sudo password.'
    & wsl.exe -d $Distribution --exec sudo service postgresql start
    Assert-NativeSuccess 'PostgreSQL could not start.'
    & wsl.exe -d $Distribution --exec sudo service redis-server start
    Assert-NativeSuccess 'Redis could not start.'
    $redisReply = & wsl.exe -d $Distribution --exec redis-cli ping
    Assert-NativeSuccess 'Redis connection check failed.'
    if (($redisReply -join '').Trim() -ne 'PONG') { throw 'Redis did not return PONG.' }
    & wsl.exe -d $Distribution --exec pg_isready -h 127.0.0.1 -p 5432
    Assert-NativeSuccess 'PostgreSQL is not accepting connections.'

    $wslCommand = '& wsl.exe -d ' + (Quote-PS $Distribution) + ' --cd '
    Open-ServiceTerminal 'RepoPilot - Django' ($wslCommand +
        (Quote-PS $linuxRoot) + ' --exec ' + (Quote-PS $pythonPath) +
        ' backend/manage.py runserver 127.0.0.1:8000')
    Open-ServiceTerminal 'RepoPilot - Celery' ($wslCommand +
        (Quote-PS "$linuxRoot/backend") + ' --exec ' + (Quote-PS $celeryPath) +
        ' -A config worker --loglevel=info --concurrency=1')
    Open-ServiceTerminal 'RepoPilot - Frontend' (
        'Set-Location -LiteralPath ' + (Quote-PS $frontendRoot) + "`r`n" +
        '& npm.cmd run dev -- --hostname 127.0.0.1 --port 3000')
    Write-Host 'Three terminals opened. Check each terminal for readiness or errors.'
    Write-Host 'When all are ready, open http://localhost:3000'
} catch {
    Write-Host ('Startup stopped: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
