"""Homepage, static assets and live lab route regression tests."""
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from server import Handler


class WebsiteRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)
        cls.server.server_close()

    def get(self, path):
        connection = HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=5)
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read()
        status, content_type = response.status, response.getheader('Content-Type')
        connection.close()
        return status, content_type, raw

    def test_home_is_a_separate_page(self):
        status, content_type, raw = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn('text/html',content_type)
        self.assertIn(b'Find the failure points',raw)
        self.assertIn(b'Launch interactive demo',raw)

    def test_lab_is_same_original_simulator(self):
        status, content_type, raw = self.get('/lab.html')
        self.assertEqual(status, 200)
        self.assertIn(b'Run live stress test', raw)
        self.assertIn(b'/api/trace', raw)
        self.assertIn(b'index.html',raw)

    def test_static_assets_are_served(self):
        for path, expected in [('/assets/styles.css','text/css'),('/assets/home.js','text/javascript'),('/assets/favicon.svg','image/svg+xml'),('/assets/simulation-screenshot.webp','image/webp')]:
            status, content_type, raw = self.get(path)
            self.assertEqual(status,200,path)
            self.assertIn(expected,content_type)
            self.assertTrue(len(raw)>100)

    def test_unlisted_paths_are_not_accessible(self):
        for path in ['/../server.py','/server.py','/assets/../server.py','/assets/unknown.js']:
            status, _, raw = self.get(path)
            self.assertEqual(status,404,path)
            self.assertIn(b'Not found',raw)

    def test_health_still_responds(self):
        status, _, raw=self.get('/health')
        self.assertEqual(status,200)
        self.assertTrue(json.loads(raw)['ok'])

if __name__=='__main__':unittest.main()
