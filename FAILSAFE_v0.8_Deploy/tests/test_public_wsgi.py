"""WSGI-level public-deploy smoke and boundary tests (no external dependencies)."""
import io
import json
import unittest
from wsgiref.validate import validator
from app import app

class PublicAppTests(unittest.TestCase):
    def request(self, method, path, obj=None, ctype='application/json', origin=None):
        data = b'' if obj is None else json.dumps(obj).encode('utf-8')
        captured = []
        env = {
            'REQUEST_METHOD': method, 'PATH_INFO': path, 'SERVER_NAME':'localhost',
            'SERVER_PORT':'8000', 'SERVER_PROTOCOL':'HTTP/1.1',
            'wsgi.version':(1,0), 'wsgi.url_scheme':'http', 'wsgi.input':io.BytesIO(data),
            'wsgi.errors':io.StringIO(), 'wsgi.multithread':False,
            'wsgi.multiprocess':False, 'wsgi.run_once':False,
            'HTTP_HOST':'localhost:8000','CONTENT_LENGTH':str(len(data)),
            'CONTENT_TYPE':ctype,
        }
        if origin:
            env['HTTP_ORIGIN'] = origin
        def start(status, headers): captured.append((status,dict(headers)))
        with self.subTest(method=method,path=path):
            res = b''.join(app(env,start))
        return captured[0][0],captured[0][1],res

    def test_public_home_and_lab(self):
        for path, text in [('/',b'FAILSAFE'),('/lab',b'Run live stress test')]:
            status, headers, body = self.request('GET',path)
            self.assertTrue(status.startswith('200'),status)
            self.assertIn(text,body)
            self.assertIn('DENY',headers['X-Frame-Options'])
    def test_server_sources_not_public(self):
        for path in ('/server.py','/app.py','/requirements.txt','/.gitignore','/tests/test_public_wsgi.py'):
            status, _, _ = self.request('GET', path)
            self.assertTrue(status.startswith('404'),path)
    def test_health(self):
        status, _, body=self.request('GET','/health')
        self.assertTrue(status.startswith('200'))
        self.assertTrue(json.loads(body)['synthetic_only'])
    def test_reject_oversized_and_cross_origin(self):
        status, _, _=self.request('POST','/api/simulate',{'patients':500},origin='https://stranger.test')
        self.assertTrue(status.startswith('403'))
        status,_,_=self.request('POST','/api/simulate',{'patients':500},ctype='text/plain')
        self.assertTrue(status.startswith('415'))
    def test_live_api_and_trace(self):
        config={'patients':50, 'validation_seeds':1}
        status,headers,body = self.request('POST','/api/simulate',config)
        self.assertTrue(status.startswith('200'),body[:100])
        result=json.loads(body)
        self.assertEqual(result['config']['patients'],50)
        self.assertIn('joint_optimizer',result)
        trace={'config':config, 'added_discharge_staff':0,'added_booking_staff':0}
        status, _, body = self.request('POST','/api/trace',trace)
        self.assertTrue(status.startswith('200'),body[:100])
        self.assertIn('queue',json.loads(body))

if __name__=='__main__':unittest.main()
