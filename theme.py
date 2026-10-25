"""Temas claro/escuro e folha de estilo do PS4 Control."""
import json
from pathlib import Path

from profiles import CONFIG

UI_CONFIG = CONFIG.with_name('ui.json')

PALETTES = {
    'dark': dict(bg='#10131c', card='#191e2b', card2='#252c3d', border='#30384b', text='#eff2fb',
                 muted='#8d9abb', accent='#6c8cff', accent_text='#ffffff', ok='#45bd91',
                 warn='#e0a458', danger='#ff8f98', body='#232d47', hover='#2c3a5e'),
    'light': dict(bg='#f1f4fb', card='#ffffff', card2='#eaeefa', border='#d2d9ec', text='#1b2236',
                  muted='#5d6a88', accent='#3f63e6', accent_text='#ffffff', ok='#1f9d72',
                  warn='#b97a1d', danger='#c93a46', body='#dfe5f6', hover='#dde4f8'),
}


def load_theme():
    try:
        value = json.loads(UI_CONFIG.read_text()).get('theme')
        return value if value in PALETTES else 'dark'
    except (OSError, ValueError, AttributeError):
        return 'dark'


def save_theme(name):
    try:
        UI_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        UI_CONFIG.write_text(json.dumps(dict(theme=name)))
    except OSError:
        pass


def stylesheet(name):
    p = PALETTES[name]
    return f'''
    QWidget {{background:{p['bg']};color:{p['text']};font-size:14px}}
    QLabel {{background:transparent}}
    QLabel#title {{font-size:28px;font-weight:700;letter-spacing:-0.5px}}
    QLabel#brand {{font-size:20px;font-weight:700}}
    QFrame#sidebar {{background:{p['card']};border-right:1px solid {p['border']}}}
    QFrame#sidebar QLabel, QFrame#sidebar QListWidget {{background:transparent}}
    QListWidget#navigation::item {{padding:13px 14px;border-radius:10px;color:{p['muted']}}}
    QListWidget#navigation::item:selected {{background:{p['accent']};color:white;font-weight:700}}
    QFrame#hero {{background:{p['card']};border:1px solid {p['border']};border-radius:18px}}
    QFrame#hero QLabel {{background:transparent}}
    QLabel#pill {{background:{p['card2']};color:{p['text']};border-radius:10px;padding:10px 16px}}
    QScrollArea, QScrollArea > QWidget > QWidget {{border:none}}
    QScrollBar:vertical {{background:transparent;width:8px;margin:2px}}
    QScrollBar::handle:vertical {{background:{p['border']};border-radius:4px;min-height:32px}}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{height:0}}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{background:transparent}}
    QPushButton {{min-height:20px}}
    QPushButton:focus, QComboBox:focus {{border:1px solid {p['accent']}}}
    QLabel#subtitle, QLabel#muted {{color:{p['muted']}}}
    QLabel#section {{font-size:12px;font-weight:700;color:{p['muted']};letter-spacing:1px}}
    QLabel#value {{color:{p['muted']};min-width:44px}}
    QLabel#error {{color:{p['danger']}}}
    QLabel#status {{color:{p['muted']}}}
    QFrame#card {{background:{p['card']};border:1px solid {p['border']};border-radius:14px}}
    QFrame#card QLabel, QFrame#card QWidget#plain {{background:transparent}}
    QPushButton, QComboBox {{background:{p['card2']};border:1px solid {p['border']};border-radius:8px;padding:8px 14px}}
    QPushButton:hover, QComboBox:hover {{background:{p['hover']}}}
    QPushButton:disabled {{color:{p['muted']}}}
    QPushButton#primary {{background:{p['accent']};color:{p['accent_text']};border:none;font-weight:700;padding:10px 22px}}
    QPushButton#primary:hover {{background:{p['accent']}}}
    QPushButton#danger {{color:{p['danger']}}}
    QPushButton#ghost {{background:transparent;border:1px solid {p['border']}}}
    QComboBox QAbstractItemView {{background:{p['card']};selection-background-color:{p['accent']};border:1px solid {p['border']}}}
    QTabWidget::pane {{border:none;top:8px}}
    QTabBar {{background:transparent}}
    QTabBar::tab {{background:transparent;color:{p['muted']};padding:9px 18px;margin-right:4px;border-radius:8px;font-weight:600}}
    QTabBar::tab:selected {{background:{p['card']};color:{p['text']};border:1px solid {p['border']}}}
    QTabBar::tab:hover:!selected {{color:{p['text']}}}
    QSlider::groove:horizontal {{height:6px;background:{p['body']};border-radius:3px}}
    QSlider::sub-page:horizontal {{background:{p['accent']};border-radius:3px}}
    QSlider::handle:horizontal {{background:{p['accent']};width:18px;margin:-6px 0;border-radius:9px;border:2px solid {p['card']}}}
    QSlider::handle:horizontal:disabled {{background:{p['muted']}}}
    QProgressBar {{background:{p['body']};border:none;border-radius:5px;height:10px;text-align:center;color:{p['muted']};font-size:11px}}
    QProgressBar::chunk {{background:{p['accent']};border-radius:5px}}
    QListWidget {{background:transparent;border:none;outline:none}}
    QListWidget::item {{padding:10px 12px;border-radius:8px;margin:2px 0}}
    QListWidget::item:selected {{background:{p['accent']};color:{p['accent_text']}}}
    QListWidget::item:hover:!selected {{background:{p['hover']}}}
    QToolTip {{background:{p['card']};color:{p['text']};border:1px solid {p['border']}}}
    '''
