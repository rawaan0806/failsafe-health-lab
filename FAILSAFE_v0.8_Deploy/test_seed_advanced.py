import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SeedPresentationTests(unittest.TestCase):
    def test_seed_is_optional_and_behind_advanced(self):
        page = (ROOT / 'outpatient.html').read_text(encoding='utf-8')
        marker = 'Advanced settings (optional)'
        self.assertIn(marker, page)
        advanced = page.split(marker, 1)[1].split('</details>', 1)[0]
        self.assertIn('name="seed"', advanced)
        self.assertNotIn('name="seed" type="number" min="0" max="1000000" value="42" required', advanced)

    def test_blank_seed_uses_reproducible_default(self):
        js = (ROOT / 'assets' / 'outpatient.js').read_text(encoding='utf-8')
        self.assertIn("el.name==='seed' && el.value.trim()==='' ? 42", js)


if __name__ == '__main__':
    unittest.main()
