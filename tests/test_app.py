"""Local HTTP tests. These do not claim to validate a live Istio mesh."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
R=Path(__file__).resolve().parents[1]
def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]
def request(url,headers=None):
    try:
        with urlopen(Request(url,headers=headers or {}),timeout=10) as r:
            return r.status,r.read(),r.headers
    except HTTPError as r:return r.code,r.read(),r.headers
class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processes=[];cls.logs=[];cls.urls={}
        try:
            for name,role,version in [('v1','payment','v1'),('v2','payment','v2'),('shop','storefront','v1')]:
                port=free_port();env={**os.environ,'APP_ROLE':role,'APP_VERSION':version,'PORT':str(port)}
                if role=='storefront':env['PAYMENT_URL']=cls.urls['v1']
                log=tempfile.TemporaryFile();cls.logs.append(log)
                proc=subprocess.Popen([sys.executable,str(R/'src/app.py')],env=env,stdout=log,stderr=log)
                cls.processes.append(proc);cls.urls[name]=f'http://127.0.0.1:{port}'
                for _ in range(100):
                    try:
                        if request(cls.urls[name]+'/healthz')[0]==200:break
                    except OSError:pass
                    time.sleep(.03)
                else:raise RuntimeError('App failed to start')
        except Exception:
            cls.tearDownClass();raise
    @classmethod
    def tearDownClass(cls):
        for p in cls.processes:p.terminate()
        for p in cls.processes:p.wait(timeout=5)
        for f in cls.logs:f.close()
    def test_two_versions(self):
        for v in ['v1','v2']:
            status,raw,_=request(self.urls[v]+'/pay')
            self.assertEqual(status,200);self.assertEqual(json.loads(raw)['version'],v)
    def test_storefront_forwards_request_id(self):
        status,raw,_=request(self.urls['shop']+'/api/pay',{'x-request-id':'local-test-id'})
        result=json.loads(raw)
        self.assertEqual(status,200);self.assertEqual(result['request_id'],'local-test-id')
        self.assertEqual(result['version'],'v1');self.assertIn('elapsed_ms',result)
    def test_routing_signals_reach_backend(self):
        status,raw,_=request(self.urls['shop']+'/api/pay',
                             {'x-canary':'yes','Cookie':'canary=yes'})
        body=json.loads(raw)
        self.assertEqual(status,200)
        self.assertEqual(body['received_canary'],'yes')
        self.assertEqual(body['received_cookie'],'canary=yes')
    def test_no_application_retries_and_query_preserved(self):
        url=self.urls['shop']+'/api/flaky?key=local-fixed-key'
        results=[(s,json.loads(b)) for s,b,_ in [request(url),request(url),request(url)]]
        self.assertEqual([s for s,b in results],[503,503,200])
        self.assertEqual([b['attempt'] for s,b in results],[1,2,3])
    def test_slow_backend(self):
        start=time.monotonic();status,_,_=request(self.urls['shop']+'/api/slow')
        self.assertEqual(status,200);self.assertGreaterEqual(time.monotonic()-start,2.9)
    def test_ui_and_unknown_endpoint(self):
        status,raw,headers=request(self.urls['shop']+'/')
        self.assertEqual(status,200);self.assertIn('text/html',headers['Content-Type'])
        self.assertIn(b'Send 30 requests',raw)
        self.assertEqual(request(self.urls['shop']+'/api/missing')[0],404)
if __name__=='__main__':unittest.main(verbosity=2)
