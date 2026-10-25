"""Widgets desenhados à mão: controle com luz, bateria e amostras de cor."""
from evdev import ecodes as e
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient, QLinearGradient
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from theme import PALETTES

PRESETS = ['#547cff', '#00c8ff', '#2ecc71', '#ffd23f', '#ff8a30', '#ff3b3b', '#ff5fb7', '#a45cff', '#ffffff']


class ControllerView(QWidget):
    """Desenho do DualShock 4: barra de luz, botões, analógicos e gatilhos."""

    def __init__(self, theme='dark', show_inputs=True, parent=None):
        super().__init__(parent)
        self.palette_name = theme
        self.show_inputs = show_inputs
        self.light = QColor('#000000')
        self.keys = set()
        self.axes = {}  # código -> valor normalizado (0..1; direcional -1..1)
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_theme(self, name):
        self.palette_name = name
        self.update()

    def set_light(self, color):
        if color != self.light:
            self.light = QColor(color)
            self.update()

    def set_state(self, keys, axes):
        state = (set(keys), dict(axes))
        if state != (self.keys, self.axes):
            self.keys, self.axes = state
            self.update()

    def clear_state(self):
        self.set_state(set(), {})

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        scale = min(self.width() / 420, self.height() / 290)
        painter.translate((self.width()-420*scale)/2, (self.height()-290*scale)/2)
        painter.scale(scale, scale)
        painter.translate(10, 5)
        accent = QColor(PALETTES[self.palette_name]['accent'])
        keys = self.keys if self.show_inputs else set()
        axes = self.axes if self.show_inputs else {}

        def gradient(top, bottom, y1=45, y2=260):
            brush = QLinearGradient(0, y1, 0, y2)
            brush.setColorAt(0, QColor(top))
            brush.setColorAt(1, QColor(bottom))
            return brush

        def disc(x, y, radius, top, bottom, border='#090b10', width=1.2):
            painter.setPen(QPen(QColor(border), width))
            painter.setBrush(gradient(top, bottom, y-radius, y+radius))
            painter.drawEllipse(QPointF(x, y), radius, radius)

        # A sombra e a luz pertencem à cena; o acabamento do controle permanece preto.
        painter.setPen(Qt.NoPen)
        shadow = QRadialGradient(QPointF(200, 252), 183)
        shadow.setColorAt(0, QColor(0, 0, 0, 100))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(shadow)
        painter.drawEllipse(QRectF(5, 233, 390, 34))
        if self.light.value() > 0:
            halo = QRadialGradient(QPointF(200, 55), 158)
            color = QColor(self.light)
            color.setAlpha(100)
            halo.setColorAt(0, color)
            color.setAlpha(0)
            halo.setColorAt(1, color)
            painter.setBrush(halo)
            painter.drawEllipse(QRectF(30, -45, 340, 245))

        # Gatilhos parcialmente visíveis, como na vista frontal do DualShock 4.
        for x, code, key in ((65, e.ABS_Z, e.BTN_TL2), (275, e.ABS_RZ, e.BTN_TR2)):
            level = 1 if key in keys else axes.get(code, 0)
            painter.setPen(QPen(QColor('#55575e'), 1))
            painter.setBrush(gradient('#696c74', '#181a21', 30, 46))
            painter.drawRoundedRect(QRectF(x, 30, 60, 19), 16, 9)
            if level > 0:
                painter.setPen(Qt.NoPen)
                painter.setBrush(accent)
                painter.drawRoundedRect(QRectF(x+5, 44-10*level, 50, 10*level), 4, 4)

        shell = QPainterPath()
        shell.moveTo(77, 43)
        shell.cubicTo(96, 38, 116, 42, 131, 48)
        shell.lineTo(269, 48)
        shell.cubicTo(284, 42, 304, 38, 323, 43)
        shell.cubicTo(351, 75, 369, 115, 380, 168)
        shell.cubicTo(388, 202, 391, 240, 373, 255)
        shell.cubicTo(358, 268, 335, 265, 322, 246)
        shell.cubicTo(310, 226, 303, 202, 293, 182)
        shell.cubicTo(278, 190, 252, 195, 233, 185)
        shell.lineTo(167, 185)
        shell.cubicTo(148, 195, 122, 190, 107, 182)
        shell.cubicTo(97, 202, 90, 226, 78, 246)
        shell.cubicTo(65, 265, 42, 268, 27, 255)
        shell.cubicTo(9, 240, 12, 202, 20, 168)
        shell.cubicTo(31, 115, 49, 75, 77, 43)
        shell.closeSubpath()
        painter.setPen(QPen(QColor('#4b4d55'), 1.2))
        painter.setBrush(gradient('#35363e', '#111218'))
        painter.drawPath(shell)

        # Painéis de borracha nas empunhaduras e reflexo suave sobre o plástico.
        painter.save()
        painter.setClipPath(shell)
        for mirrored in (False, True):
            painter.save()
            if mirrored:
                painter.translate(400, 0)
                painter.scale(-1, 1)
            grip = QPainterPath()
            grip.moveTo(14, 203)
            grip.cubicTo(31, 220, 58, 232, 88, 226)
            grip.lineTo(82, 267)
            grip.lineTo(12, 267)
            grip.closeSubpath()
            painter.setPen(QPen(QColor('#353740'), 0.8))
            painter.setBrush(gradient('#202128', '#0e1015', 205, 270))
            painter.drawPath(grip)
            sheen = QRadialGradient(QPointF(47, 157), 67)
            sheen.setColorAt(0, QColor(255, 255, 255, 14))
            sheen.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(sheen)
            painter.drawEllipse(QRectF(15, 86, 85, 150))
            painter.restore()
        painter.restore()

        # Bases circulares dos botões e bumpers discretos.
        for x in (90, 310):
            disc(x, 102, 46, '#303139', '#25262d', '#4a4b53', 0.8)
        for x, key in ((66, e.BTN_TL), (274, e.BTN_TR)):
            painter.setPen(QPen(accent if key in keys else QColor('#55565d'), 1))
            painter.setBrush(accent if key in keys else QColor('#292b32'))
            painter.drawRoundedRect(QRectF(x, 42, 60, 6), 3, 3)

        # Touchpad encastrado, borda biselada e superfície pontilhada.
        painter.setPen(QPen(QColor('#08090d'), 2))
        painter.setBrush(gradient('#45464d', '#15161c', 48, 119))
        painter.drawRoundedRect(QRectF(135, 47, 130, 73), 7, 7)
        painter.setPen(QPen(QColor('#4b4d54'), 0.7))
        painter.setBrush(gradient('#24252d', '#101218', 51, 117))
        painter.drawRoundedRect(QRectF(138, 51, 124, 66), 5, 5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#383a45'))
        for row in range(14):
            for col in range(29):
                painter.drawEllipse(QPointF(143+col*4, 59+row*4), 0.55, 0.55)
        painter.setBrush(self.light if self.light.value() else QColor('#30333f'))
        painter.drawRoundedRect(QRectF(142, 53, 116, 2), 1, 1)

        # Direcional com borda e símbolos de direção nas quatro extremidades.
        hx, hy = axes.get(e.ABS_HAT0X, 0), axes.get(e.ABS_HAT0Y, 0)
        for angle, active in ((0, hy < 0), (90, hx > 0), (180, hy > 0), (270, hx < 0)):
            painter.save()
            painter.translate(90, 102)
            painter.rotate(angle)
            key_shape = QPainterPath()
            key_shape.moveTo(-7, -29)
            key_shape.quadTo(-11, -29, -11, -24)
            key_shape.lineTo(-10, -12)
            key_shape.lineTo(0, -4)
            key_shape.lineTo(10, -12)
            key_shape.lineTo(11, -24)
            key_shape.quadTo(11, -29, 7, -29)
            key_shape.closeSubpath()
            painter.setPen(QPen(accent if active else QColor('#07080c'), 2))
            painter.setBrush(accent if active else gradient('#45464e', '#202128', -29, -4))
            painter.drawPath(key_shape)
            arrow = QPainterPath()
            arrow.moveTo(0, -40)
            arrow.lineTo(-4, -35)
            arrow.lineTo(4, -35)
            arrow.closeSubpath()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#686a73'))
            painter.drawPath(arrow)
            painter.restore()

        # Símbolos vetoriais: o desenho não depende de glifos da fonte instalada.
        for dx, dy, code, symbol, color in ((0, -1, e.BTN_NORTH, 'triangle', '#64d3c1'),
                (1, 0, e.BTN_EAST, 'circle', '#ef8193'), (0, 1, e.BTN_SOUTH, 'cross', '#81bde7'),
                (-1, 0, e.BTN_WEST, 'square', '#d79ac8')):
            x, y = 310+dx*27, 102+dy*27
            active = code in keys
            disc(x, y, 13, '#50525a' if not active else accent.lighter(130).name(),
                 '#1c1e25' if not active else accent.darker(140).name(), '#08090d', 1.7)
            painter.setPen(QPen(QColor('#ffffff' if active else color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            if symbol == 'circle':
                painter.drawEllipse(QPointF(x, y), 8, 8)
            elif symbol == 'square':
                painter.drawRect(QRectF(x-7, y-7, 14, 14))
            elif symbol == 'cross':
                painter.drawLine(QPointF(x-7, y-7), QPointF(x+7, y+7))
                painter.drawLine(QPointF(x+7, y-7), QPointF(x-7, y+7))
            else:
                tri = QPainterPath()
                tri.moveTo(x, y-8)
                tri.lineTo(x+8, y+7)
                tri.lineTo(x-8, y+7)
                tri.closeSubpath()
                painter.drawPath(tri)

        # Share / Options, grelha do alto-falante e botão central.
        painter.setFont(QFont('Sans', 4.5, QFont.Bold))
        for x, key, label in ((126, e.BTN_SELECT, 'SHARE'), (274, e.BTN_START, 'OPTIONS')):
            painter.setPen(QPen(QColor('#08090d'), 1.3))
            painter.setBrush(accent if key in keys else gradient('#494b53', '#22242b', 53, 78))
            painter.drawRoundedRect(QRectF(x-4, 54, 8, 22), 4, 4)
            painter.setPen(QColor('#a7a8b0'))
            painter.drawText(QRectF(x-18, 44, 36, 8), Qt.AlignCenter, label)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#080a0f'))
        for row, count in enumerate((5, 4, 3)):
            for col in range(count):
                painter.drawEllipse(QPointF(200+(col-(count-1)/2)*6, 130+row*5), 1.65, 1.65)
        disc(200, 163, 9, '#41434b', '#101218', accent.name() if e.BTN_MODE in keys else '#080a0d')
        painter.setFont(QFont('Sans', 5.5, QFont.Bold))
        painter.setPen(QColor('#eceef5'))
        painter.drawText(QRectF(191, 154, 18, 18), Qt.AlignCenter, 'PS')
        painter.setPen(QPen(QColor('#3c3e46'), 0.8))
        painter.setBrush(QColor('#090b10'))
        painter.drawRoundedRect(QRectF(191, 181, 18, 2.5), 1.2, 1.2)

        # Analógicos: suporte, aro biselado, cavidade e tampa côncava móvel.
        for x, xcode, ycode, key in ((140, e.ABS_X, e.ABS_Y, e.BTN_THUMBL),
                                      (260, e.ABS_RX, e.ABS_RY, e.BTN_THUMBR)):
            y = 164
            disc(x, y, 34, '#4b4c54', '#24262d', '#111319')
            disc(x, y, 27, '#12141a', '#2b2d34', '#08090d', 1.7)
            ox = (axes.get(xcode, 0.5)-0.5)*14
            oy = (axes.get(ycode, 0.5)-0.5)*14
            active = key in keys
            disc(x+ox, y+oy, 23, '#61636d' if not active else accent.lighter(125).name(),
                 '#202229' if not active else accent.darker(130).name(), '#090b10', 1.5)
            disc(x+ox, y+oy, 17, '#1e2027', '#363840', '#4d4f59', 0.8)
        painter.end()

class BatteryBar(QWidget):
    """Barra de bateria com porcentagem; cinza quando sem leitura."""

    def __init__(self, theme='dark', parent=None):
        super().__init__(parent)
        self.palette_name = theme
        self.percent = None
        self.charging = False
        self.setFixedHeight(26)
        self.setMinimumWidth(150)

    def set_theme(self, name):
        self.palette_name = name
        self.update()

    def set_value(self, percent, charging=False):
        if (percent, charging) != (self.percent, self.charging):
            self.percent, self.charging = percent, charging
            self.update()

    def paintEvent(self, _):
        p = PALETTES[self.palette_name]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 3.5, self.width() - 6, self.height() - 7)
        painter.setPen(QPen(QColor(p['border']), 1.5))
        painter.setBrush(QColor(p['body']))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setBrush(QColor(p['border']))
        painter.drawRoundedRect(QRectF(self.width() - 5, 9, 4, self.height() - 18), 2, 2)
        if self.percent is not None:
            color = p['danger'] if self.percent <= 20 else p['ok'] if self.charging else p['accent']
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(2, 5, max(6, (rect.width() - 3) * self.percent / 100), self.height() - 10), 4, 4)
        painter.setPen(QColor(p['text']))
        painter.setFont(QFont('Sans', 9, QFont.Bold))
        label = 'sem leitura' if self.percent is None else f"{'⚡ ' if self.charging else ''}{self.percent}%"
        painter.drawText(rect, Qt.AlignCenter, label)
        painter.end()


class Swatch(QPushButton):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(26, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(color.upper())
        self.setStyleSheet(f'QPushButton{{background:{color};border:2px solid rgba(128,128,128,.45);border-radius:13px;padding:0}}'
                           'QPushButton:hover{border:2px solid #ffffff}')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(self.color))
        painter.setPen(QPen(QColor('#ffffff' if self.underMouse() else '#6c7791'), 2))
        painter.drawEllipse(QRectF(2, 2, self.width()-4, self.height()-4))
        painter.end()


class SwatchRow(QWidget):
    picked = Signal(str)

    def __init__(self, colors=PRESETS, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QHBoxLayout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        for color in colors:
            swatch = Swatch(color)
            swatch.clicked.connect(lambda _=False, c=color: self.picked.emit(c))
            layout.addWidget(swatch)
        layout.addStretch()
