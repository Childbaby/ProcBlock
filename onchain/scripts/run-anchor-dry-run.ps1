param(
    [string]$RpcUrl = 'http://127.0.0.1:8899',
    [int]$RpcPort = 8899,
    [int]$FaucetPort = 9900,
    [string]$LedgerPath = '.\.anchor\dev-ledger',
    [string]$ProgramId = '8had5koATJfLWrZ5yMrnSsQ5Ssc5aW4EWNtwrHzb4Prz',
    [string]$ProgramSoPath = '.\target\deploy\vaxchain_trust_layer.so',
    [string]$PythonExecutable = 'C:\Users\Desktop\Projects\Procurement\.venv\Scripts\python.exe',
    [string]$DryRunScriptPath = '..\server\scripts\dry_run_anchor_bridge.py',
    [string]$HubCode = 'ZMHUB001',
    [string]$KeypairPath = '',
    [switch]$UseExistingValidator,
    [switch]$StartElevatedValidator
)

$ErrorActionPreference = 'Stop'
$isWindowsPlatform = $env:OS -eq 'Windows_NT'

function Resolve-FullPath {
    param(
        [string]$PathValue,
        [string]$BasePath
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $PathValue))
}

function Test-RpcHealth {
    param([string]$Url)

    $body = '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5
        return $resp.Content -match '"ok"'
    }
    catch {
        return $false
    }
}

function Get-CurrentSlot {
    param([string]$Url)

    $body = '{"jsonrpc":"2.0","id":1,"method":"getSlot","params":[{"commitment":"processed"}]}'
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5
        $json = $resp.Content | ConvertFrom-Json
        if ($null -eq $json.result) {
            return $null
        }
        return [int64]$json.result
    }
    catch {
        return $null
    }
}

function Test-ProgramPresent {
    param(
        [string]$Url,
        [string]$ProgramPubkey
    )

    $body = "{`"jsonrpc`":`"2.0`",`"id`":1,`"method`":`"getAccountInfo`",`"params`": [`"$ProgramPubkey`", {`"encoding`":`"base64`"}] }"
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5
        return $resp.Content -notmatch '"value":null'
    }
    catch {
        return $false
    }
}

function Wait-RpcReady {
    param(
        [string]$Url,
        [int]$MaxSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-RpcHealth -Url $Url) {
            return $true
        }
        Start-Sleep -Seconds 2
    }

    return $false
}

function Wait-RpcProgress {
    param(
        [string]$Url,
        [int]$MaxSeconds = 30,
        [int]$IntervalSeconds = 2
    )

    $lastSlot = Get-CurrentSlot -Url $Url
    if ($null -eq $lastSlot) {
        return $false
    }

    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds $IntervalSeconds
        $currentSlot = Get-CurrentSlot -Url $Url
        if ($null -eq $currentSlot) {
            continue
        }
        if ($currentSlot -gt $lastSlot) {
            return $true
        }
        $lastSlot = $currentSlot
    }

    return $false
}

function Test-PortAvailable {
    param([int]$Port)

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse('127.0.0.1'), $Port)
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $listener) {
            $listener.Stop()
        }
    }
}

function Get-NextAvailablePort {
    param(
        [int]$StartPort,
        [int]$MaxPort = 65535
    )

    for ($port = $StartPort; $port -le $MaxPort; $port++) {
        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }

    return $null
}

