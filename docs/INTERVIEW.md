# Explain this project in interviews

## A truthful one minute introduction

“I built a read-only shopping lab with Storefront and two Payment versions on Kubernetes. I used Istio sidecars to demonstrate weighted canaries, header and path routing, cookie routing and traffic mirroring. I also compared a slow backend with a mesh timeout and used a controlled temporary failure to observe retries. I checked application logs and proxy configuration, and practised rolling traffic back to v1. This was a lab, not a production payment system.”

Only say you ran and observed each demonstration after you have completed it. If asked about production experience, describe your actual work separately.

## Questions and technical answers

### Why do you need both a VirtualService and a DestinationRule

The DestinationRule maps named subsets to version labels and can define connection policies. The VirtualService selects routes and weights for requests. Creating two Deployments or two subsets by itself does not define a 90/10 canary.

### How do you roll back a bad canary

Apply the all-v1 policy, wait for propagation and confirm fresh requests return v1. Preserve logs and investigate v2. Routing rollback does not undo database changes or stop every already-running request. In production I would also check error rate and latency, not just the version field.

### How is mirroring different from a canary

In a canary, a fraction of clients receives the new version's response. With mirroring the original route responds and an additional destination receives a copy; that copied response is discarded. Mirroring can still cause writes or load, so I used read-only endpoints.

### Can you route by user

For the lab I used an explicit header or cookie. The app forwards it to Payment and Envoy matches it. In a real system I would distinguish a caller-controlled value from a trusted identity claim. Routing to v2 does not grant permission to access protected operations.

### Where is the routing decision applied here

On the Storefront sidecar's outgoing HTTP call to the Payment Service. Inbound traffic at a gateway could have its own routing policy, but this lab uses port-forward only to open Storefront and does not test ingress routing.

### Why does the frontend forward the header

A header sent by the browser is not automatically copied into every new downstream request. Storefront explicitly forwards selected headers so its Payment call contains the routing signal. This is an application propagation concern, even though the routing decision belongs to the mesh.

### What happens if istiod is unavailable

Existing proxies can continue with their last configuration, while updates, new proxy configuration and certificate operations may be disrupted. I would inspect control-plane health and proxy synchronisation rather than assuming the whole application immediately stops.

### What is the difference between a timeout and a retry

A timeout limits how long the caller waits. A retry makes another attempt under specified conditions. The total budget and per-attempt budget limit how many attempts fit. Two retries can mean up to three backend attempts; the app counter makes this visible in this lab.

### Why not retry every failed payment

A payment may have succeeded before the response was lost. Repeating it can duplicate the effect. A real payment API needs idempotency and clear transaction semantics. A proxy cannot infer those semantics from an HTTP failure alone.

### Why did you use one v1 replica for retry testing

The demonstration failure counter is process-local and keyed by the request query. One v1 replica makes “fail twice then succeed” easy to reproduce. This is a teaching constraint, not a high-availability design. A distributed test would need shared state or a different failure model.

### How do you investigate a 503

First confirm ready Pods and Service endpoints, then match subset labels and destination hosts. Inspect `istioctl analyze`, proxy sync and actual routes/endpoints. Compare application logs and proxy response details. In this lab a 503 could be an intentional app failure, a fault abort or an unavailable upstream; the number alone does not identify the cause.

### Does mTLS authorise a caller

mTLS authenticates peers and encrypts the connection. An AuthorizationPolicy decides permissions. The optional policy lets the Storefront service account GET Payment. A different authenticated identity can still be denied.

### Why use a ConfigMap for source

It removes the image build and registry setup from the first learning session. The Dockerfile is supplied for the next step. In a deployed product I would package reviewed source in a versioned image and use an image promotion workflow.

## Evidence to collect for your portfolio

- A screenshot of three ready Deployments and injected proxies.
- A dashboard screenshot for the 90/10 sample, labelled with the actual sample size.
- Header and URL examples showing predictable v1/v2 selection.
- A client v1 response paired with a matching mirrored request in v2 logs.
- A timeout response and a retry response with attempt 3.
- A successful all-v1 rollback and your live-results.json report, if you run the live checks.

Use only your learning cluster. Avoid including credentials, internal hostnames or unrelated employer information.
