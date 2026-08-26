param(
    [string]$Interface = "Wi-Fi",
    [int]$DurationSeconds = 330,
    [int]$Port = 8005,
    [switch]$UseExistingServer
)

$ErrorActionPreference = "Stop"
if ($DurationSeconds -lt 300) {
    throw "DurationSeconds must be at least 300 for release-candidate validation"
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

$apiBase = "http://127.0.0.1:$Port/api/v1"
$server = $null
if (-not $UseExistingServer) {
    $server = Start-Process `
        -FilePath $python `
        -ArgumentList "-m", "uvicorn", "src.api.app:app", "--host", "127.0.0.1", "--port", [string]$Port, "--log-level", "warning" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -PassThru
}

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-RestMethod -Uri "$apiBase/health" -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        throw "Host live API did not start on port $Port"
    }
    $serverProcessId = if ($server) {
        $server.Id
    }
    else {
        (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty OwningProcess)
    }

    Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/start" -TimeoutSec 20 | Out-Null
    $startedAt = Get-Date
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
        $live = Invoke-RestMethod -Uri "$apiBase/live" -TimeoutSec 10
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

    $final = Invoke-RestMethod -Uri "$apiBase/live" -TimeoutSec 10
    $stopped = Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/stop" -TimeoutSec 20
    Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/start" -TimeoutSec 20 | Out-Null
    $restarted = Invoke-RestMethod -Uri "$apiBase/live" -TimeoutSec 10
    Invoke-RestMethod -Method Post -Uri "$apiBase/telemetry/stop" -TimeoutSec 20 | Out-Null

    $sortedLatencies = @($apiLatencies | Sort-Object)
    $p95Index = [math]::Min($sortedLatencies.Count - 1, [math]::Floor($sortedLatencies.Count * 0.95))
    [pscustomobject]@{
        duration_seconds = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 2)
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
finally {
    if (-not $UseExistingServer -and $server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}
