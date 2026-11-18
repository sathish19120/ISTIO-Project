"""Regenerate declarative learning examples. Requires PyYAML only for authoring."""
from pathlib import Path
from copy import deepcopy
import yaml
R=Path(__file__).parent
NS='istio-kt'
HOST=f'payment.{NS}.svc.cluster.local'
def write(path,docs):
    (R/path).write_text(yaml.safe_dump_all(docs,sort_keys=False),encoding='utf-8')
write('k8s/00-namespace.yaml',[dict(apiVersion='v1',kind='Namespace',metadata=dict(name=NS,labels={'istio-injection':'enabled'}))])
base=[]
for name in ['storefront','payment']:
    base.append(dict(apiVersion='v1',kind='ServiceAccount',metadata=dict(name=name,namespace=NS)))
    base.append(dict(apiVersion='v1',kind='Service',metadata=dict(name=name,namespace=NS),spec=dict(selector={'app':name},ports=[dict(name='http',port=8080,targetPort=8080)])))
for name,role,version in [('storefront','storefront','v1'),('payment-v1','payment','v1'),('payment-v2','payment','v2')]:
    labels={'app':role,'version':version}
    env=[dict(name='APP_ROLE',value=role),dict(name='APP_VERSION',value=version)]
    if role=='storefront':env.append(dict(name='PAYMENT_URL',value='http://payment:8080'))
    c=dict(name='app',image='python:3.12-alpine',command=['python','-u','/app/app.py'],env=env,ports=[dict(containerPort=8080)],
       volumeMounts=[dict(name='source',mountPath='/app',readOnly=True)],
       readinessProbe=dict(httpGet=dict(path='/readyz',port=8080),initialDelaySeconds=2,periodSeconds=3),
       livenessProbe=dict(httpGet=dict(path='/healthz',port=8080),initialDelaySeconds=5,periodSeconds=10),
       resources=dict(requests=dict(cpu='50m',memory='32Mi'),limits=dict(cpu='300m',memory='128Mi')),
       securityContext=dict(runAsNonRoot=True,runAsUser=10001,allowPrivilegeEscalation=False,capabilities=dict(drop=['ALL'])))
    base.append(dict(apiVersion='apps/v1',kind='Deployment',metadata=dict(name=name,namespace=NS),spec=dict(replicas=1,selector=dict(matchLabels=labels),template=dict(metadata=dict(labels=labels),spec=dict(serviceAccountName=role,containers=[c],volumes=[dict(name='source',configMap=dict(name='mesh-shop-source'))])))))
write('k8s/01-app.yaml',base)
write('istio/00-destination-rule.yaml',[dict(apiVersion='networking.istio.io/v1',kind='DestinationRule',metadata=dict(name='payment',namespace=NS),spec=dict(host=HOST,subsets=[dict(name=v,labels=dict(version=v)) for v in ['v1','v2']]))])
def dest(v,weight=None):
    d={'destination':{'host':HOST,'subset':v}}
    if weight is not None:d['weight']=weight
    return d
def route(v):return dict(route=[dest(v)],retries=dict(attempts=0))
def vs(name,http):
    write('istio/scenarios/'+name+'.yaml',[dict(apiVersion='networking.istio.io/v1',kind='VirtualService',metadata=dict(name='payment',namespace=NS),spec=dict(hosts=[HOST],http=http))])
vs('01-all-v1',[route('v1')]);vs('02-all-v2',[route('v2')])
vs('03-weighted',[dict(route=[dest('v1',90),dest('v2',10)],retries=dict(attempts=0))])
a=route('v2');a['match']=[dict(headers={'x-canary':dict(exact='yes')})];vs('04-header',[a,route('v1')])
a=route('v2');a['match']=[dict(uri=dict(prefix='/preview'))];vs('05-path',[a,route('v1')])
a=route('v2');a['match']=[dict(headers={'cookie':dict(regex='(^|.*; *)canary=yes(;.*|$)')})];vs('06-cookie',[a,route('v1')])
a=route('v1');a.update(mirror={'host':HOST,'subset':'v2'},mirrorPercentage=dict(value=100.0));vs('07-mirror',[a])
a={'match':[dict(headers={'x-demo-fault':dict(exact='yes')})], 'fault':dict(delay=dict(percentage=dict(value=100.0),fixedDelay='2s')),'route':[dest('v1')]};vs('08-delay',[a,route('v1')])
a=deepcopy(a);a['fault']=dict(abort=dict(percentage=dict(value=100.0),httpStatus=503));vs('09-abort',[a,route('v1')])
a=route('v1');a['timeout']='1s';vs('10-timeout',[a])
a=route('v1');a.update(timeout='6s',retries=dict(attempts=2,perTryTimeout='2s',retryOn='5xx'));vs('11-retry',[a])
write('istio/12-security-optional.yaml',[
 dict(apiVersion='security.istio.io/v1',kind='PeerAuthentication',metadata=dict(name='strict',namespace=NS),spec=dict(mtls=dict(mode='STRICT'))),
 dict(apiVersion='security.istio.io/v1',kind='AuthorizationPolicy',metadata=dict(name='storefront-to-payment',namespace=NS),spec=dict(selector=dict(matchLabels=dict(app='payment')),action='ALLOW',rules=[{'from':[{'source':{'principals':['cluster.local/ns/istio-kt/sa/storefront']}}],'to':[{'operation':{'methods':['GET']}}]}]))])
write('istio/13-access-logs-optional.yaml',[
 dict(apiVersion='telemetry.istio.io/v1',kind='Telemetry',metadata=dict(name='access-logs',namespace=NS),spec=dict(accessLogging=[dict(providers=[dict(name='envoy')])]))])
print('Generated Kubernetes resources and 11 mutually exclusive routing scenarios')
