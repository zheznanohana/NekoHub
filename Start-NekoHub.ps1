param([switch]$ServicesOnly)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Python = Join-Path $Root 'backend\memory_v1\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Install the backend, desktop and social requirements in backend/memory_v1/.venv first.' }
$State = Join-Path $env:LOCALAPPDATA 'NekoHubMemory'
New-Item -ItemType Directory -Path $State -Force | Out-Null
# DPAPI protects the local service token for the current Windows user.
$TokenFile = Join-Path $State 'service-token.xml'
if (-not (Test-Path -LiteralPath $TokenFile)) {
    $Bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Bytes)
    ConvertTo-SecureString ([Convert]::ToBase64String($Bytes)) -AsPlainText -Force | Export-Clixml -LiteralPath $TokenFile
}
$env:MEMORY_SERVICE_TOKEN = [System.Net.NetworkCredential]::new('', (Import-Clixml -LiteralPath $TokenFile)).Password
$env:MEMORY_SERVICE_URL = 'http://127.0.0.1:18081'
$env:MEMORY_DB_PATH = Join-Path $State 'memory.db'
$env:MEMORY_CONNECTOR_OWNER = 'admin'
$env:MEMORY_AGENT_RUNTIME = 'pi'
# Local ONNX embeddings: no key, no network at query time, nothing leaves the machine.
# bge-small-zh-v1.5 measured best on this corpus (5/6 vs 3/6) at a ninth of jina's cost.
$env:MEMORY_EMBED_BACKEND = 'local'
$env:MEMORY_EMBED_MODEL = 'BAAI/bge-small-zh-v1.5'
$env:MEMORY_EMBED_CACHE = Join-Path $State 'embed-cache'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
$env:MEMORY_GITHUB_REPO = 'zheznanohana/NekoHub'
# One-click import of the pre-memory desktop database, when a copy is present.
$LegacyDb = Join-Path $State 'legacy-nekohub.db'
if (Test-Path -LiteralPath $LegacyDb) { $env:MEMORY_LEGACY_DB = $LegacyDb }
$ConfigFile = Join-Path $State 'environment.xml'
if (Test-Path -LiteralPath $ConfigFile) {
    $SecretConfig = [System.Net.NetworkCredential]::new('', (Import-Clixml -LiteralPath $ConfigFile)).Password | ConvertFrom-Json
    foreach ($Property in $SecretConfig.PSObject.Properties) {
        if ($Property.Name -in @('MEMORY_LLM_BASE_URL','MEMORY_LLM_MODEL','MEMORY_LLM_API_KEY','MEMORY_EMBED_BASE_URL','MEMORY_EMBED_MODEL','MEMORY_EMBED_API_KEY','MEMORY_GOTIFY_URL','MEMORY_GOTIFY_TOKEN','MEMORY_GITHUB_TOKEN')) {
            [Environment]::SetEnvironmentVariable($Property.Name, [string]$Property.Value, 'Process')
        }
    }
}
$env:NEKOHUB_SOCIAL_CONFIG = Join-Path $State 'social.json'
if (-not (Test-Path -LiteralPath $env:NEKOHUB_SOCIAL_CONFIG)) {
    Copy-Item -LiteralPath (Join-Path $Root 'integrations\social\config.example.json') -Destination $env:NEKOHUB_SOCIAL_CONFIG
}
# Gotify runs as the official release binary; the DPAPI config holds its tokens.
$GotifyDir = Join-Path $State 'gotify'
$GotifyExe = Join-Path $GotifyDir 'gotify-windows-amd64.exe'
if (Test-Path -LiteralPath $GotifyExe) {
    $GotifyPidFile = Join-Path $State 'gotify.pid'
    $GotifyRunning = $false
    if (Test-Path -LiteralPath $GotifyPidFile) {
        $ExistingId = [int](Get-Content -LiteralPath $GotifyPidFile)
        $Existing = Get-CimInstance Win32_Process -Filter "ProcessId=$ExistingId" -ErrorAction SilentlyContinue
        $GotifyRunning = $Existing -and $Existing.ExecutablePath -eq $GotifyExe
    }
    if (-not $GotifyRunning) {
        $GotifyProcess = Start-Process -FilePath $GotifyExe -WorkingDirectory $GotifyDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $State 'gotify.log') -RedirectStandardError (Join-Path $State 'gotify.err.log')
        $GotifyProcess.Id | Set-Content -LiteralPath $GotifyPidFile
    }
    # The worker pulls on its own schedule; a slow start here is not fatal.
    foreach ($Attempt in 1..10) {
        try { Invoke-RestMethod 'http://127.0.0.1:18080/health' -TimeoutSec 2 | Out-Null; break }
        catch { Start-Sleep -Milliseconds 500 }
    }
}

function Start-ServiceModule([string]$Name, [string]$Module) {
    $PidFile = Join-Path $State ($Name + '.pid')
    if (Test-Path -LiteralPath $PidFile) {
        $ExistingId = [int](Get-Content -LiteralPath $PidFile)
        $Existing = Get-CimInstance Win32_Process -Filter "ProcessId=$ExistingId" -ErrorAction SilentlyContinue
        if ($Existing -and $Existing.ExecutablePath -eq $Python -and $Existing.CommandLine.Contains($Module)) { return }
    }
    $Process = Start-Process -FilePath $Python -ArgumentList @('-m',$Module) -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $State ($Name+'.log')) -RedirectStandardError (Join-Path $State ($Name+'.err.log'))
    $Process.Id | Set-Content -LiteralPath $PidFile
}
Start-ServiceModule 'memory-server' 'backend.memory_v1.server'
Start-ServiceModule 'memory-worker' 'backend.memory_v1.worker'
Start-ServiceModule 'social-bridge' 'integrations.social.bridge'
if (-not $ServicesOnly) {
    # pythonw keeps the desktop app from opening a console window alongside it.
    $Pythonw = Join-Path $Root 'backend\memory_v1\.venv\Scripts\pythonw.exe'
    if (-not (Test-Path -LiteralPath $Pythonw)) { $Pythonw = $Python }
    Start-Process -FilePath $Pythonw -ArgumentList @('ui_app.py') -WorkingDirectory (Join-Path $Root 'pc') | Out-Null
}
Write-Output 'NekoHub launch requested. Local status/logs: %LOCALAPPDATA%\NekoHubMemory. Social accounts need platform credentials and allowed sessions.'
