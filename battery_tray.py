"""Percentage icon and tray menu for Qt desktop applications (MIT)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def percentage_icon(percent, charging=False):
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    color = '#697386' if percent is None else '#e25c65' if percent <= 20 else '#45bd91' if charging else '#648dff'
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(1, 8, 62, 49, 10, 10)
    painter.setPen(QColor('white'))
    painter.setFont(QFont('Sans', 27 if percent != 100 else 22, QFont.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, '?' if percent is None else str(percent))
    painter.end()
    return QIcon(pixmap)


class BatteryTray(QSystemTrayIcon):
    def __init__(self, title, show_window, quit_app, parent=None):
        super().__init__(parent)
        self.title = title
        self.menu = QMenu()
        self.header = self.menu.addAction(title)
        self.header.setEnabled(False)
        self.detail = self.menu.addAction('Bateria indisponível')
        self.detail.setEnabled(False)
        self.menu.addSeparator()
        self.menu.addAction('Abrir aplicativo', show_window)
        self.menu.addAction('Sair', quit_app)
        self.setContextMenu(self.menu)
        self.activated.connect(lambda reason: show_window() if reason in (self.Trigger, self.DoubleClick) else None)
        self.update_battery(None, 'Aguardando dispositivo')
        if self.isSystemTrayAvailable():
            self.show()

    def update_battery(self, percent, detail, charging=False):
        self.setIcon(percentage_icon(percent, charging))
        value = 'Sem leitura' if percent is None else f'{percent}%'
        self.detail.setText(f'{value} • {detail}')
        self.setToolTip(f'{self.title}: {value}\n{detail}')
