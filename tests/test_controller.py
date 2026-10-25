from pathlib import Path
import tempfile
import unittest
from controller import Lightbar, discover


class BackendTests(unittest.TestCase):
    def test_channels_follow_kernel_order_and_scale(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'multi_index').write_text('blue red green')
            (p / 'max_brightness').write_text('100')
            Lightbar(p).apply((255, 0, 128), 0.5)
            self.assertEqual((p / 'multi_intensity').read_text(), '50 100 0\n')
            self.assertEqual((p / 'brightness').read_text(), '50\n')

    def test_separate_channels_discovery_and_brightness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hid = root / 'hid'
            hid.mkdir()
            (hid / 'uevent').write_text('HID_ID=0005:0000054C:000005C4\n')
            leds = hid / 'leds'
            leds.mkdir()
            for color in ('red', 'green', 'blue', 'global'):
                led = leds / ('input42:' + color)
                led.mkdir()
                (led / 'brightness').write_text('0')
                (led / 'max_brightness').write_text('1' if color == 'global' else '255')
                (root / led.name).symlink_to(led, target_is_directory=True)
            found = discover(root)
            self.assertEqual(len(found), 1)
            found[0].apply((200, 100, 50), 0.5)
            self.assertEqual((leds / 'input42:red/brightness').read_text(), '100\n')
            self.assertEqual((leds / 'input42:green/brightness').read_text(), '50\n')
            self.assertEqual((leds / 'input42:blue/brightness').read_text(), '25\n')
            self.assertEqual((leds / 'input42:global/brightness').read_text(), '1\n')
            found[0].apply((200, 100, 50), 0)
            self.assertEqual((leds / 'input42:global/brightness').read_text(), '0\n')

    def test_serial_identity_is_independent_of_port_and_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            identities = []
            for bus in ('0003', '0005'):
                root = Path(directory) / bus
                root.mkdir()
                (root / 'uevent').write_text(f'HID_ID={bus}:0000054C:000009CC\nHID_UNIQ=AA:BB:CC:DD:EE:FF\n')
                led = root / 'led'
                led.mkdir()
                (led / 'multi_index').write_text('red green blue')
                (led / 'max_brightness').write_text('255')
                identities.append(Lightbar(led).identity)
            self.assertEqual(identities, ['sony-ds4:aa:bb:cc:dd:ee:ff'] * 2)

    def test_only_sony_ds4_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, vendor, product in [('ds4', '054C', '09CC'), ('ds5', '054C', '0CE6'), ('other', '1234', '09CC')]:
                device = root / name
                device.mkdir()
                (device / 'uevent').write_text(f'HID_ID=0003:0000{vendor}:0000{product}\n')
                led = device / f'{name}:rgb:indicator'
                led.mkdir()
                (led / 'multi_index').write_text('red green blue')
                (led / 'max_brightness').write_text('255')
                (root / led.name).symlink_to(led, target_is_directory=True)
            self.assertEqual([d.name for d in discover(root)], ['ds4:rgb:indicator'])


if __name__ == '__main__':
    unittest.main()
