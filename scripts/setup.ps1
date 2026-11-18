$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Set-Location (Split-Path $PSScriptRoot -Parent)
function K {
    & kubectl @args
    if ($LASTEXITCODE -ne 0) { throw "kubectl failed: $args" }
}
Write-Host 'Deploying the learning app to the current cluster context:'
K config current-context
K get nodes
K rollout status deployment/istiod -n istio-system --timeout=60s
K apply -f k8s/00-namespace.yaml
$source = & kubectl create configmap mesh-shop-source -n istio-kt --from-file=src/app.py --from-file=src/index.html --dry-run=client -o yaml
if ($LASTEXITCODE -ne 0) { throw 'Could not generate the source ConfigMap.' }
$source | kubectl apply -f -
if ($LASTEXITCODE -ne 0) { throw 'Could not apply the source ConfigMap.' }
K apply -f k8s/01-app.yaml
K apply -f istio/00-destination-rule.yaml
K apply -f istio/scenarios/01-all-v1.yaml
# Restart also loads any changed ConfigMap source during later reruns.
K rollout restart deployment -n istio-kt
foreach ($name in @('storefront', 'payment-v1', 'payment-v2')) {
    K rollout status "deployment/$name" -n istio-kt --timeout=180s
}
K get pods -n istio-kt
$podJson = & kubectl get pods -n istio-kt -o json
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Pods.' }
foreach ($pod in ($podJson | ConvertFrom-Json).items) {
    $containers = @($pod.spec.containers) + @($pod.spec.initContainers)
    if (!($containers | Where-Object { $_.name -eq 'istio-proxy' })) {
        throw "No Istio proxy in $($pod.metadata.name). Fix injection and restart workloads."
    }
}
Write-Host 'Confirm each Pod contains istio-proxy. Then run in a new terminal:'
Write-Host 'kubectl port-forward -n istio-kt svc/storefront 8080:8080'
Write-Host 'Open http://localhost:8080 and read docs/KT_RUNBOOK.md.'
