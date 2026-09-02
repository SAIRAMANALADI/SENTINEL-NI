param(
    [string]$Interface = "Wi-Fi",
    [int]$DurationSeconds = 330,
    [int]$Port = 8005,
    [string]$BindAddress = "127.0.0.1",
    [int]$StartupTimeoutSeconds = 60,
    [int]$HealthRequestTimeoutSeconds = 2,
    [int]$ReadinessRequestTimeoutSeconds = 5,
    [int]$LiveRequestTimeoutSeconds = 15,
    [int]$ControlRequestTimeoutSeconds = 20,
    [int]$PollIntervalMilliseconds = 500,
    [switch]$UseExistingServer
)

$ErrorActionPreference = "Stop"
if ($DurationSeconds -lt 300) {
    throw "DurationSeconds must be at least 300 for release-candidate validation"
}
if ($Port -lt 1 -or $Port -gt 65535) {
    throw "Port must be in the range 1..65535"
}
if ($StartupTimeoutSeconds -lt 1 -or $HealthRequestTimeoutSeconds -lt 1 -or $ReadinessRequestTimeoutSeconds -lt 1 -or $LiveRequestTimeoutSeconds -lt 1 -or $ControlRequestTimeoutSeconds -lt 1) {
    throw "Startup and request timeouts must be positive"
}
if ($PollIntervalMilliseconds -lt 100) {
    throw "PollIntervalMilliseconds must be at least 100"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Project virtual environment was not found: $python"
}

$env:SIH_TELEMETRY_MODE = "live"
$env:SIH_TELEMETRY_INTERFACE = $Interface
$env:SIH_API_PORT = [string]$Port
$env:SIH_AUTH_ENABLED = "false"

$apiBase = "http://$BindAddress`:$Port/api/v1"
$server = $null
$serverProcessId = $null
$telemetryStarted = $false
$logRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("sentinel-live-rc-" + [guid]::NewGuid().ToString("N"))
$stdoutLog = Join-Path $logRoot "stdout.log"
$stderrLog = Join-Path $logRoot "stderr.log"
$startedAt = Get-Date
$lastHealth = "not probed"
$lastReadiness = "not probed"
$failureCategory = "unknown"

