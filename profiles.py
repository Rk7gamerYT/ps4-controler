"""Versioned named profiles, with migration from the first app release."""
import json
import os
from pathlib import Path

CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'ps4-controler/settings.json'
DEFAULT = dict(color='#547cff', brightness=70, speed=35, effect=0, strong=50, weak=50)


def normalize(data):
    if not isinstance(data, dict):
        raise ValueError('Perfil deve ser um objeto JSON.')
    result = DEFAULT.copy()
    color = data.get('color', result['color'])
    if not isinstance(color, str) or len(color) != 7 or not color.startswith('#'):
        raise ValueError('Cor inválida.')
    try:
        int(color[1:], 16)
    except ValueError:
        raise ValueError('Cor inválida.') from None
    result['color'] = color
    for key in ('brightness', 'speed', 'effect', 'strong', 'weak'):
        value = data.get(key, result[key])
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f'Valor inválido: {key}')
        if not (1 if key == 'speed' else 0) <= value <= (3 if key == 'effect' else 100):
            raise ValueError(f'Valor fora do intervalo: {key}')
        result[key] = value
    return result


class Profiles:
    def __init__(self, path=CONFIG):
        self.path = Path(path)
        self.items = {'Padrão': DEFAULT.copy()}
        self.active = 'Padrão'
        self.bindings = {}
        self.error = ''
        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict):
                raise ValueError('Formato de configurações inválido.')
            if 'profiles' in data:
                if data.get('version') != 2 or not isinstance(data['profiles'], dict) or not data['profiles']:
                    raise ValueError('Formato de perfis inválido.')
                loaded = {}
                for name, value in data['profiles'].items():
                    loaded[self.valid_name(name)] = normalize(value)
                self.items = loaded
                bindings = data.get('bindings', {})
                if not isinstance(bindings, dict):
                    raise ValueError('Associações inválidas.')
                self.bindings = {key: value for key, value in bindings.items() if isinstance(key, str) and value in loaded}
                self.active = data.get('active') if data.get('active') in loaded else next(iter(loaded))
            else:
                self.items['Padrão'] = normalize(data)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as exc:
            self.error = f'Não foi possível carregar as preferências: {exc}'

    @staticmethod
    def valid_name(name):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 60:
            raise ValueError('Use um nome entre 1 e 60 caracteres.')
        return name.strip()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(version=2, active=self.active, profiles=self.items, bindings=self.bindings), indent=2))
        temporary.replace(self.path)
