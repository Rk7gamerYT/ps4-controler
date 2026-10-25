"""Read-only gamepad monitoring and bounded force-feedback tests using evdev."""
from evdev import InputDevice, ecodes as e, ff

BUTTONS = {e.BTN_SOUTH:'✕', e.BTN_EAST:'○', e.BTN_NORTH:'△', e.BTN_WEST:'□',
    e.BTN_TL:'L1', e.BTN_TR:'R1', e.BTN_TL2:'L2', e.BTN_TR2:'R2',
    e.BTN_SELECT:'SHARE', e.BTN_START:'OPTIONS', e.BTN_MODE:'PS',
    e.BTN_THUMBL:'L3', e.BTN_THUMBR:'R3'}
AXES = {e.ABS_X:'Analógico E • X', e.ABS_Y:'Analógico E • Y',
    e.ABS_RX:'Analógico D • X', e.ABS_RY:'Analógico D • Y',
    e.ABS_Z:'L2', e.ABS_RZ:'R2', e.ABS_HAT0X:'Direcional X', e.ABS_HAT0Y:'Direcional Y'}


class Gamepad:
    def __init__(self, lightbar):
        self.device = None
        self.effect_id = None
        self.keys = set()
        self.axes = {}
        for node in sorted(lightbar.hid_path.glob('input/input*/event*')):
            dev = InputDevice('/dev/input/' + node.name)
            try:
                caps = dev.capabilities(absinfo=False)
                if e.BTN_GAMEPAD not in caps.get(e.EV_KEY, []):
                    dev.close()
                    continue
                self.device = dev
                self.rumble_supported = e.FF_RUMBLE in caps.get(e.EV_FF, [])
                self.resync()
                break
            except Exception:
                dev.close()
                raise
        if self.device is None:
            raise OSError('Entrada do gamepad não encontrada neste dispositivo.')

    def resync(self):
        self.keys = set(self.device.active_keys())
        self.axes = {code: self.device.absinfo(code) for code in AXES if code in
            self.device.capabilities(absinfo=False).get(e.EV_ABS, [])}

    def poll(self):
        try:
            for event in self.device.read():
                if event.type == e.EV_SYN and event.code == e.SYN_DROPPED:
                    self.resync()
                elif event.type == e.EV_KEY:
                    if event.value:
                        self.keys.add(event.code)
                    else:
                        self.keys.discard(event.code)
                elif event.type == e.EV_ABS and event.code in AXES:
                    self.axes[event.code] = self.device.absinfo(event.code)
        except BlockingIOError:
            pass
        return self.keys, self.axes

    def rumble(self, strong, weak):
        if not self.rumble_supported:
            raise OSError('Este dispositivo não oferece vibração pelo driver.')
        self.stop()
        effect = ff.Effect(e.FF_RUMBLE, -1, 0, ff.Trigger(0, 0), ff.Replay(700, 0),
            ff.EffectType(ff_rumble_effect=ff.Rumble(round(strong * 65535), round(weak * 65535))))
        self.effect_id = self.device.upload_effect(effect)
        self.device.write(e.EV_FF, self.effect_id, 1)

    def stop(self):
        if self.effect_id is not None:
            self.device.write(e.EV_FF, self.effect_id, 0)
            self.device.erase_effect(self.effect_id)
            self.effect_id = None

    def close(self):
        try:
            self.stop()
        except OSError:
            pass
        self.device.close()
