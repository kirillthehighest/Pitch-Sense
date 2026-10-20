# Starts the installed server as the window does (--with-window, its input and output piped),
# reads the port it announces and asks it at once, as the window's interface does. The 0.5.0
# server announced its port before it listened, and Windows refused that first question (the
# window's "Failed to fetch"). Run after the silent install (.github/workflows/package.yml).
param([string]$ServerPath = "$env:ProgramFiles\PitchSense\server\pitchsense-server.exe")

$start = [System.Diagnostics.ProcessStartInfo]::new($ServerPath, "--with-window")
$start.UseShellExecute = $false
$start.RedirectStandardInput = $true
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
$process = [System.Diagnostics.Process]::Start($start)
try {
    $first = $process.StandardOutput.ReadLine()
    if ($first -notmatch "^PITCHSENSE_PORT=(\d+)$") {
        Write-Output "The server's first line is not its port: $first"
        Write-Output $process.StandardError.ReadToEnd()
        exit 1
    }
    $port = $Matches[1]
    $leagues = Invoke-RestMethod "http://127.0.0.1:$port/api/leagues" -TimeoutSec 60
    Write-Output "Asked at once on port ${port}: $($leagues.Count) leagues"
    if ($leagues.Count -lt 1) { exit 1 }
    $deadline = (Get-Date).AddSeconds(60)
    do {
        $status = Invoke-RestMethod "http://127.0.0.1:$port/api/status" -TimeoutSec 60
        $ready = @($status.prepared.PSObject.Properties | Where-Object { $_.Value }).Count
        if ($ready -eq $leagues.Count) { break }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    $elapsed = [Math]::Round(((Get-Date) - $process.StartTime).TotalSeconds, 1)
    Write-Output "Leagues with their predictions ready: $ready of $($leagues.Count), $elapsed s after start"
    if ($ready -ne $leagues.Count) { exit 1 }
} finally {
    $process.StandardInput.Close()  # the server ends with its window
    if (-not $process.WaitForExit(15000)) { $process.Kill($true) }
}
