# KT demonstration runbook

Plan a 35–40 minute recording after setup. Rehearse once before recording. Use the dashboard for visible results and keep YAML open beside it. Increase both terminal and editor font sizes.

For every scenario: predict the result, apply one file, allow configuration to propagate, send requests, explain the evidence, then state the use case. The UI cannot detect which scenario is installed; your applied YAML is the source of truth.

Commands below run from the project directory in PowerShell. The scenario helper invokes `istioctl analyze`. You can replace it with `kubectl apply -f <exact file>` when scripts are blocked. Clear browser counters between scenarios and choose **Standard payment** plus **None** unless instructed otherwise.

## 1 Baseline and architecture

```powershell
.\scripts\scenario.ps1 -Number 1
.\scripts\traffic.ps1 -Count 3
```

Expected: HTTP 200 and `version: v1` for every response after propagation. Show the DestinationRule and explain that labels define the two subsets. Show `kubectl get pods -n istio-kt` to identify the proxies. Say: “The browser reaches Storefront. The mesh call we are inspecting is Storefront to Payment.”

## 2 Switch entirely to version two

```powershell
.\scripts\scenario.ps1 -Number 2
.\scripts\traffic.ps1 -Count 3
```

Expected: v2. Both versions remain deployed. Say: “We changed a route, not the number of replicas.” Roll back by applying scenario 1; verify v1 returns.

## 3 Canary with weighted traffic

```powershell
.\scripts\scenario.ps1 -Number 3
.\scripts\traffic.ps1 -Count 100
```

Or click **Send 30 requests** in the dashboard. Expect mostly v1 and some v2. The exact ratio varies; ten percent is not a rule that every tenth request goes to v2. For a stronger sample use 100 requests. A small batch can contain no v2 responses.

Teaching example: “In a rollout we might start at ten percent, observe service-level error and latency targets, and increase only if the evidence supports it. A real rollback threshold must be defined before release.” The UI counters alone do not measure production health.

## 4 Header routing

```powershell
.\scripts\scenario.ps1 -Number 4
.\scripts\traffic.ps1 -Count 1 -Signal none
.\scripts\traffic.ps1 -Count 1 -Signal header
```

Expected: ordinary request v1; `x-canary: yes` request v2. In the UI select the matching request signal. A tester can try the next version without moving all traffic. A client-supplied header is not an authorisation boundary.

## 5 URL path routing

```powershell
.\scripts\scenario.ps1 -Number 5
.\scripts\traffic.ps1 -Count 1 -Endpoint pay
.\scripts\traffic.ps1 -Count 1 -Endpoint preview
```

Expected: `/api/pay` returns v1 and `/api/preview` returns v2. Storefront removes `/api` when forwarding, so the mesh sees `/pay` or `/preview`. Explain that the URI match is evaluated on the outgoing Payment request. No rewrite rule is used here.

## 6 Cookie routing

```powershell
.\scripts\scenario.ps1 -Number 6
.\scripts\traffic.ps1 -Count 1 -Signal none
.\scripts\traffic.ps1 -Count 1 -Signal cookie
```

Expected: no cookie gives v1; `Cookie: canary=yes` gives v2. The dashboard sets and clears this demo cookie on each request according to its selection. This is a simple user-cohort example, not a complete sticky-session implementation or a secure entitlement check.

## 7 Mirror traffic

```powershell
.\scripts\scenario.ps1 -Number 7
.\scripts\traffic.ps1 -Count 3
kubectl logs deployment/payment-v1 -n istio-kt -c app --tail=15
kubectl logs deployment/payment-v2 -n istio-kt -c app --tail=15
```

Expected: client responses say v1, while v2 application logs show copied requests. Mirrored responses are discarded. Show timestamps/request IDs to distinguish new traffic from earlier exercises. Mirrored traffic can have an authority ending in `-shadow`; this application does not restrict Host values.

Say: “Canary routing chooses which version answers the client. Mirroring copies the request while the original version still answers.” Mirrored writes can produce side effects; this app uses read-only demonstration endpoints.

## 8 Inject delay

```powershell
.\scripts\scenario.ps1 -Number 8
.\scripts\traffic.ps1 -Count 1 -Signal none
.\scripts\traffic.ps1 -Count 1 -Signal fault
```

Expected: the matching request still returns v1/200 but takes approximately two extra seconds. In the UI choose **Standard payment** and **Header x-demo-fault**. The delay is introduced by the mesh before the backend; it is not a slow app response. Do not combine this scenario with the timeout scenario when teaching the distinction.

## 9 Inject an abort

```powershell
.\scripts\scenario.ps1 -Number 9
.\scripts\traffic.ps1 -Count 1 -Signal fault
```

