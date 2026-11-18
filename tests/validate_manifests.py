"""Static consistency checks. Install PyYAML for this optional developer check."""
from pathlib import Path
import yaml
R=Path(__file__).resolve().parents[1]
files=list(R.glob('k8s/*.yaml'))+list(R.glob('istio/**/*.yaml'))
resources=[]
for file in files:
    for obj in yaml.safe_load_all(file.read_text()):
        assert obj['apiVersion'] and obj['kind'],file
        resources.append(obj)
scenarios=sorted((R/'istio/scenarios').glob('*.yaml'))
assert len(scenarios)==11
for file in scenarios:
    obj=yaml.safe_load(file.read_text())
    assert obj['metadata']['name']=='payment'
    assert obj['metadata']['namespace']=='istio-kt'
    for rule in obj['spec']['http']:
        routes=rule['route']
        if any('weight' in d for d in routes):assert sum(d.get('weight',0) for d in routes)==100
        for d in routes:
            assert d['destination']['subset'] in ['v1','v2']
            assert d['destination']['host']=='payment.istio-kt.svc.cluster.local'
        if 'fault' in rule:assert 'retries' not in rule and 'timeout' not in rule
apps=[x for x in resources if x['kind']=='Deployment']
assert len(apps)==3
for app in apps:
    spec=app['spec'];assert spec['selector']['matchLabels']==spec['template']['metadata']['labels']
    assert spec['template']['spec']['volumes'][0]['configMap']['name']=='mesh-shop-source'
print(f'PASS: {len(files)} YAML files; {len(resources)} resources; 11 scenario policies; selectors and weights checked')
