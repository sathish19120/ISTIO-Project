"""Opt-in live mesh checks. Applies scenario policies and restores scenario 1.
Run after setup and port-forward: python tests/live_mesh.py
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import time
import uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
R=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',default='http://localhost:8080')
args=parser.parse_args();BASE=args.base_url.rstrip('/')
results=[]
def kubectl(*parts):
    return subprocess.check_output(['kubectl',*parts],text=True)
def call(endpoint='pay',headers=None):
    headers=dict(headers or {});headers['x-request-id']=str(uuid.uuid4())
    if endpoint=='flaky':endpoint+='?key='+str(uuid.uuid4())
    req=Request(BASE+'/api/'+endpoint,headers=headers)
    try:
        with urlopen(req,timeout=12) as r:return r.status,json.loads(r.read())
    except HTTPError as r:return r.code,json.loads(r.read())
def apply(n):
    path=next((R/'istio/scenarios').glob(f'{n:02}-*.yaml'))
    print(kubectl('apply','-f',str(path)).strip())
def until(label,predicate,endpoint='pay',headers=None):
    deadline=time.monotonic()+25;last=None
    while time.monotonic()<deadline:
        try:
            last=call(endpoint,headers)
            if predicate(*last):
                results.append({'test':label,'status':'PASS','response':last[1]})
                print('PASS:',label);return last
        except (OSError,ValueError,URLError) as exc:last=str(exc)
        time.sleep(.5)
    raise AssertionError(f'{label}: last result {last}')
def version(v):return lambda status,body:status==200 and body.get('version')==v

def run():
    print('Current context:',kubectl('config','current-context').strip())
    kubectl('get','deployment/storefront','-n','istio-kt')
    apply(1);until('all v1',version('v1'))
    apply(2);until('all v2',version('v2'))
    apply(3)
    # Wait until v1 is observable again, then sample rather than assert an exact ratio.
    until('weighted policy becomes observable',version('v1'))
    counts=Counter()
    for _ in range(100):
        status,body=call();assert status==200,(status,body)
        assert body.get('version') in ('v1','v2'),body
        counts[body['version']]+=1
    print('Weighted sample:',dict(counts))
    results.append({'test':'weighted sample','status':'OBSERVED','counts':dict(counts)})
    if not counts['v2']:print('No v2 in this sample: repeat and inspect active proxy routes.')
    apply(4);until('header selects v2',version('v2'),headers={'x-canary':'yes'})
    until('header fallback v1',version('v1'))
    apply(5);until('preview path selects v2',version('v2'),'preview')
    until('path fallback v1',version('v1'))
    apply(6);until('cookie selects v2',version('v2'),headers={'Cookie':'canary=yes'})
    until('cookie fallback v1',version('v1'))
    apply(7)
    deadline=time.monotonic()+25
    while True:
        status,body=call();assert version('v1')(status,body),body
        time.sleep(.2)
        lines=kubectl('logs','deployment/payment-v2','-n','istio-kt','-c','app','--tail=100')
        seen=[]
        for line in lines.splitlines():
            try:seen.append(json.loads(line))
            except ValueError:pass
        if any(x.get('event')=='payment' and x.get('request_id')==body['request_id'] for x in seen):break
        if time.monotonic()>deadline:raise AssertionError('Mirrored request not found in v2 logs')
    results.append({'test':'mirror observed in v2 logs','status':'PASS'})
    print('PASS: mirror observed in v2 logs')
    apply(8);until('injected delay',lambda s,b:s==200 and b.get('elapsed_ms',0)>=1800,headers={'x-demo-fault':'yes'})
    apply(9);until('injected abort',lambda s,b:s==503 and 'fault' in b.get('upstream_body',''),headers={'x-demo-fault':'yes'})
    apply(1);until('slow backend without timeout',lambda s,b:s==200 and b.get('elapsed_ms',0)>=2900,'slow')
    apply(10);until('mesh timeout',lambda s,b:s==504 and b.get('elapsed_ms',99999)<2800,'slow')
    apply(1);until('baseline no retry',lambda s,b:s==503 and b.get('attempt')==1,'flaky')
    apply(11);until('mesh retries twice',lambda s,b:s==200 and b.get('attempt')==3,'flaky')

try:
    run()
except Exception as exc:
    results.append({'test':'execution','status':'FAIL','error':str(exc)})
    raise
finally:
    try:apply(1);print('Restored all-v1 policy.')
    finally:
        (R/'live-results.json').write_text(json.dumps(results,indent=2))
        print('Wrote live-results.json. Expected mesh results become verified only after this run succeeds.')
