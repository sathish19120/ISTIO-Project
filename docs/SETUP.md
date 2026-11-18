# Setup on Windows

## Prerequisites

Use a disposable local cluster such as Docker Desktop Kubernetes or Minikube. Have `kubectl`, `istioctl` and `curl.exe` on PATH. Suggested local cluster allocation is 4 CPUs and 8 GB RAM; actual resource needs vary. The cluster must be able to pull `python:3.12-alpine` and Istio images.

Obtain Istio from the official installation guide and choose a release compatible with your Kubernetes version. This kit uses stable `networking.istio.io/v1`, `security.istio.io/v1` and `telemetry.istio.io/v1` APIs with default sidecar injection. Do not use ambient enrollment for this namespace.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes
istioctl version --remote=false
istioctl x precheck
```

Confirm the context is your intended learning cluster. The nodes must be Ready. If the cluster or a tool is missing, install it before running this project.

If Istio is not installed in this disposable cluster:

```powershell
istioctl install --set profile=default -y
kubectl rollout status deployment/istiod -n istio-system --timeout=180s
```

The default profile may install an ingress gateway, but this kit does not use it. Do not reinstall or change an existing company mesh. The setup script assumes the default `istiod` deployment and injection label, not a revision-based installation.

## Deploy the application

Extract the ZIP. Open PowerShell inside the `Istio_KT_Lab` folder.

```powershell
.\scripts\setup.ps1
```

If PowerShell blocks scripts under your machine policy, use the manual commands below; do not change a company execution policy. The script creates namespace `istio-kt`, a source ConfigMap and the lab resources. On reruns it restarts the lab Deployments to load changed source. Use an otherwise unused `istio-kt` namespace.

```powershell
kubectl apply -f .\k8s\00-namespace.yaml
kubectl create configmap mesh-shop-source -n istio-kt --from-file=src/app.py --from-file=src/index.html --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f .\k8s\01-app.yaml
kubectl apply -f .\istio\00-destination-rule.yaml
kubectl apply -f .\istio\scenarios\01-all-v1.yaml
kubectl rollout status deployment/storefront -n istio-kt --timeout=180s
kubectl rollout status deployment/payment-v1 -n istio-kt --timeout=180s
kubectl rollout status deployment/payment-v2 -n istio-kt --timeout=180s
kubectl get pods -n istio-kt
istioctl proxy-status
```

Normally app Pods show two ready containers: `app` and `istio-proxy`. With native sidecars, inspect both containers and initContainers. If there is no proxy, stop: requests may work but Istio routing will not be demonstrated. Namespace labels affect new Pods; use a rollout restart after fixing injection.

## Open the UI

Keep this command running in a separate PowerShell window:

```powershell
kubectl port-forward -n istio-kt svc/storefront 8080:8080
```

Open **http://localhost:8080**. If port 8080 is occupied, use `8081:8080` and open port 8081. Pass `-BaseUrl http://localhost:8081` to `traffic.ps1` if using the alternate port. If a storefront Pod restarts, restart the port-forward.

## Optional image build

The default deployment uses a source ConfigMap for a fast first demo. For an image-build exercise:

```powershell
docker build -t mesh-shop:demo .
```

Load this image into your cluster or push it to a reachable registry. For example, Minikube can load it using `minikube image load mesh-shop:demo`. Update all three app containers to that image and remove the `/app` ConfigMap mount and source volume from their templates. Otherwise the mount would hide files packaged in the image. Keep the role and version environment variables.

## Local app-only practice

In separate terminals, run Payment and Storefront with Python 3.12 or newer:

```powershell
$env:APP_ROLE='payment'; $env:APP_VERSION='v1'; $env:PORT='8081'
python .\src\app.py
```

```powershell
$env:APP_ROLE='storefront'; $env:PORT='8080'
$env:PAYMENT_URL='http://localhost:8081'
python .\src\app.py
```

This opens the dashboard and tests the app only. It has no mesh, no weighted routing and no mesh retries.

## Clean up

Stop port-forward with Ctrl+C. Then delete only the dedicated lab namespace:

```powershell
kubectl delete namespace istio-kt
```

This removes all resources in that namespace. It leaves the Istio installation in place. No cloud cluster or billable infrastructure is created by this kit.

Official setup: https://istio.io/latest/docs/setup/getting-started/
