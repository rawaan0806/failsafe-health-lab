"""HTTP integration coverage for live and event-trace endpoints."""
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from server import Handler


class TraceHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.thread.join(timeout=2)
        cls.http.server_close()

    def send(self, path, body):
        conn = HTTPConnection('127.0.0.1', self.http.server_address[1], timeout=5)
        raw = json.dumps(body).encode()
        conn.request('POST', path, raw, {'Content-Type':'application/json'})
        response = conn.getresponse()
        result = response.status, json.loads(response.read())
        conn.close()
        return result

    def test_trace_http_response_and_api_consistency(self):
        body = {'config':{'patients':80,'seed':11},'added_discharge_staff':1,'added_booking_staff':0}
        status, payload=self.send('/api/trace',body)
        self.assertEqual(status,200)
        self.assertEqual(payload['version'],'0.6')
        self.assertEqual(len(payload['queue']['trace']),80)
        status, original=self.send('/api/simulate',{'patients':80,'seed':11,'validation_seeds':1})
        self.assertEqual(status,200)
        self.assertEqual(original['version'],'0.6')
        matching=next(p for p in original['joint_optimizer']['plans']
                      if p['id']=='baseline__d1_b0')
        self.assertEqual(matching['demo_mean_wait_minutes'],payload['queue']['mean_wait_minutes'])

    def test_trace_http_rejects_invalid_additions(self):
        bad={'config':{'patients':80},'added_discharge_staff':500,'added_booking_staff':0}
        status, response=self.send('/api/trace',bad)
        self.assertEqual(status,400)
        self.assertIn('error',response)

if __name__=='__main__':unittest.main()
