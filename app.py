import colorsys
import json
import math
import os
import subprocess
import shutil
from pathlib import Path
import sys
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QComboBox, QColorDialog, QFormLayout,
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QSlider, QVBoxLayout, QWidget,
    QTabWidget, QInputDialog, QFileDialog, QMessageBox, QProgressBar)
from battery_tray import BatteryTray
from controller import discover
from profiles import CONFIG, Profiles, normalize
from input_device import Gamepad, BUTTONS, AXES




class Window(QMainWindow):
    def __init__(self, demo=False):
        super().__init__()
        self.quitting = False
        self.tray = None
        self.demo = demo
        self.devices = []
        self.store = Profiles()
        self.gamepad = None
        self.selected_identity = None
        self.permission_process = None
        self.last_output = None
        self.color = QColor('#547cff')
        self.started = time.monotonic()
        self.setWindowTitle('PS4 Control • Linux')
        self.resize(780, 730)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(32, 28, 32, 28)
        title = QLabel('PS4 Control')
        title.setStyleSheet('font-size:30px; font-weight:700')
        layout.addWidget(title)
        layout.addWidget(QLabel('Controles, perfis e personalização no Linux'))
        row = QHBoxLayout()
        self.selector = QComboBox()
        row.addWidget(self.selector, 1)
        refresh = QPushButton('Buscar controle')
        refresh.clicked.connect(self.retry_controller)
        row.addWidget(refresh)
        layout.addLayout(row)
        profile_row = QHBoxLayout()
        self.profile = QComboBox()
        self.profile.addItems(self.store.items)
        self.profile.setCurrentText(self.store.active)
        profile_row.addWidget(QLabel('Perfil deste controle'))
        profile_row.addWidget(self.profile, 1)
        for text, handler in [('Novo', self.new_profile), ('Excluir', self.delete_profile),
                              ('Importar', self.import_profile), ('Exportar', self.export_profile)]:
            button = QPushButton(text)
            button.clicked.connect(handler)
            profile_row.addWidget(button)
        layout.addLayout(profile_row)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        light = QWidget()
        light_layout = QVBoxLayout(light)
        self.tabs.addTab(light, 'Barra de luz')
        self.preview = QLabel('DUALSHOCK 4')
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(100)
        light_layout.addWidget(self.preview)
        form = QFormLayout()
        self.color_button = QPushButton('Escolher cor')
        self.color_button.clicked.connect(self.choose_color)
        form.addRow('Cor da luz', self.color_button)
        self.brightness = QSlider(Qt.Horizontal)
        self.brightness.setRange(0, 100)
        self.brightness.setValue(70)
        form.addRow('Brilho', self.brightness)
        self.effect = QComboBox()
        self.effect.addItems(['Fixa', 'Pulsação', 'Arco-íris', 'Desligada'])
        form.addRow('Efeito', self.effect)
        self.speed = QSlider(Qt.Horizontal)
        self.speed.setRange(1, 100)
        self.speed.setValue(35)
        form.addRow('Velocidade', self.speed)
        light_layout.addLayout(form)
        light_layout.addStretch()
        self.build_monitor()
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color:#ffbc91')
        self.light_error = QLabel()
        self.light_error.setWordWrap(True)
        self.light_error.setStyleSheet('color:#ffbc91')
        layout.addWidget(self.light_error)
        layout.addWidget(self.error)
        self.permissions_button = QPushButton('Liberar acesso à luz…')
        self.permissions_button.clicked.connect(self.grant_light_access)
        layout.addWidget(self.permissions_button)
        layout.addStretch()
        save = QPushButton('Salvar preferências')
        save.clicked.connect(self.save)
        layout.addWidget(save)
        layout.addWidget(QLabel('Os efeitos animados funcionam enquanto o app estiver aberto.'))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.apply_profile(self.store.active)
        self.profile.currentTextChanged.connect(self.change_profile)
        self.selector.currentIndexChanged.connect(self.select_controller)
        self.refresh()
        if self.store.error:
            self.error.setText(self.store.error)
        self.timer.start(50)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.refresh)
        self.scan_timer.start(3000)
        self.tray = BatteryTray('PS4 Control', self.show_window, self.quit_app, self)
        self.update_tray()

    def build_monitor(self):
        page = QWidget()
        form = QFormLayout(page)
        self.device_info = QLabel('Nenhum controle selecionado')
        self.device_info.setWordWrap(True)
        form.addRow('Dispositivo', self.device_info)
        self.input_status = QLabel('Conecte um controle para testar as entradas.')
        self.input_status.setWordWrap(True)
        form.addRow(self.input_status)
        self.pressed = QLabel('—')
        self.pressed.setWordWrap(True)
        form.addRow('Botões pressionados', self.pressed)
        self.axis_bars = {}
        for code, label in AXES.items():
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            form.addRow(label, bar)
            self.axis_bars[code] = bar
        self.tabs.addTab(page, 'Controle e entradas')
        rumble = QWidget()
        rf = QFormLayout(rumble)
        self.strong = QSlider(Qt.Horizontal)
        self.weak = QSlider(Qt.Horizontal)
        for label, slider in [('Motor forte', self.strong), ('Motor suave', self.weak)]:
            slider.setRange(0, 100)
            slider.setValue(50)
            rf.addRow(label, slider)
        self.test_rumble = QPushButton('Testar vibração • 0,7 segundo')
        self.test_rumble.clicked.connect(self.rumble)
        self.test_rumble.setEnabled(False)
        rf.addRow(self.test_rumble)
        rf.addRow(QLabel('As intensidades são salvas no perfil e usadas neste teste.'))
        self.tabs.addTab(rumble, 'Vibração')

    def values(self):
        return dict(color=self.color.name(), brightness=self.brightness.value(),
            speed=self.speed.value(), effect=self.effect.currentIndex(),
            strong=self.strong.value(), weak=self.weak.value())

    def apply_profile(self, name):
        data = self.store.items[name]
        self.color = QColor(data['color'])
        for key in ('brightness', 'speed', 'strong', 'weak'):
            getattr(self, key).setValue(data[key])
        self.effect.setCurrentIndex(data['effect'])
        self.store.active = name
        self.profile.blockSignals(True)
        self.profile.setCurrentText(name)
        self.profile.blockSignals(False)

    def remember_edits(self):
        self.store.items[self.store.active] = self.values()

    def change_profile(self, name):
        if not name or name not in self.store.items:
            return
        self.remember_edits()
        self.apply_profile(name)
        self.save()

    def sync_profiles(self, active):
        self.profile.blockSignals(True)
        self.profile.clear()
        self.profile.addItems(self.store.items)
        self.profile.setCurrentText(active)
        self.profile.blockSignals(False)
        self.apply_profile(active)
        self.save()

    def new_profile(self):
        name, ok = QInputDialog.getText(self, 'Novo perfil', 'Nome (copia os ajustes atuais):')
        if not ok:
            return
        try:
            name = self.store.valid_name(name)
            if name in self.store.items:
                raise ValueError('Já existe um perfil com esse nome.')
            self.remember_edits()
            self.store.items[name] = self.values()
            self.sync_profiles(name)
        except ValueError as exc:
            self.error.setText(str(exc))

    def delete_profile(self):
        name = self.store.active
        if len(self.store.items) == 1:
            self.error.setText('Mantenha pelo menos um perfil.')
            return
        if QMessageBox.question(self, 'Excluir perfil', f'Excluir “{name}”?') != QMessageBox.Yes:
            return
        del self.store.items[name]
        self.store.bindings = {key: value for key, value in self.store.bindings.items() if value != name}
        self.sync_profiles(next(iter(self.store.items)))

    def import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Importar perfil do PS4 Control', '', 'JSON (*.json)')
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text())
            if not isinstance(data, dict):
                raise ValueError('Arquivo de perfil inválido.')
            name = self.store.valid_name(data.get('name', Path(path).stem))
            if name in self.store.items:
                raise ValueError('Esse nome já existe. Renomeie o perfil no arquivo antes de importar.')
            profile = normalize(data.get('settings'))
            self.remember_edits()
            self.store.items[name] = profile
            self.sync_profiles(name)
        except (OSError, ValueError, TypeError) as exc:
            self.error.setText(f'Falha ao importar: {exc}')

    def export_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Exportar perfil', 'perfil.json', 'JSON (*.json)')
        if path:
            try:
                Path(path).write_text(json.dumps(dict(name=self.store.active, settings=self.values()), indent=2))
                self.status.setText('Perfil exportado.')
            except OSError as exc:
                self.error.setText(str(exc))

    def save(self):
        self.remember_edits()
        if self.selected_identity:
            self.store.bindings[self.selected_identity] = self.store.active
        try:
            self.store.save()
            self.status.setText('Perfil salvo e associado ao controle selecionado.' if self.selected_identity
                                else 'Perfil salvo. Selecione um controle para associá-lo.')
        except OSError as exc:
            self.error.setText(f'Não foi possível salvar: {exc}')

    def select_controller(self):
        self.remember_edits()
        if self.gamepad:
            self.gamepad.close()
            self.gamepad = None
        self.last_output = None
        self.selected_identity = None
        self.test_rumble.setEnabled(False)
        self.pressed.setText('—')
        for bar in self.axis_bars.values():
            bar.setValue(0)
            bar.setFormat('—')
        if not self.devices:
            self.device_info.setText('Prévia visual' if self.demo else 'Nenhum controle selecionado')
            self.input_status.setText('Conecte um controle para testar as entradas.')
            return
        device = self.devices[max(0, self.selector.currentIndex())]
        try:
            self.selected_identity = device.identity
            name = self.store.bindings.get(self.selected_identity, 'Padrão')
            self.apply_profile(name if name in self.store.items else next(iter(self.store.items)))
            self.update_info()
            if self.selected_identity.startswith('port:'):
                self.status.setText('Controle sem identificador único: a associação vale para esta porta.')
            self.gamepad = Gamepad(device)
            self.test_rumble.setEnabled(self.gamepad.rumble_supported)
            self.input_status.setText('Entradas reais • somente leitura, sem remapeamento.')
        except (OSError, ValueError) as exc:
            self.input_status.setText(f'Entradas indisponíveis: {exc}. Consulte as permissões no README.')

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self.quitting = True
        self.close()
        QApplication.instance().quit()

    def update_tray(self):
        if self.tray is None:
            return
        percent, state = None, 'Controle desconectado'
        if self.devices:
            device = self.devices[max(0, self.selector.currentIndex())]
            try:
                percent, state = device.battery_status()
                state = f'{device.name} • {state}'
            except OSError:
                state = 'Leitura temporariamente indisponível'
        self.tray.update_battery(percent, state, 'Charging' in state and 'Discharging' not in state)

    def update_info(self):
        self.update_tray()
        if self.devices:
            try:
                name, connection, battery = self.devices[max(0, self.selector.currentIndex())].info()
                self.device_info.setText(f'{name} • {connection}\nBateria: {battery}')
            except (OSError, ValueError):
                self.device_info.setText('Informações temporariamente indisponíveis')

    def rumble(self):
        if self.gamepad:
            try:
                self.gamepad.rumble(self.strong.value() / 100, self.weak.value() / 100)
            except OSError as exc:
                self.error.setText(f'Falha na vibração: {exc}')

    def poll_inputs(self):
        if not self.gamepad:
            return
        try:
            keys, axes = self.gamepad.poll()
            self.pressed.setText('  '.join(BUTTONS.get(key, str(key)) for key in sorted(keys)) or '—')
            for code, info in axes.items():
                bar = self.axis_bars[code]
                bar.setValue(round(100 * (info.value - info.min) / max(1, info.max - info.min)))
                bar.setFormat(str(info.value))
        except OSError as exc:
            self.input_status.setText(f'Leitura interrompida: {exc}. Use Buscar controle para tentar novamente.')
            self.gamepad.close()
            self.gamepad = None
            self.test_rumble.setEnabled(False)

    def grant_light_access(self):
        if not self.devices or self.permission_process:
            return
        pkexec, chown = shutil.which('pkexec'), shutil.which('chown')
        if not pkexec or not chown:
            self.error.setText('Instale o PolicyKit (pkexec) para liberar o acesso pela interface.')
            return
        device = self.devices[max(0, self.selector.currentIndex())]
        try:
            files = [str(path.resolve(strict=True)) for path in device.permission_files]
            if not all(path.startswith('/sys/devices/') and path.endswith(('/brightness', '/multi_intensity')) for path in files):
                raise ValueError('Caminho de LED inválido.')
            self.permission_process = subprocess.Popen([pkexec, chown, str(os.getuid()), '--', *files],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.permissions_button.setEnabled(False)
            self.status.setText('Autorize na janela do sistema para liberar apenas a luz do controle.')
        except (OSError, ValueError) as exc:
            self.error.setText(f'Falha ao liberar acesso: {exc}')

    def check_permissions(self):
        if self.permission_process and self.permission_process.poll() is not None:
            code = self.permission_process.returncode
            self.permission_process = None
            self.permissions_button.setEnabled(True)
            if code == 0:
                self.last_output = None
                self.error.clear()
                self.status.setText('Acesso à luz liberado até desconectar ou reiniciar.')
            else:
                self.error.setText('Autorização cancelada ou acesso não concedido. Tente liberar novamente.')

    def retry_controller(self):
        self.refresh()
        self.select_controller()

    def refresh(self):
        selected = self.selector.currentText()
        try:
            devices = [] if self.demo else discover()
        except (OSError, ValueError) as exc:
            self.error.setText(f'Falha ao buscar controle: {exc}')
            return
        if [d.name for d in devices] != [d.name for d in self.devices] or self.selector.count() == 0:
            self.devices = devices
            self.selector.blockSignals(True)
            self.selector.clear()
            self.selector.addItems([d.name for d in devices] or ['Prévia' if self.demo else 'Nenhum DualShock 4 conectado'])
            if selected in [d.name for d in devices]:
                self.selector.setCurrentText(selected)
            self.selector.blockSignals(False)
            self.status.setText('Controle detectado. Ajustes aplicados em tempo real.' if devices else
                'Modo demonstração: apenas prévia visual.' if self.demo else
                'Conecte o controle por USB ou emparelhe nas configurações Bluetooth do Linux.')
            self.select_controller()

        self.update_info()

    def choose_color(self):
        color = QColorDialog.getColor(self.color, self, 'Cor da luz')
        if color.isValid():
            self.color = color

    def tick(self):
        self.check_permissions()
        self.permissions_button.setVisible(bool(self.devices))
        self.poll_inputs()
        elapsed = time.monotonic() - self.started
        period = 0.5 + (100 - self.speed.value()) / 15
        rgb = self.color.getRgb()[:3]
        brightness = self.brightness.value() / 100
        effect = self.effect.currentIndex()
        if effect == 1:
            brightness *= (1 - math.cos(elapsed * 2 * math.pi / period)) / 2
        elif effect == 2:
            rgb = tuple(round(c * 255) for c in colorsys.hsv_to_rgb((elapsed / period) % 1, 0.85, 1))
        elif effect == 3:
            brightness = 0
        shown = QColor(*(round(c * brightness) for c in rgb)).name()
        self.preview.setStyleSheet(f'background:{shown}; border-radius:18px; color:white; font-weight:700; letter-spacing:4px')
        self.color_button.setText(self.color.name().upper() + ' • Escolher cor')
        self.speed.setEnabled(effect in (1, 2))
        if self.devices:
            try:
                output = (tuple(rgb), round(brightness * 255))
                if output != self.last_output:
                    self.devices[max(0, self.selector.currentIndex())].apply(rgb, brightness)
                    self.last_output = output
                self.light_error.clear()
            except PermissionError:
                self.light_error.setText('Sem permissão para alterar a luz. Clique em Liberar acesso à luz e autorize na janela do sistema.')
            except (OSError, ValueError) as exc:
                self.light_error.setText(f'Não foi possível ajustar a luz: {exc}')

    def closeEvent(self, event):
        if self.tray is not None and self.tray.isVisible() and not self.quitting:
            self.hide()
            event.ignore()
            return
        self.timer.stop()
        if self.gamepad:
            self.gamepad.close()
        # Leave a stable color instead of freezing halfway through an animation.
        if self.devices:
            try:
                self.devices[max(0, self.selector.currentIndex())].apply(self.color.getRgb()[:3],
                    0 if self.effect.currentIndex() == 3 else self.brightness.value() / 100)
            except OSError:
                pass
        event.accept()


def create_application():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet('''QWidget {background:#101522;color:#e4eaf9;font-size:14px}
        QPushButton,QComboBox {background:#222d46;border:1px solid #3b4a6b;border-radius:8px;padding:10px}
        QPushButton:hover {background:#33486f} QLabel {background:transparent}
        QSlider::groove:horizontal {height:6px;background:#303d59;border-radius:3px}
        QSlider::handle:horizontal {background:#7e9cff;width:18px;margin:-6px 0;border-radius:9px}''')
    return app


def main():
    app = create_application()
    window = Window('--demo' in sys.argv)
    window.show()
    if '--smoke-test' in sys.argv:
        QTimer.singleShot(300, app.quit)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
