import json
from pathlib import Path
import tempfile
import unittest
from profiles import Profiles, normalize


class ProfileTests(unittest.TestCase):
    def test_migrates_old_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text(json.dumps(dict(color='#ff0000', brightness=20, effect=1, speed=40)))
            store = Profiles(path)
            self.assertEqual(store.items['Padrão']['brightness'], 20)
            store.save()
            self.assertEqual(json.loads(path.read_text())['version'], 2)

    def test_independent_associations_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            store = Profiles(path)
            store.items['Azul'] = normalize({'color': '#0000ff'})
            store.items['Vermelho'] = normalize({'color': '#ff0000'})
            store.bindings = {'sony-ds4:aa': 'Azul', 'sony-ds4:bb': 'Vermelho'}
            store.save()
            loaded = Profiles(path)
            self.assertEqual(loaded.items[loaded.bindings['sony-ds4:aa']]['color'], '#0000ff')
            self.assertEqual(loaded.items[loaded.bindings['sony-ds4:bb']]['color'], '#ff0000')

    def test_rejects_bad_imports(self):
        for value in ([], None, {'brightness': 101}, {'color': '#zzzzzz'}, {'effect': -1}):
            with self.assertRaises(ValueError):
                normalize(value)