function Stop-ValidatorProcesses {
    $names = @('solana-test-validator', 'agave-validator')
    $found = $false

    foreach ($name in $names) {
        $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
        if ($procs) {
            $found = $true
            $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        }
    }

    if (-not $found) {
        return $true
    }

    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        $stillRunning = $false
        foreach ($name in $names) {
            if (Get-Process -Name $name -ErrorAction SilentlyContinue) {
                $stillRunning = $true
                break
            }
        }

        if (-not $stillRunning) {
            return $true
        }

        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Test-IsWindowsAdmin {
    if (-not $isWindowsPlatform) {
        return $false
    }

    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = [Security.Principal.WindowsPrincipal]::new($identity)
        return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch {
        return $false
    }
}

Set-Location (Split-Path -Parent $PSScriptRoot)
$onchainRoot = Get-Location

$ledgerFullPath = Resolve-FullPath -PathValue $LedgerPath -BasePath $onchainRoot
$programSoFullPath = Resolve-FullPath -PathValue $ProgramSoPath -BasePath $onchainRoot
$pythonFullPath = Resolve-FullPath -PathValue $PythonExecutable -BasePath $onchainRoot
$dryRunScriptFullPath = Resolve-FullPath -PathValue $DryRunScriptPath -BasePath $onchainRoot
$effectiveRpcUrl = $RpcUrl
$effectiveRpcPort = $RpcPort
$effectiveFaucetPort = $FaucetPort
$effectiveLedgerPath = $ledgerFullPath

if (-not $KeypairPath) {
    $KeypairPath = Join-Path $HOME '.config\solana\id.json'
}
$keypairFullPath = Resolve-FullPath -PathValue $KeypairPath -BasePath $onchainRoot

if (-not (Test-Path $programSoFullPath)) {
    throw "Program .so file was not found: $programSoFullPath"
}

if (-not (Test-Path $pythonFullPath)) {
    throw "Python executable was not found: $pythonFullPath"
}

if (-not (Test-Path $dryRunScriptFullPath)) {
    throw "Dry-run script was not found: $dryRunScriptFullPath"
}

if (-not (Test-Path $keypairFullPath)) {
    throw "Keypair file was not found: $keypairFullPath"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ledgerFullPath) | Out-Null

$healthy = Test-RpcHealth -Url $effectiveRpcUrl
$programExists = $false
$slotProgressing = $false
if ($healthy) {
    $programExists = Test-ProgramPresent -Url $effectiveRpcUrl -ProgramPubkey $ProgramId
    $slotProgressing = Wait-RpcProgress -Url $effectiveRpcUrl -MaxSeconds 10 -IntervalSeconds 2
}

$existingValidatorReady = $healthy -and $programExists -and $slotProgressing
$shouldStartValidator = -not $existingValidatorReady

if ($existingValidatorReady) {
    Write-Host "Using existing validator at $effectiveRpcUrl (healthy, progressing, program preloaded)." -ForegroundColor DarkCyan
}

if ($shouldStartValidator) {
    Write-Host "Starting local validator with preloaded program..." -ForegroundColor Yellow

    $useElevatedLaunch = $false
    if ($isWindowsPlatform) {
        $useElevatedLaunch = $StartElevatedValidator -or -not (Test-IsWindowsAdmin)
    }

    if ($useElevatedLaunch) {
        Write-Host "Launching validator in elevated mode on Windows." -ForegroundColor DarkYellow

        $validatorCmd = "Get-Process solana-test-validator -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; " +
            "solana-test-validator --reset --ledger '$effectiveLedgerPath' --bind-address 127.0.0.1 --rpc-port $effectiveRpcPort --faucet-port $effectiveFaucetPort --bpf-program $ProgramId '$programSoFullPath' --limit-ledger-size 10000"

        Start-Process powershell -Verb RunAs -ArgumentList @('-NoExit', '-Command', $validatorCmd) | Out-Null
    }
    else {
        if (-not (Stop-ValidatorProcesses)) {
            $fallbackRpcPort = Get-NextAvailablePort -StartPort ($RpcPort + 1)
            $fallbackFaucetPort = Get-NextAvailablePort -StartPort ($FaucetPort + 1)

            if (($null -eq $fallbackRpcPort) -or ($null -eq $fallbackFaucetPort)) {
                throw "Unable to stop existing validator processes and no fallback ports are available. If you are on Windows, retry with -StartElevatedValidator."
            }

            if ($fallbackRpcPort -eq $fallbackFaucetPort) {
                $fallbackFaucetPort = Get-NextAvailablePort -StartPort ($fallbackFaucetPort + 1)
                if ($null -eq $fallbackFaucetPort) {
                    throw "Unable to allocate distinct fallback RPC and faucet ports."
                }
            }

            $effectiveRpcPort = $fallbackRpcPort
            $effectiveFaucetPort = $fallbackFaucetPort
            $effectiveRpcUrl = "http://127.0.0.1:$effectiveRpcPort"
            $effectiveLedgerPath = Resolve-FullPath -PathValue (".\.anchor\dev-ledger-$effectiveRpcPort") -BasePath $onchainRoot

            Write-Host "Existing validator could not be stopped. Falling back to RPC $effectiveRpcPort / faucet $effectiveFaucetPort." -ForegroundColor Yellow
        }

        $validatorArgs = @(
            '--reset',
            '--ledger', $effectiveLedgerPath,
            '--bind-address', '127.0.0.1',
            '--rpc-port', "$effectiveRpcPort",
            '--faucet-port', "$effectiveFaucetPort",
            '--bpf-program', $ProgramId, $programSoFullPath,
            '--limit-ledger-size', '10000'
        )

        if ($isWindowsPlatform) {
            Start-Process -FilePath 'solana-test-validator' -ArgumentList $validatorArgs -WindowStyle Minimized | Out-Null
        }
        else {
            Start-Process -FilePath 'solana-test-validator' -ArgumentList $validatorArgs | Out-Null
        }
    }
}

if (-not (Wait-RpcReady -Url $effectiveRpcUrl -MaxSeconds 90)) {
    if ($isWindowsPlatform) {
        throw "Validator did not become healthy at $effectiveRpcUrl. If a UAC prompt appeared, approve it or rerun from an elevated PowerShell shell."
    }
    throw "Validator did not become healthy at $effectiveRpcUrl."
}

if (-not (Wait-RpcProgress -Url $effectiveRpcUrl -MaxSeconds 30 -IntervalSeconds 2)) {
    if ($isWindowsPlatform -and $shouldStartValidator) {
        throw "Validator at $effectiveRpcUrl is reachable but slot is not advancing. Ensure the elevated validator window was allowed to start, then retry."
    }
    throw "Validator at $effectiveRpcUrl is reachable but slot is not advancing. Restart validator and retry."
}

if (-not (Test-ProgramPresent -Url $effectiveRpcUrl -ProgramPubkey $ProgramId)) {
    throw "Program $ProgramId was not found on validator at $effectiveRpcUrl."
}

Write-Host "Running Anchor dry-run bridge script..." -ForegroundColor Cyan
$env:PROCBLOCK_DRY_RUN_RPC_URL = $effectiveRpcUrl
$env:PROCBLOCK_DRY_RUN_PROGRAM_ID = $ProgramId
$env:PROCBLOCK_DRY_RUN_HUB_CODE = $HubCode
$env:PROCBLOCK_DRY_RUN_KEYPAIR_PATH = $keypairFullPath

& $pythonFullPath $dryRunScriptFullPath
if ($LASTEXITCODE -ne 0) {
    throw "Dry-run script failed with exit code $LASTEXITCODE"
}

Write-Host "Anchor dry-run completed successfully." -ForegroundColor Green
