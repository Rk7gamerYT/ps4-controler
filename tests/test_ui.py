import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtGui import QColor
from app import Window, create_application
from profiles import Profiles, normalize


class FakeController:
    def __init__(self, identity):
        self.identity = identity
        self.name = identity
    def info(self):
        return ('DualShock 4', 'USB', '80%')
    def apply(self, rgb, brightness):
        pass


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def test_switching_and_reconnecting_restore_each_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Profiles(Path(directory) / 'settings.json')
            store.items['Azul'] = normalize({'color': '#0000ff'})
            store.items['Vermelho'] = normalize({'color': '#ff0000'})
            a, b = FakeController('sony-ds4:aa'), FakeController('sony-ds4:bb')
            store.bindings = {a.identity: 'Azul', b.identity: 'Vermelho'}
            with patch('app.Profiles', return_value=store), patch('app.discover', return_value=[a, b]), patch('app.Gamepad', side_effect=OSError('Sem acesso no teste')):
                window = Window()
                window.timer.stop()
                window.scan_timer.stop()
                self.assertEqual(window.color.name(), '#0000ff')
                window.selector.setCurrentIndex(1)
                self.assertEqual(window.color.name(), '#ff0000')
                window.color = QColor('#00ff00')
                window.save()
                window.selector.setCurrentIndex(0)
                self.assertEqual(window.color.name(), '#0000ff')
                with patch('app.discover', return_value=[a]):
                    window.refresh()
                with patch('app.discover', return_value=[a, b]):
                    window.refresh()
                window.selector.setCurrentIndex(1)
                self.assertEqual(window.color.name(), '#00ff00')
                self.assertEqual(Profiles(store.path).bindings[b.identity], 'Vermelho')
                window.close()
