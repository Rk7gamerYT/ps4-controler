"""Linux multicolor LED backend. Only Sony DualShock 4 devices are selected."""
from pathlib import Path


class Lightbar:
    def __init__(self, path):
        self.path = Path(path)
        self.channels = (self.path / 'multi_index').read_text().split()
        self.maximum = int((self.path / 'max_brightness').read_text())

    @property
    def hid_path(self):
        for parent in self.path.resolve().parents:
            try:
                if any(line.startswith('HID_ID=') for line in (parent / 'uevent').read_text().splitlines()):
                    return parent
            except OSError:
                continue
        raise OSError('Dispositivo HID não encontrado.')

    @property
    def identity(self):
        data = dict(line.split('=', 1) for line in (self.hid_path / 'uevent').read_text().splitlines() if '=' in line)
        unique = data.get('HID_UNIQ', '').strip().lower()
        if unique and unique.replace(':', '').replace('-', '').strip('0'):
            return 'sony-ds4:' + unique
        # Fallback is explicitly port-specific when hardware provides no serial.
        return 'port:' + str(self.hid_path)

    def info(self):
        root = self.hid_path
        data = dict(line.split('=', 1) for line in (root / 'uevent').read_text().splitlines() if '=' in line)
        connection = 'Bluetooth' if data.get('HID_ID', '').startswith('0005:') else 'USB / adaptador'
        battery = 'Não informada pelo driver'
        for supply in root.glob('power_supply/*'):
            try:
                battery = f"{int((supply / 'capacity').read_text())}% • {(supply / 'status').read_text().strip()}"
                break
            except (OSError, ValueError):
                continue
        return data.get('HID_NAME', 'DualShock 4'), connection, battery

    @property
    def name(self):
        return self.path.name

    @property
    def permission_files(self):
        return [self.path / 'brightness', self.path / 'multi_intensity']

    def apply(self, rgb, brightness):
        values = dict(zip(('red', 'green', 'blue'), rgb))
        intensity = ' '.join(str(round(values.get(c, 0) * self.maximum / 255)) for c in self.channels)
        (self.path / 'multi_intensity').write_text(intensity + '\n')
        (self.path / 'brightness').write_text(str(round(self.maximum * brightness)) + '\n')


class SeparateLightbar(Lightbar):
    """Driver variant exposing red/green/blue and a global LED switch."""
    def __init__(self, path):
        self.path = Path(path)
        prefix = self.path.name.rsplit(':', 1)[0]
        self.leds = {color: self.path.parent / (prefix + ':' + color)
                     for color in ('red', 'green', 'blue')}
        self.global_led = self.path.parent / (prefix + ':global')

    @property
    def permission_files(self):
        files = [p / 'brightness' for p in self.leds.values()]
        if self.global_led.exists():
            files.append(self.global_led / 'brightness')
        return files

    def apply(self, rgb, brightness):
        for color, value in zip(('red', 'green', 'blue'), rgb):
            led = self.leds[color]
            maximum = int((led / 'max_brightness').read_text())
            (led / 'brightness').write_text(str(round(value / 255 * maximum * brightness)) + '\n')
        if self.global_led.exists():
            (self.global_led / 'brightness').write_text('1\n' if brightness > 0 else '0\n')


def discover(root=Path('/sys/class/leds')):
    result = []
    seen = set()
    root = Path(root)
    candidates = [(p, Lightbar) for p in sorted(root.glob('*:rgb:indicator')) if (p / 'multi_index').exists()]
    for p in sorted(root.glob('*:red')):
        prefix = p.name.rsplit(':', 1)[0]
        if all((root / (prefix + ':' + c) / 'brightness').exists() for c in ('red', 'green', 'blue')):
            candidates.append((p, SeparateLightbar))
    for path, backend in candidates:
        try:
            device = backend(path)
            hid = device.hid_path
            lines = (hid / 'uevent').read_text().upper().splitlines()
            ids = [line.split('=', 1)[1].split(':') for line in lines if line.startswith('HID_ID=')]
            if ids:
                _, vendor, product = ids[0]
                if int(vendor, 16) == 0x054C and int(product, 16) in (0x05C4, 0x09CC, 0x0BA0) and hid not in seen:
                    result.append(device)
                    seen.add(hid)
        except (OSError, ValueError):
            continue
    return result