Expected: HTTP 503 and usually an upstream body such as `fault filter abort`. There may be no Payment version because the proxy aborted the request. Storefront wraps non-JSON upstream bodies in JSON for display. An ordinary request without the fault header should still return 200/v1.

## 10 Enforce a timeout

First show that the app is genuinely slow without a mesh timeout:

```powershell
.\scripts\scenario.ps1 -Number 1
.\scripts\traffic.ps1 -Count 1 -Endpoint slow
.\scripts\scenario.ps1 -Number 10
.\scripts\traffic.ps1 -Count 1 -Endpoint slow
```

Expected: baseline `/slow` returns 200 after approximately three seconds. Scenario 10 returns a proxy timeout, normally HTTP 504, at approximately one second plus overhead. The app may continue working after the caller has stopped waiting. Delay injection and request timeouts are different mechanisms. Timing varies with machine and cluster load.

## 11 Retry a temporary failure

```powershell
.\scripts\scenario.ps1 -Number 1
.\scripts\traffic.ps1 -Count 1 -Endpoint flaky
.\scripts\scenario.ps1 -Number 11
.\scripts\traffic.ps1 -Count 1 -Endpoint flaky
kubectl logs deployment/payment-v1 -n istio-kt -c app --tail=15
```

Expected: baseline returns 503 with `attempt: 1`. With retries the client normally receives 200, version v1 and `attempt: 3`. Logs show the first two 503 responses and a successful third backend attempt for the same key/request. Two configured retries permit up to three total attempts, subject to the time budget.

The helper and UI generate a fresh query key for each user request. For each key the backend fails twice, then succeeds. Keep Payment v1 at one replica for this deterministic demonstration; its counter is process-local. If you reuse a key, later requests may already be past the first two failures. The application makes only one upstream call per incoming request; Envoy supplies the extra attempts.

This retry rule is for a read-only GET demo. Retrying a real money movement requires application-level idempotency and careful failure semantics.

## Finish and roll back

```powershell
.\scripts\scenario.ps1 -Number 1
.\scripts\traffic.ps1 -Count 1
```

Expected: normal calls are back on v1. Do not delete application Pods to demonstrate routing rollback. Finish the video by asking viewers to explain why a DestinationRule by itself does not cause a 90/10 split.

## Optional security demonstration

```powershell
kubectl apply -f .\istio\12-security-optional.yaml
.\scripts\traffic.ps1 -Count 1
```

Expected: normal Storefront calls still work. The Payment ALLOW policy permits only the Storefront service account using GET. It assumes the default `cluster.local` trust domain. STRICT mTLS requires encrypted peer authentication on incoming mesh traffic. To prove a denial, run a separate client with a different service account and call Payment through its sidecar; expect a 403. A plaintext client instead tests transport rejection and may receive a connection error rather than a 403. Do not use `kubectl exec` into the Storefront app as an unauthorised identity: it shares the allowed Storefront identity.

Remove the optional security resources after the exercise:

```powershell
kubectl delete -f .\istio\12-security-optional.yaml
```

## Recording outline

| Minutes | Show | Explain |
|---|---|---|
| 0–5 | Architecture and ready Pods | Control plane versus data plane |
| 5–9 | Baseline and full switch | Routing versus deploying versions |
| 9–14 | Weighted split | Canary rollout and rollback |
| 14–20 | Header, URL and cookie | Ordered matches and test cohorts |
| 20–24 | Mirroring and application logs | Copies versus client responses |
| 24–30 | Delay, abort and timeout | Failure testing versus resilience |
| 30–35 | Retry and attempt number | Time budgets and idempotency |
| 35–40 | Diagnosis and questions | Evidence and limits of the lab |

Official explanations: request routing, mirroring and fault injection at https://istio.io/latest/docs/tasks/traffic-management/ . Exact fields are documented at https://istio.io/latest/docs/reference/config/networking/virtual-service/ .

### Reproduce the authenticated caller denial

While the optional security policy is applied, create a sidecar-injected client with the default service account:

```powershell
kubectl apply -f .\istio\14-untrusted-client-optional.yaml
kubectl wait --for=condition=Ready pod/untrusted -n istio-kt --timeout=180s
kubectl exec -n istio-kt untrusted -c client -- python -c "import http.client; c=http.client.HTTPConnection('payment',8080); c.request('GET','/pay'); r=c.getresponse(); print(r.status, r.read().decode())"
```

Expected: `403 RBAC: access denied`. The client participates in mTLS but its service account is not the allowed Storefront identity. This demonstrates authorisation denial separately from transport encryption. If you already removed the security file, reapply it before running this check.

```powershell
kubectl delete -f .\istio\14-untrusted-client-optional.yaml
kubectl delete -f .\istio\12-security-optional.yaml
```

Delete only files you applied. A NotFound response during this optional cleanup means that resource was already absent.
