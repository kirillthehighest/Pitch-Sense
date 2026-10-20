# Opens the installed PitchSense on Windows and checks that its window started the server, that
# the server answers with every league's predictions ready, and that it lets the window's origin
# (http://tauri.localhost) read its answers. The page itself cannot be read on the build machine:
# the WebView2 debugging port stays closed there (tried in October 2026). Run after the silent
# install (.github/workflows/package.yml).
param(
    [string]$App = "$env:ProgramFiles\PitchSense\pitchsense.exe",
    [int]$Seconds = 120,
    [string]$WindowOrigin = "http://tauri.localhost"
)

$started = Get-Date
$window = Start-Process -FilePath $App -PassThru
try {
    while (((Get-Date) - $started).TotalSeconds -lt $Seconds) {
        Start-Sleep -Seconds 1
        foreach ($candidate in @(Get-Process -Name pitchsense-server -ErrorAction SilentlyContinue)) {
            $listening = Get-NetTCPConnection -State Listen -OwningProcess $candidate.Id -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if (-not $listening) { continue }  # the worker process, which does not listen
            $port = $listening.LocalPort
            try {
                $answer = Invoke-WebRequest "http://127.0.0.1:$port/api/status" -Headers @{ Origin = $WindowOrigin } -TimeoutSec 10
            } catch {
                continue
            }
            $prepared = ($answer.Content | ConvertFrom-Json).prepared.PSObject.Properties
            $ready = @($prepared | Where-Object { $_.Value }).Count
            if ($ready -lt @($prepared).Count) { continue }
            $elapsed = [Math]::Round(((Get-Date) - $started).TotalSeconds, 1)
            $allowed = "$($answer.Headers['Access-Control-Allow-Origin'])"
            Write-Output "The window's server (port $port) has all $ready leagues ready $elapsed s after the window was opened."
            Write-Output "Access-Control-Allow-Origin for ${WindowOrigin}: $allowed"
            if ($allowed -ne $WindowOrigin) { exit 1 }
            exit 0
        }
    }
    $windowRunning = [bool](Get-Process -Id $window.Id -ErrorAction SilentlyContinue)
    Write-Output "Within $Seconds s the window's server did not answer with every league ready (window running: $windowRunning)."
    exit 1
} finally {
    Stop-Process -Id $window.Id -Force -ErrorAction SilentlyContinue  # its server ends with it
}
