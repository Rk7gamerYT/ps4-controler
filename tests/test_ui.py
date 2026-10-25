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
    def battery_status(self):
        return 80, "Discharging"
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
                window.quitting = True
                window.close()

    def test_tray_uses_selected_battery_and_unknown_on_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Profiles(Path(directory) / 'settings.json')
            with patch('app.Profiles', return_value=store), patch('app.discover', return_value=[]):
                window = Window(True)
                window.timer.stop()
                window.scan_timer.stop()
                window.devices = [FakeController('test')]
                window.update_tray()
                self.assertIn('80%', window.tray.toolTip())
                window.devices = []
                window.update_tray()
                self.assertIn('Sem leitura', window.tray.toolTip())
                window.quitting = True
                window.close()

    def test_closing_hides_when_tray_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('app.Profiles', return_value=Profiles(Path(directory) / 'settings.json')):
                window = Window(True)
                window.show()
                with patch.object(window.tray, 'isVisible', return_value=True):
                    window.close()
                    self.assertFalse(window.isVisible())
                    self.assertTrue(window.timer.isActive())
                window.quitting = True
                window.close()
                self.assertFalse(window.timer.isActive())

    def test_duplicate_and_rename_keep_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Profiles(Path(directory) / 'settings.json')
            store.bindings = {'sony-ds4:aa': 'Padrão'}
            with patch('app.Profiles', return_value=store), patch('app.discover', return_value=[]), \
                    patch('app.QInputDialog.getText', return_value=('Jogos', True)):
                window = Window(True)
                window.timer.stop()
                window.scan_timer.stop()
                window.duplicate_profile()
                self.assertIn('Padrão (cópia)', store.items)
                window.change_profile('Padrão')
                window.rename_profile()
                self.assertIn('Jogos', store.items)
                self.assertEqual(store.bindings['sony-ds4:aa'], 'Jogos')
                self.assertEqual(store.active, 'Jogos')
                window.quitting = True
                window.close()
