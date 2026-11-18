# Diagnose a failed demonstration

Work from workload health to network endpoints to mesh configuration. An HTTP status is a clue, not a diagnosis.

```powershell
kubectl get pods,svc -n istio-kt
kubectl get endpointslices -n istio-kt
kubectl describe deployment payment-v1 -n istio-kt
kubectl get virtualservice,destinationrule -n istio-kt -o yaml
istioctl analyze -n istio-kt
istioctl proxy-status
```

For a specific Pod, copy its actual name from `kubectl get pods`:

```powershell
istioctl proxy-config routes STOREFRONT_POD_NAME -n istio-kt
istioctl proxy-config clusters STOREFRONT_POD_NAME -n istio-kt
istioctl proxy-config endpoints STOREFRONT_POD_NAME -n istio-kt
kubectl logs deployment/storefront -n istio-kt -c app --tail=30
kubectl logs deployment/payment-v1 -n istio-kt -c app --tail=30
kubectl logs deployment/payment-v2 -n istio-kt -c app --tail=30
```

Replace `STOREFRONT_POD_NAME` with the complete running Pod name. These are not commands to paste with the placeholder unchanged.

| Symptom | Inspect | Likely issue |
|---|---|---|
| Pod Pending | Pod events and node capacity | Resource shortage |
| ImagePullBackOff | Pod events | Registry access or image availability |
| Python cannot find app.py | ConfigMap and volume | Source files not loaded |
| UI cannot open | Port-forward terminal | Local port occupied or Pod restarted |
| Always mixed versions in all-v1 | Proxy injection and route host | App traffic bypassing mesh or wrong host |
| Header route remains v1 | UI signal, rule order and forwarded header | Missing match or catch-all first |
| v2 subset gets 503 | Pod version labels and endpoints | No ready subset endpoints |
| Mirror has no extra UI result | v2 app logs | Expected; mirrored response is discarded |
| Retry gets 503 | Active rule and fresh key | Wrong scenario, propagation or retry budget |
| Retry succeeds without retry rule | Fresh key and baseline retries 0 | Old key reused or unexpected policy |
| 403 after optional security | Service account and ALLOW scope | Caller is not Storefront |
| Timeout becomes frontend 502 after 8 seconds | Outbound route and proxy presence | Mesh timeout did not take effect |

## Optional proxy access logs

Application logs are enabled by the demo itself. Proxy access logs are a separate mechanism. If the installation has the standard `envoy` access-log provider:

```powershell
kubectl apply -f .\istio\13-access-logs-optional.yaml
kubectl get pods -n istio-kt
kubectl logs STOREFRONT_POD_NAME -n istio-kt -c istio-proxy --tail=30
```

Generate traffic before inspecting logs. If the provider or telemetry configuration differs, consult the installed release documentation. Prometheus, Kiali, Grafana and tracing backends are not installed by this project. Full distributed tracing also requires trace-context propagation and a configured backend.

## Reset the demo

Apply `istio/scenarios/01-all-v1.yaml`; clear the UI counters, choose Standard payment and None, then send a fresh request. Remove the optional security policy only if you applied it. If source changed, rerun setup to update the ConfigMap and restart the lab workloads.

## Sources

Official documentation consulted on 18 November 2026. Latest URLs may change; use the documentation matching your installed version.

- Architecture: https://istio.io/latest/docs/ops/deployment/architecture/
- Traffic management: https://istio.io/latest/docs/concepts/traffic-management/
- VirtualService API: https://istio.io/latest/docs/reference/config/networking/virtual-service/
- DestinationRule API: https://istio.io/latest/docs/reference/config/networking/destination-rule/
- Request routing: https://istio.io/latest/docs/tasks/traffic-management/request-routing/
- Mirroring: https://istio.io/latest/docs/tasks/traffic-management/mirroring/
- Fault injection: https://istio.io/latest/docs/tasks/traffic-management/fault-injection/
- Timeouts: https://istio.io/latest/docs/tasks/traffic-management/request-timeouts/
- Security: https://istio.io/latest/docs/concepts/security/
- Proxy diagnostics: https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/
