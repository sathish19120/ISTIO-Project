# Validation record

Prepared on 18 November 2026.

## Checks actually run

| Check | Result |
|---|---|
| Python HTTP integration tests | 6 passed |
| YAML parsing and resource consistency | 17 files and 24 resources passed |
| Scenario destinations and weights | All 11 checked |
| Deployment selectors and source mounts | Passed |
| Python source and test compilation | Passed |
| Dashboard JavaScript syntax | Passed Node syntax check |
| Architecture image | Rendered and visually inspected |

The six app tests start real local HTTP processes and verify both version responses, Storefront forwarding, routing header and cookie propagation, preserved query keys with no application retries, the three-second slow endpoint, dashboard serving and unknown-endpoint handling. The raw local test result is included in `local-test-results.txt`.

## Checks not run here

This environment had no kubectl, Docker, PowerShell runtime or Kubernetes/Istio cluster. Images were not pulled, PowerShell scripts were not executed, and mesh policies were not verified against an API server or Envoy runtime. The UI's browser interactions were not exercised in a browser; its JavaScript passed syntax checking and its HTML was served in an HTTP test.

Expected traffic distributions, mirroring, injected faults, timeouts, retries and optional security outcomes are described as expected results. They become observations only after you run them on your cluster. The supplied live test automates requests, checks most scenario results, captures mirror evidence in logs and restores all-v1 routing afterward. It records weighted counts rather than requiring an exact 90/10 split.

## Repeat local checks

```powershell
python .\tests\test_app.py
```

Static YAML validation is an optional developer check requiring PyYAML:

```powershell
python -m pip install PyYAML
python .\tests\validate_manifests.py
```

The application itself has no pip package dependencies.

## Run the live checks on your cluster

After setup, confirm the UI works and keep the port-forward running. Then run:

```powershell
python .\tests\live_mesh.py
```

For an alternate local port:

```powershell
python .\tests\live_mesh.py --base-url http://localhost:8081
```

This script applies each routing scenario to the existing `istio-kt` namespace. It writes `live-results.json` in the project directory and attempts to restore scenario 1 even after a failed assertion. A failure is useful evidence: inspect its recorded result and the active proxy configuration. Timing thresholds are learning defaults and may need adjustment on an overloaded laptop. The script does not test the optional security or access-log resources.
