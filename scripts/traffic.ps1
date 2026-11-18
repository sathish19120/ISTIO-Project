param(
    [ValidateRange(1,500)][int]$Count = 30,
    [ValidateSet('pay','preview','slow','flaky')][string]$Endpoint = 'pay',
    [ValidateSet('none','header','cookie','fault')][string]$Signal = 'none',
    [string]$BaseUrl = 'http://localhost:8080'
)
$ErrorActionPreference = 'Stop'
foreach ($i in 1..$Count) {
    $id = [guid]::NewGuid().ToString()
    $url = "$($BaseUrl.TrimEnd('/'))/api/$Endpoint"
    if ($Endpoint -eq 'flaky') { $url += "?key=$id" }
    $curlArgs = @('-sS', '--max-time', '12', '-H', "x-request-id: $id")
    switch ($Signal) {
        'header' { $curlArgs += @('-H', 'x-canary: yes') }
        'cookie' { $curlArgs += @('-H', 'Cookie: canary=yes') }
        'fault'  { $curlArgs += @('-H', 'x-demo-fault: yes') }
    }
    & curl.exe @curlArgs $url
    if ($LASTEXITCODE -ne 0) { throw "Request $i failed at the client transport layer." }
    Write-Host ''
}
