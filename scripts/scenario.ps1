param([Parameter(Mandatory=$true)][ValidateRange(1,11)][int]$Number)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$prefix = '{0:D2}-' -f $Number
$file = Get-ChildItem istio/scenarios -Filter "$prefix*.yaml" | Select-Object -First 1
if (!$file) { throw 'Scenario file not found.' }
& kubectl apply -f $file.FullName
if ($LASTEXITCODE -ne 0) { throw 'Scenario apply failed.' }
& istioctl analyze -n istio-kt
if ($LASTEXITCODE -ne 0) { throw 'Resolve the analysis findings before the demonstration.' }
Write-Host "Applied $($file.Name). Wait for propagation, then test."
Write-Host 'Rollback: .\scripts\scenario.ps1 -Number 1'
