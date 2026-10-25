import unittest
from unittest.mock import Mock
from evdev import ecodes as e
from input_device import Gamepad


class RumbleTests(unittest.TestCase):
    def test_bounded_effect_stops_and_releases_on_close(self):
        gamepad = Gamepad.__new__(Gamepad)
        gamepad.device = Mock()
        gamepad.device.upload_effect.return_value = 7
        gamepad.effect_id = None
        gamepad.rumble_supported = True
        gamepad.rumble(1, 0.5)
        effect = gamepad.device.upload_effect.call_args.args[0]
        self.assertEqual(effect.ff_replay.length, 700)
        self.assertEqual(effect.u.ff_rumble_effect.strong_magnitude, 65535)
        self.assertEqual(effect.u.ff_rumble_effect.weak_magnitude, 32768)
        gamepad.device.write.assert_called_with(e.EV_FF, 7, 1)
        gamepad.close()
        gamepad.device.write.assert_called_with(e.EV_FF, 7, 0)
        gamepad.device.erase_effect.assert_called_once_with(7)
        gamepad.device.close.assert_called_once()
