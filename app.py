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
from PySide6.QtGui import QColor, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QColorDialog, QFrame,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QPushButton, QSlider,
    QVBoxLayout, QWidget, QTabWidget, QInputDialog, QFileDialog, QMessageBox, QProgressBar, QScrollArea, QLayout, QSizePolicy)
from battery_tray import BatteryTray
from theme import PALETTES, load_theme, save_theme, stylesheet
from widgets import BatteryBar, ControllerView, SwatchRow
from controller import discover
from profiles import CONFIG, Profiles, normalize
from input_device import Gamepad, BUTTONS, AXES
from evdev import ecodes as e




def card(title=None):
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 16, 20, 18)
    layout.setSpacing(10)
    if title:
        label = QLabel(title.upper())
        label.setObjectName('section')
        layout.addWidget(label)
    return frame, layout


def slider_row(slider, suffix='%'):
    row = QHBoxLayout()
    value = QLabel()
    value.setObjectName('value')
    value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    slider.valueChanged.connect(lambda v: value.setText(f'{v}{suffix}'))
    value.setText(f'{slider.value()}{suffix}')
    row.addWidget(slider, 1)
    row.addWidget(value)
    return row


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
        self.theme = load_theme()
        self.color = QColor('#547cff')
        self.started = time.monotonic()
        self.setWindowTitle('PS4 Control • Linux')
        self.resize(1180, 820)
        body = QWidget()
        self.setCentralWidget(body)
        shell = QHBoxLayout(body)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self.build_sidebar())
        content = QWidget()
        content.setObjectName('workspace')
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)
        shell.addWidget(scroll, 1)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(14)
        layout.addLayout(self.build_header())
        layout.addWidget(self.build_device_card())
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.build_light_tab()
        self.build_monitor()
        self.build_profiles_tab()
        self.tabs.tabBar().hide()
        self.navigation.currentRowChanged.connect(self.navigate)
        self.navigation.setCurrentRow(0)
        self.error = QLabel()
        self.error.setObjectName('error')
        self.light_error = QLabel()
        self.light_error.setObjectName('error')
        for label in (self.error, self.light_error):
            label.setWordWrap(True)
            label.hide()
            layout.addWidget(label)
        self.permissions_button = QPushButton('Liberar acesso à luz…')
        self.permissions_button.clicked.connect(self.grant_light_access)
        self.permissions_button.hide()
        layout.addWidget(self.permissions_button)
        footer = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName('status')
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.save_button = QPushButton('Salvar perfil')
        self.save_button.setObjectName('primary')
        self.save_button.setToolTip('Salvar perfil e associação ao controle • Ctrl+S')
        self.save_button.clicked.connect(self.save)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)
        QShortcut(QKeySequence.Save, self, activated=self.save)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.apply_profile(self.store.active)
        self.profile.currentTextChanged.connect(self.change_profile)
        self.selector.currentIndexChanged.connect(self.select_controller)
        self.apply_theme(self.theme, persist=False)
        self.refresh()
        if self.store.error:
            self.error.setText(self.store.error)
        self.timer.start(50)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.refresh)
        self.scan_timer.start(3000)
        self.tray = BatteryTray('PS4 Control', self.show_window, self.quit_app, self)
        self.update_tray()

    # ---- construção da interface -------------------------------------------------
    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(204)
        column = QVBoxLayout(sidebar)
        column.setContentsMargins(18, 28, 18, 22)
        column.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(QIcon(str(Path(__file__).with_name('assets') / 'icon.svg')).pixmap(52, 52))
        column.addWidget(logo)
        brand = QLabel('PS4 Control')
        brand.setObjectName('brand')
        column.addWidget(brand)
        subtitle = QLabel('SEU CONTROLE.\nDO SEU JEITO.')
        subtitle.setObjectName('section')
        column.addWidget(subtitle)
        column.addSpacing(26)
        self.navigation = QListWidget()
        self.navigation.setObjectName('navigation')
        self.navigation.addItems(['Barra de luz', 'Teste de entradas', 'Vibração', 'Meus perfis'])
        self.navigation.setSpacing(5)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        column.addWidget(self.navigation, 1)
        foot = QLabel('DUALSHOCK 4\nUSB + Bluetooth')
        foot.setObjectName('muted')
        column.addWidget(foot)
        return sidebar

    def navigate(self, index):
        if index < 0:
            return
        self.tabs.setCurrentIndex(index)
        self.page_title.setText(['Sua luz, sua identidade', 'Cada movimento em tempo real',
                                 'Sinta o controle', 'Pronto para cada jogo'][index])
        self.page_subtitle.setText(['Escolha uma cor e veja seu DualShock 4 ganhar vida.',
            'Confira os botões, gatilhos e analógicos do controle selecionado.',
            'Ajuste a intensidade e teste os dois motores de vibração.',
            'Organize seus ajustes e associe um perfil a cada controle.'][index])

    def build_header(self):
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel('Sua luz, sua identidade')
        self.page_title = title
        title.setObjectName('title')
        subtitle = QLabel('Escolha uma cor e veja seu DualShock 4 ganhar vida.')
        self.page_subtitle = subtitle
        subtitle.setWordWrap(True)
        subtitle.setObjectName('subtitle')
        titles.addWidget(title)
        titles.addWidget(subtitle)
        row.addLayout(titles, 1)
        self.theme_button = QPushButton()
        self.theme_button.setObjectName('ghost')
        self.theme_button.setToolTip('Alternar entre tema escuro e claro')
        self.theme_button.clicked.connect(lambda: self.apply_theme('light' if self.theme == 'dark' else 'dark'))
        row.addWidget(self.theme_button)
        return row

    def build_device_card(self):
        frame, outer = card()
        outer.setSpacing(12)
        top = QHBoxLayout()
        self.selector = QComboBox()
        self.selector.setMinimumWidth(180)
        self.selector.setToolTip('Controle que recebe os ajustes deste perfil')
        top.addWidget(self.selector, 1)
        refresh = QPushButton('Buscar controle')
        refresh.clicked.connect(self.retry_controller)
        top.addWidget(refresh)
        top.addSpacing(10)
        top.addWidget(QLabel('Perfil'))
        self.profile = QComboBox()
        self.profile.addItems(self.store.items)
        self.profile.setCurrentText(self.store.active)
        self.profile.setMinimumWidth(130)
        top.addWidget(self.profile)
        outer.addLayout(top)
        info = QHBoxLayout()
        info.setSpacing(16)
        self.connection_label = QLabel('Desconectado')
        self.connection_label.setObjectName('muted')
        self.device_info = QLabel('Nenhum controle selecionado')
        self.device_info.setWordWrap(True)
        info.addWidget(self.device_info, 1)
        info.addWidget(self.connection_label)
        self.battery_bar = BatteryBar(self.theme)
        info.addWidget(self.battery_bar)
        outer.addLayout(info)
        return frame

    def build_light_tab(self):
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(14)
        preview_card, pl = card('Seu DualShock 4')
        preview_card.setObjectName('hero')
        self.preview = ControllerView(self.theme, show_inputs=False)
        pl.addWidget(self.preview, 1)
        self.light_caption = QLabel()
        self.light_caption.setObjectName('pill')
        self.light_caption.setAlignment(Qt.AlignCenter)
        pl.addWidget(self.light_caption)
        row.addWidget(preview_card, 5)
        controls, cl = card('Personalizar luz')
        controls.setMinimumWidth(350)
        cl.addWidget(QLabel('Cor'))
        swatches = SwatchRow()
        swatches.picked.connect(self.pick_preset)
        cl.addWidget(swatches)
        self.color_button = QPushButton('Escolher cor')
        self.color_button.clicked.connect(self.choose_color)
        cl.addWidget(self.color_button)
        cl.addSpacing(6)
        cl.addWidget(QLabel('Brilho'))
        self.brightness = QSlider(Qt.Horizontal)
        self.brightness.setRange(0, 100)
        self.brightness.setValue(70)
        cl.addLayout(slider_row(self.brightness))
        cl.addWidget(QLabel('Efeito'))
        self.effect = QComboBox()
        self.effect.addItems(['Fixa', 'Pulsação', 'Arco-íris', 'Desligada'])
        cl.addWidget(self.effect)
        self.speed_label = QLabel('Velocidade do efeito')
        cl.addWidget(self.speed_label)
        self.speed = QSlider(Qt.Horizontal)
        self.speed.setRange(1, 100)
        self.speed.setValue(35)
        cl.addLayout(slider_row(self.speed))
        cl.addStretch()
        row.addWidget(controls, 4)
        self.tabs.addTab(page, 'Barra de luz')

    def build_monitor(self):
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(14)
        pad_card, pl = card('Teste de entradas')
        self.pad = ControllerView(self.theme)
        pl.addWidget(self.pad, 1)
        self.input_status = QLabel('Conecte um controle para testar as entradas.')
        self.input_status.setObjectName('muted')
        self.input_status.setWordWrap(True)
        self.input_status.setAlignment(Qt.AlignCenter)
        pl.addWidget(self.input_status)
        row.addWidget(pad_card, 5)
        values, vl = card('Valores em tempo real')
        vl.addWidget(QLabel('Botões pressionados'))
        self.pressed = QLabel('—')
        self.pressed.setWordWrap(True)
        self.pressed.setStyleSheet('font-size:18px;font-weight:700')
        vl.addWidget(self.pressed)
        self.axis_bars = {}
        for code, label in AXES.items():
            line = QHBoxLayout()
            name = QLabel(label)
            name.setMinimumWidth(130)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat('—')
            line.addWidget(name)
            line.addWidget(bar, 1)
            vl.addLayout(line)
            self.axis_bars[code] = bar
        vl.addStretch()
        row.addWidget(values, 4)
        self.tabs.addTab(page, 'Entradas')
        rumble = QWidget()
        rl = QVBoxLayout(rumble)
        rl.setContentsMargins(0, 4, 0, 0)
        rcard, rc = card('Teste de vibração')
        self.strong = QSlider(Qt.Horizontal)
        self.weak = QSlider(Qt.Horizontal)
        for label, slider in [('Motor forte (esquerda)', self.strong), ('Motor suave (direita)', self.weak)]:
            slider.setRange(0, 100)
            slider.setValue(50)
            rc.addWidget(QLabel(label))
            rc.addLayout(slider_row(slider))
        self.test_rumble = QPushButton('Testar vibração • 0,7 segundo')
        self.test_rumble.setObjectName('primary')
        self.test_rumble.clicked.connect(self.rumble)
        self.test_rumble.setEnabled(False)
        rc.addWidget(self.test_rumble)
        note = QLabel('As intensidades são salvas no perfil e usadas neste teste.')
        note.setObjectName('muted')
        rc.addWidget(note)
        rl.addWidget(rcard)
        rl.addStretch()
        self.tabs.addTab(rumble, 'Vibração')

    def build_profiles_tab(self):
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(14)
        listing, ll = card('Seus perfis')
        self.profile_list = QListWidget()
        self.profile_list.currentTextChanged.connect(self.pick_listed_profile)
        ll.addWidget(self.profile_list, 1)
        row.addWidget(listing, 4)
        actions, al = card('Gerenciar')
        self.profile_summary = QLabel()
        self.profile_summary.setWordWrap(True)
        al.addWidget(self.profile_summary)
        for text, handler, name in [('Novo perfil (copia os ajustes atuais)', self.new_profile, ''),
                                    ('Duplicar', self.duplicate_profile, ''),
                                    ('Renomear', self.rename_profile, ''),
                                    ('Importar de arquivo…', self.import_profile, ''),
                                    ('Exportar para arquivo…', self.export_profile, ''),
                                    ('Excluir perfil', self.delete_profile, 'danger')]:
            button = QPushButton(text)
            if name:
                button.setObjectName(name)
            button.clicked.connect(handler)
            al.addWidget(button)
        al.addStretch()
        note = QLabel('Perfis podem ser compartilhados por vários controles; editar um perfil altera todos que o usam.')
        note.setObjectName('muted')
        note.setWordWrap(True)
        al.addWidget(note)
        row.addWidget(actions, 4)
        self.tabs.addTab(page, 'Perfis')

    # ---- tema e cartão de status ---------------------------------------------------
    def apply_theme(self, name, persist=True):
        self.theme = name
        QApplication.instance().setStyleSheet(stylesheet(name))
        self.theme_button.setText('☀  Tema claro' if name == 'dark' else '☾  Tema escuro')
        for widget in (self.preview, self.pad, self.battery_bar):
            widget.set_theme(name)
        if persist:
            save_theme(name)

    def update_status_card(self, percent, state, name, connection):
        self.battery_bar.set_value(percent, 'Charging' in state and 'Discharging' not in state)
        self.connection_label.setText(f'● {connection}')
        self.connection_label.setStyleSheet(f"color:{PALETTES[self.theme]['ok']}")
        self.device_info.setText(f'{name}\n{state}')

    def clear_status_card(self):
        self.battery_bar.set_value(None)
        self.connection_label.setText('○ Desconectado')
        self.connection_label.setStyleSheet('')
        self.device_info.setText('Prévia visual' if self.demo else 'Nenhum controle selecionado')

    def refresh_profile_list(self):
        self.profile_list.blockSignals(True)
        self.profile_list.clear()
        users = {}
        for profile in self.store.bindings.values():
            users[profile] = users.get(profile, 0) + 1
        for name in self.store.items:
            count = users.get(name, 0)
            item = QListWidgetItem(f"{name}   ·   {count} controle{'s' if count != 1 else ''}" if count else name)
            item.setData(Qt.UserRole, name)
            self.profile_list.addItem(item)
            if name == self.store.active:
                self.profile_list.setCurrentItem(item)
        self.profile_list.blockSignals(False)
        data = self.store.items.get(self.store.active)
        if data:
            effect = ['Fixa', 'Pulsação', 'Arco-íris', 'Desligada'][data['effect']]
            self.profile_summary.setText(f"Perfil ativo: {self.store.active}\nCor {data['color'].upper()} • {effect} • brilho {data['brightness']}%")

    def pick_listed_profile(self, _):
        item = self.profile_list.currentItem()
        name = item.data(Qt.UserRole) if item else None
        if name and name != self.store.active:
            self.change_profile(name)

    def pick_preset(self, color):
        self.color = QColor(color)
        if self.effect.currentIndex() in (2, 3):
            self.effect.setCurrentIndex(0)

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
        self.refresh_profile_list()

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

    def duplicate_profile(self):
        name = f'{self.store.active} (cópia)'
        number = 2
        while name in self.store.items:
            name = f'{self.store.active} (cópia {number})'
            number += 1
        self.remember_edits()
        self.store.items[name] = self.values()
        self.sync_profiles(name)
        self.status.setText(f'Perfil duplicado como “{name}”.')

    def rename_profile(self):
        old = self.store.active
        name, ok = QInputDialog.getText(self, 'Renomear perfil', 'Novo nome:', text=old)
        if not ok:
            return
        try:
            name = self.store.valid_name(name)
            if name != old and name in self.store.items:
                raise ValueError('Já existe um perfil com esse nome.')
            self.remember_edits()
            self.store.items = {(name if key == old else key): value for key, value in self.store.items.items()}
            self.store.bindings = {key: (name if value == old else value) for key, value in self.store.bindings.items()}
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
            self.refresh_profile_list()
            self.error.clear()
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
        self.pad.clear_state()
        for bar in self.axis_bars.values():
            bar.setValue(0)
            bar.setFormat('—')
        if not self.devices:
            self.clear_status_card()
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
                device = self.devices[max(0, self.selector.currentIndex())]
                name, connection, _ = device.info()
                percent, state = device.battery_status()
                self.update_status_card(percent, state, name, connection)
            except (OSError, ValueError):
                self.device_info.setText('Informações temporariamente indisponíveis')
        else:
            self.clear_status_card()

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
            levels = {}
            for code, info in axes.items():
                bar = self.axis_bars[code]
                level = (info.value - info.min) / max(1, info.max - info.min)
                levels[code] = info.value if code in (e.ABS_HAT0X, e.ABS_HAT0Y) else level
                bar.setValue(round(100 * level))
                bar.setFormat(str(info.value))
            self.pad.set_state(keys, levels)
        except OSError as exc:
            self.input_status.setText(f'Leitura interrompida: {exc}. Use Buscar controle para tentar novamente.')
            self.gamepad.close()
            self.gamepad = None
            self.test_rumble.setEnabled(False)
            self.pad.clear_state()

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
        needs_access = bool(self.devices) and any(not os.access(path, os.W_OK)
            for path in getattr(self.devices[max(0, self.selector.currentIndex())], 'permission_files', []))
        self.permissions_button.setVisible(needs_access or self.permission_process is not None)
        self.error.setVisible(bool(self.error.text()))
        self.light_error.setVisible(bool(self.light_error.text()))
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
        self.preview.set_light(shown)
        self.light_caption.setText(f"{self.color.name().upper()} • {['Fixa', 'Pulsação', 'Arco-íris', 'Desligada'][effect]}")
        self.color_button.setText(self.color.name().upper() + ' • Outra cor…')
        self.speed.setEnabled(effect in (1, 2))
        self.speed_label.setText('Velocidade do efeito' if effect in (1, 2) else 'Velocidade • escolha um efeito animado')
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
    app.setApplicationName('ps4-control')
    app.setDesktopFileName('ps4-control')
    app.setWindowIcon(QIcon(str(Path(__file__).with_name('assets') / 'icon.svg')))
    app.setStyle('Fusion')
    app.setStyleSheet(stylesheet('dark'))
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
