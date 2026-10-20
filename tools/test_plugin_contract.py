import copy
import json
from pathlib import Path
import unittest
from plugin_contract import validate_manifest


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((Path(__file__).resolve().parents[1] / 'kiosk-satellite-plugin.json').read_text(encoding='utf-8'))

    def test_current_manifest(self):
        validate_manifest(self.manifest)

    def test_missing_secret_default_is_rejected(self):
        secret = next(s for s in self.manifest['settings'] if s['type'] == 'secret')
        secret.pop('default')
        with self.assertRaisesRegex(ValueError, 'Missing default'):
            validate_manifest(self.manifest)

    def test_every_top_level_default_is_required(self):
        for index in range(len(self.manifest['settings'])):
            manifest = copy.deepcopy(self.manifest)
            manifest['settings'][index].pop('default')
            with self.assertRaisesRegex(ValueError, 'Missing default'):
                validate_manifest(manifest)

    def test_secret_must_not_be_published(self):
        next(s for s in self.manifest['settings'] if s['type'] == 'secret')['default'] = 'fake-secret'
        with self.assertRaisesRegex(ValueError, 'Secret default must be empty'):
            validate_manifest(self.manifest)


if __name__ == '__main__':
    unittest.main()
