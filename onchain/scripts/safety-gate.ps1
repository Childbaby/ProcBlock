param(
    [switch]$SkipRuntimeTests
)

$ErrorActionPreference = 'Stop'

function Set-SolanaBuildHome {
    # Allow explicit override for CI or local setups.
    if ($env:PROCBLOCK_HOME_PATH) {
        $env:USERPROFILE = $env:PROCBLOCK_HOME_PATH
        $env:HOME = $env:PROCBLOCK_HOME_PATH
        return
    }

    # Keep backward compatibility for this workstation layout when present.
    if ($IsWindows -and (Test-Path 'C:\Users\Desktop')) {
        $env:USERPROFILE = 'C:\Users\Desktop'
        $env:HOME = 'C:\Users\Desktop'
        return
    }

    # Ensure HOME is available for toolchains that depend on it.
    if (-not $env:HOME -and $env:USERPROFILE) {
        $env:HOME = $env:USERPROFILE
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "\n==> $Name" -ForegroundColor Cyan
    & $Action
    Write-Host "PASS: $Name" -ForegroundColor Green
}

function Test-ValidatorHealth {
    $body = '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8899' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5
        return $resp.Content -match '"ok"'
    }
    catch {
        return $false
    }
}

Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Running ProcBlock onchain safety gate..." -ForegroundColor Yellow
Set-SolanaBuildHome

Invoke-Step -Name 'SBF build' -Action {
    cargo-build-sbf -v --manifest-path '.\programs\vaxchain_trust_layer\Cargo.toml'
}

Invoke-Step -Name 'Anchor build (IDL regeneration)' -Action {
    anchor build
}

Invoke-Step -Name 'TypeScript compile check' -Action {
    npx tsc -p .\tsconfig.json --noEmit
}

if (-not $SkipRuntimeTests) {
    if (-not (Test-ValidatorHealth)) {
        Write-Host "\nValidator is not reachable at 127.0.0.1:8899." -ForegroundColor Red
        Write-Host "Start it first (prefer elevated terminal on this machine):" -ForegroundColor Yellow
        Write-Host "solana-test-validator --bind-address 127.0.0.1 --rpc-port 8899 --faucet-port 9900" -ForegroundColor Yellow
        Write-Host "Or run: .\scripts\run-anchor-dry-run.ps1 -StartElevatedValidator" -ForegroundColor Yellow
        exit 2
    }

    Invoke-Step -Name 'Runtime integration tests' -Action {
        npx ts-mocha -p .\tsconfig.json -t 1000000 tests\vaxchain_trust_layer.ts
    }
}

Write-Host "\nAll configured safety checks passed." -ForegroundColor Green
