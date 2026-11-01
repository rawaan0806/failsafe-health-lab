"""Unit and protocol tests for local live scenario customization."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from failsafe import TRAIT_FREQUENCIES, generate_patients
from server import Handler, calculate, parse_config


class LiveModelTests(unittest.TestCase):
    def test_all_zero_and_all_one_trait_rates(self):
        zero = generate_patients(100, 42, {k: 0 for k in TRAIT_FREQUENCIES})
        one = generate_patients(100, 42, {k: 1 for k in TRAIT_FREQUENCIES})
        self.assertTrue(all(not getattr(p, k) for p in zero for k in TRAIT_FREQUENCIES))
        self.assertTrue(all(getattr(p, k) for p in one for k in TRAIT_FREQUENCIES))

    def test_custom_rates_preserve_seed_reproducibility(self):
        rates = {'transport_barrier': .85, 'interpreter_needed': .75}
        self.assertEqual(generate_patients(160, 222, rates), generate_patients(160, 222, rates))
        original = generate_patients(160, 222)
        changed = generate_patients(160, 222, rates)
        self.assertNotEqual(original, changed)

    def test_invalid_custom_rate_raises(self):
        for settings in ({'transport_barrier': 1.01}, {'transport_barrier': -0.1},
                         {'transport_barrier': True}, {'bad_trait': .5}):
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    generate_patients(100, 42, settings)

    def test_input_validation(self):
        for config in ({'patients': 0}, {'patients': '500'}, {'patients': True},
                       {'budget': -1}, {'budget': 'bad'}, {'validation_seeds': 10},
                       {'trait_percentages': {'transport_barrier': 200}},
                       {'trait_percentages': {'transport_barrier': 'high'}},
                       {'trait_percentages': {'other_trait': 50}},
                       {'unexpected': 1}):
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    parse_config(config)

    def test_recomputed_after_changing_barriers(self):
        normal = calculate({'patients': 500, 'seed': 42})
        hard = calculate({'patients': 500, 'seed': 42,
                          'trait_percentages': {'transport_barrier': 100}})
        self.assertEqual(next(p for p in normal['result']['possible_plans'] if p['id'] == 'baseline')['demo']['fully_completed'], 219)
        self.assertNotEqual(next(p for p in normal['result']['possible_plans'] if p['id'] == 'baseline')['demo']['fully_completed'],
                            next(p for p in hard['result']['possible_plans'] if p['id'] == 'baseline')['demo']['fully_completed'])
        self.assertEqual(hard['config']['trait_percentages']['transport_barrier'], 100)
        self.assertEqual(len(hard['patient_records']['baseline']), 500)
        self.assertEqual(len(hard['result']['possible_plans']), 8)

    def test_cost_scales_with_number_of_patients(self):
        a = calculate({'patients': 100, 'budget': 1000, 'validation_seeds': 1})
        b = calculate({'patients': 200, 'budget': 1000, 'validation_seeds': 1})
        plan_id = 'medication_navigation'
        plans_a = {p['id']: p for p in a['result']['possible_plans']}
        plans_b = {p['id']: p for p in b['result']['possible_plans']}
        self.assertEqual(plans_b[plan_id]['cost_credits'], 2 * plans_a[plan_id]['cost_credits'])


class HttpProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.port = cls.server.server_port
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)

    def endpoint(self, path):
        return f'http://127.0.0.1:{self.port}{path}'

    def test_html_and_health(self):
        with urlopen(self.endpoint('/')) as response:
            self.assertIn(b'FAILSAFE', response.read())
        with urlopen(self.endpoint('/health')) as response:
            self.assertTrue(json.loads(response.read())['ok'])

    def test_live_post(self):
        req = Request(self.endpoint('/api/simulate'),
                      data=json.dumps({'patients': 80, 'seed': 7, 'budget': 35}).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
        self.assertEqual(result['config']['patients'], 80)
        self.assertEqual(len(result['patient_records']['baseline']), 80)

    def test_api_rejects_invalid_request(self):
        req = Request(self.endpoint('/api/simulate'),
                      data=json.dumps({'patients': 999999}).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req)
        self.assertEqual(ctx.exception.code, 400)


if __name__ == '__main__':
    unittest.main()