function Redact-Text([string]$Text) {
    if ($null -eq $Text) {
        return ""
    }
    return ($Text -replace '(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+', '$1[REDACTED]' `
        -replace '(?i)(token|secret|password|private[_ -]?key)\s*[:=]\s*[^\s,;]+', '$1=[REDACTED]')
}

function Read-LogTail([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return "(no log output)"
    }
    $lines = @(Get-Content -LiteralPath $Path -Tail 30 -ErrorAction SilentlyContinue)
    if ($lines.Count -eq 0) {
        return "(no log output)"
    }
    return Redact-Text ($lines -join [Environment]::NewLine)
}

function Invoke-JsonProbe([string]$Uri, [int]$TimeoutSeconds) {
    try {
        $payload = Invoke-RestMethod -Uri $Uri -TimeoutSec $TimeoutSeconds
        return [pscustomobject]@{ status_code = 200; payload = $payload; error = $null }
    }
    catch {
        $statusCode = $null
        try {
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
        }
        catch {
            $statusCode = $null
        }
        return [pscustomobject]@{ status_code = $statusCode; payload = $null; error = Redact-Text $_.Exception.Message }
    }
}

function Get-ProcessExitCode($Process) {
    if ($null -eq $Process) {
        return $null
    }
    try {
        if ($Process.HasExited) {
            return $Process.ExitCode
        }
    }
    catch {
        return $null
    }
    return $null
}

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

try {
    if (-not $UseExistingServer) {
        $existingListener = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        if ($existingListener.Count -gt 0) {
            $existingPids = ($existingListener | Select-Object -ExpandProperty OwningProcess) -join ","
            $failureCategory = "stale_or_conflicting_listener"
            throw "Port $Port is already listening (PID $existingPids). Stop the intended service or rerun with -UseExistingServer after verifying its identity."
        }
        $server = Start-Process `
            -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "src.api.app:app", "--host", $BindAddress, "--port", [string]$Port, "--log-level", "warning") `
            -WorkingDirectory $projectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog `
            -PassThru
        $serverProcessId = $server.Id
    }
    else {
        $existingListener = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        if ($existingListener.Count -eq 0) {
            $failureCategory = "expected_existing_server_missing"
            throw "-UseExistingServer was supplied, but no listener was found on port $Port."
        }
        $serverProcessId = $existingListener[0].OwningProcess
    }

    $failureCategory = "startup_or_readiness_timeout"
    $startupDeadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $serviceReady = $false
    while ((Get-Date) -lt $startupDeadline) {
        if ($serverProcessId -and -not (Get-Process -Id $serverProcessId -ErrorAction SilentlyContinue)) {
            $failureCategory = "process_exited_before_readiness"
            throw "Sentinel process $serverProcessId exited before health/readiness succeeded."
        }

        $remainingSeconds = ($startupDeadline - (Get-Date)).TotalSeconds
        if ($remainingSeconds -le 0) {
            break
        }
        $healthTimeout = [math]::Max(1, [math]::Min($HealthRequestTimeoutSeconds, [math]::Ceiling($remainingSeconds)))
        $health = Invoke-JsonProbe "$apiBase/health" $healthTimeout
        $lastHealth = "status=$($health.status_code) error=$($health.error)"
        $healthOk = $health.status_code -eq 200 -and $health.payload.status -eq "ok" -and $health.payload.service_state -eq "HEALTHY"

        $remainingSeconds = ($startupDeadline - (Get-Date)).TotalSeconds
        if ($remainingSeconds -le 0) {
            break
        }
        $readinessTimeout = [math]::Max(1, [math]::Min($ReadinessRequestTimeoutSeconds, [math]::Ceiling($remainingSeconds)))
        $readiness = Invoke-JsonProbe "$apiBase/ready" $readinessTimeout
        $lastReadiness = "status=$($readiness.status_code) error=$($readiness.error)"
        $readinessOk = $readiness.status_code -eq 200 -and $readiness.payload.ready -eq $true

        if ($healthOk -and $readinessOk) {
            $serviceReady = $true
            break
        }
        Start-Sleep -Milliseconds $PollIntervalMilliseconds
    }
    if (-not $serviceReady) {
        throw "Sentinel did not become healthy and ready within $StartupTimeoutSeconds seconds."
    }

    Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/start" -TimeoutSec $ControlRequestTimeoutSeconds | Out-Null
    $telemetryStarted = $true
    $captureStartedAt = Get-Date
    $peakPackets = 0
    $peakFlows = 0
    $peakStates = 0
    $peakForecasts = 0
    $peakMemory = 0L
    $apiLatencies = [System.Collections.Generic.List[double]]::new()

    for ($second = 0; $second -lt $DurationSeconds; $second += 5) {
        try {
            Invoke-WebRequest -Uri "https://example.com/?rc=$second" -UseBasicParsing -TimeoutSec 4 | Out-Null
        }
        catch {
            # External traffic generation is best-effort; capture may see other host traffic.
        }

        $requestStarted = [System.Diagnostics.Stopwatch]::StartNew()
        $live = Invoke-RestMethod -Uri "$apiBase/live" -TimeoutSec $LiveRequestTimeoutSeconds
        $requestStarted.Stop()
        $apiLatencies.Add($requestStarted.Elapsed.TotalMilliseconds)

        $peakPackets = [math]::Max($peakPackets, [int]$live.telemetry.packet_quality.packets_seen)
        $peakFlows = [math]::Max($peakFlows, [int]$live.telemetry.flow_count)
        $peakStates = [math]::Max($peakStates, [int]$live.state.valid_state_count)
        $peakForecasts = [math]::Max($peakForecasts, [int]$live.forecast_update_count)
        $hostProcess = if ($serverProcessId) {
            Get-Process -Id $serverProcessId -ErrorAction SilentlyContinue
        }
        else {
            $null
        }
        if ($hostProcess) {
            $peakMemory = [math]::Max($peakMemory, [long]$hostProcess.WorkingSet64)
        }

        if (($second % 30) -eq 0) {
            Write-Output (
                "elapsed={0}s packets={1} flows={2} states={3} forecasts={4} readiness={5} dropped={6}" -f `
                    $second,
                    $peakPackets,
                    $peakFlows,
                    $peakStates,
                    $peakForecasts,
                    $live.telemetry.readiness_state,
                    $live.telemetry.packet_quality.dropped_events
            )
        }
        Start-Sleep -Seconds 5
    }

    $final = Invoke-RestMethod -Uri "$apiBase/live" -TimeoutSec $LiveRequestTimeoutSeconds
    $stopped = Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/stop" -TimeoutSec $ControlRequestTimeoutSeconds
    $telemetryStarted = $false
    Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/start" -TimeoutSec $ControlRequestTimeoutSeconds | Out-Null
    $telemetryStarted = $true
    $restarted = Invoke-RestMethod -Uri "$apiBase/live" -TimeoutSec $LiveRequestTimeoutSeconds
    Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/stop" -TimeoutSec $ControlRequestTimeoutSeconds | Out-Null
    $telemetryStarted = $false

    $sortedLatencies = @($apiLatencies | Sort-Object)
    $p95Index = [math]::Min($sortedLatencies.Count - 1, [math]::Floor($sortedLatencies.Count * 0.95))
    [pscustomobject]@{
        duration_seconds = [math]::Round(((Get-Date) - $captureStartedAt).TotalSeconds, 2)
        interface = $Interface
        packets_seen = $peakPackets
        completed_flows = $peakFlows
        valid_states = $peakStates
        forecast_updates = $peakForecasts
        final_readiness = $final.telemetry.readiness_state
        final_forecast_status = $final.forecast.status
        dropped_events = $final.telemetry.packet_quality.dropped_events
        ignored_events = $final.telemetry.packet_quality.ignored_events
        peak_working_set_bytes = $peakMemory
        live_api_mean_ms = [math]::Round(($apiLatencies | Measure-Object -Average).Average, 3)
        live_api_p95_ms = [math]::Round($sortedLatencies[$p95Index], 3)
        stop_status = $stopped.status
        restart_buffer_size = $restarted.state.buffer_size
        restart_forecast_status = $restarted.forecast.status
    } | ConvertTo-Json -Depth 4
}
catch {
    $failureElapsed = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 2)
    $exitCode = Get-ProcessExitCode $server
    Write-Error @"
Sentinel live validation failed.
category=$failureCategory
command=$python -m uvicorn src.api.app:app --host $BindAddress --port $Port --log-level warning
elapsed_seconds=$failureElapsed
health=$lastHealth
readiness=$lastReadiness
process_id=$serverProcessId
process_exit_code=$exitCode
stderr_tail=$(Read-LogTail $stderrLog)
stdout_tail=$(Read-LogTail $stdoutLog)
"@
    exit 1
}
finally {
    if ($telemetryStarted) {
        try {
            Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/stop" -TimeoutSec 5 | Out-Null
        }
        catch {
            # The process may already have exited; cleanup below remains authoritative.
        }
    }
    if (-not $UseExistingServer -and $server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
    if (Test-Path -LiteralPath $logRoot) {
        Remove-Item -LiteralPath $logRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
