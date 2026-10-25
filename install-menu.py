#!/usr/bin/env python3
"""Install a user-local application menu entry and icon, without root."""
import os
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parent
ident, name, description = ('ps4-control', 'PS4 Control', 'Configurar o controle DualShock 4 no Linux') if (root / 'controller.py').exists() else ('attack-shark-r1-control', 'Attack Shark R1 Control', 'Configurar o mouse Attack Shark R1 e acompanhar a bateria')
data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
icons = data / 'icons/hicolor/scalable/apps'
icons.mkdir(parents=True, exist_ok=True)
shutil.copyfile(root / 'assets/icon.svg', icons / (ident + '.svg'))
applications = data / 'applications'
applications.mkdir(parents=True, exist_ok=True)
# Desktop Entry Exec has its own quoting rules, independent of shell quoting.
command = str(root / 'run.sh').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
entry = applications / (ident + '.desktop')
entry.write_text(f'''[Desktop Entry]
Type=Application
Version=1.0
Name={name}
Comment={description}
Exec="{command}"
Icon={ident}
Terminal=false
Categories=Settings;HardwareSettings;
Keywords=Linux;Battery;Bateria;
StartupNotify=true
StartupWMClass={ident}
''')
if shutil.which('update-desktop-database'):
    subprocess.run(['update-desktop-database', str(applications)], check=True)
if shutil.which('gtk-update-icon-cache'):
    subprocess.run(['gtk-update-icon-cache', '-f', '-t', str(data / 'icons/hicolor')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f'Atalho instalado: {entry}')
