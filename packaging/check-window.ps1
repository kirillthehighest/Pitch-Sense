# Opens the installed PitchSense on Windows and reads the text of its window through the WebView2
# debugging port until the Meciuri screen shows a league's matches, at most $Seconds seconds. It
# fails when the window says that the server does not answer, or never shows the matches, and then
# reports what it saw: whether the window and its server run and answer, and whether the debugging
# port does. Run after the silent install (.github/workflows/package.yml).
param(
    [string]$App = "$env:ProgramFiles\PitchSense\pitchsense.exe",
    [int]$Seconds = 120
)

function Read-PageText([string]$Address) {
    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    $none = [System.Threading.CancellationToken]::None
    $socket.ConnectAsync([Uri]$Address, $none).Wait()
    $question = '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.body.innerText","returnByValue":true}}'
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($question)
    $socket.SendAsync([ArraySegment[byte]]::new($bytes), "Text", $true, $none).Wait()
    $buffer = [byte[]]::new(4MB)
    $answer = [System.IO.MemoryStream]::new()
    do {
        $receive = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer), $none)
        $receive.Wait()
        $answer.Write($buffer, 0, $receive.Result.Count)
    } until ($receive.Result.EndOfMessage)
    $socket.Dispose()
    $json = [System.Text.Encoding]::UTF8.GetString($answer.ToArray()) | ConvertFrom-Json
    return [string]$json.result.result.value
}

function Show-State {
    $window = Get-Process -Name pitchsense -ErrorAction SilentlyContinue
    $server = Get-Process -Name pitchsense-server -ErrorAction SilentlyContinue
    Write-Output "window running: $([bool]$window); server processes: $(@($server).Count)"
    foreach ($process in @($server)) {
        $ports = Get-NetTCPConnection -State Listen -OwningProcess $process.Id -ErrorAction SilentlyContinue
        foreach ($port in @($ports)) {
            try {
                $status = Invoke-RestMethod "http://127.0.0.1:$($port.LocalPort)/api/status" -TimeoutSec 10
                Write-Output "server on port $($port.LocalPort): $($status | ConvertTo-Json -Compress)"
            } catch {
                Write-Output "server on port $($port.LocalPort) does not answer: $($_.Exception.Message)"
            }
        }
    }
    $debugging = Get-NetTCPConnection -State Listen -LocalPort 9222 -ErrorAction SilentlyContinue
    Write-Output "debugging port 9222 listening: $([bool]$debugging)"
}

$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = "--remote-debugging-port=9222"
$started = Get-Date
$window = Start-Process -FilePath $App -PassThru
$text = ""
$problems = [System.Collections.Generic.List[string]]::new()
try {
    while (((Get-Date) - $started).TotalSeconds -lt $Seconds) {
        Start-Sleep -Seconds 2
        try {
            $page = Invoke-RestMethod "http://127.0.0.1:9222/json" -TimeoutSec 5 |
                Where-Object { $_.type -eq "page" } | Select-Object -First 1
            if (-not $page) { $problems.Add("no page yet"); continue }
            $text = Read-PageText $page.webSocketDebuggerUrl
        } catch {
            $problems.Add($_.Exception.Message)
            continue
        }
        if ($text -match "Serverul nu") {
            Write-Output "The window says the server does not answer:"
            Write-Output $text
            Show-State
            exit 1
        }
        if ($text -match "Gazde" -and $text -match "Egal") {  # a match with its probabilities
            $elapsed = [Math]::Round(((Get-Date) - $started).TotalSeconds, 1)
            Write-Output "The window shows the matches $elapsed s after it was opened:"
            Write-Output $text.Substring(0, [Math]::Min(800, $text.Length))
            exit 0
        }
    }
    Write-Output "The window did not show the matches within $Seconds s. Its text: $text"
    Write-Output "What failed while reading it: $(($problems | Select-Object -Unique) -join ' | ')"
    Show-State
    exit 1
} finally {
    Stop-Process -Id $window.Id -Force -ErrorAction SilentlyContinue
}
