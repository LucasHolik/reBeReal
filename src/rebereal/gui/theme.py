"""Centralized GUI theme — palette tokens, fonts, and the QSS builder.

The whole interface is styled from a single palette dict so alternative
themes (light, accented, high-contrast) drop in by passing a different
dict to ``build_stylesheet`` — no widget code changes. ``DARK`` is the
only palette shipped today (pure monochrome, near-black canvas).
"""

from __future__ import annotations

from pathlib import Path

# --- palettes -------------------------------------------------------------

# Pure dark monochrome. No hue, no gradients — hierarchy comes from value
# (near-black surfaces, white text, grey hairlines) and typography.
DARK: dict[str, str] = {
    "bg": "#0D0D0D",          # window canvas
    "panel": "#0D0D0D",       # sidebar (matches canvas; separated by a hairline)
    "surface": "#1A1A1A",     # inputs, log, troughs
    "line": "#2A2A2A",        # hairlines / borders
    "line_strong": "#3A3A3A", # hover / focus borders
    "text": "#F5F5F5",        # primary text + controls
    "muted": "#9A9A9A",       # secondary text, section labels
    "faint": "#6B6B6B",       # placeholders, disabled text
    # inverted primary button
    "accent": "#F5F5F5",
    "accent_hover": "#FFFFFF",
    "accent_pressed": "#E0E0E0",
    "on_accent": "#0D0D0D",
}

PALETTE = DARK

# Font stacks — system-native first so it never looks like a web font drop-in.
FONTS: dict[str, str] = {
    # UI font is left to Qt's native system default (set in app.main); only the
    # monospace stack is declared. "Menlo" leads because it ships on every macOS
    # and Qt resolves it by name (Qt does not expose "SF Mono" under that name).
    "mono": '"Menlo", "SF Mono", "JetBrains Mono", "Consolas", monospace',
}

# Absolute path to the checkmark glyph, injected into the QSS so url()
# resolves regardless of the process working directory.
_ASSETS = Path(__file__).parent / "assets"
_CHECK_SVG = (_ASSETS / "check.svg").as_posix()
_CHEVRON_SVG = (_ASSETS / "chevron.svg").as_posix()


def build_stylesheet(palette: dict[str, str] = PALETTE) -> str:
    """Return the full application QSS for ``palette``."""
    p = palette
    mono = FONTS["mono"]
    # No base font-family — Qt's default is already the native system UI font
    # (San Francisco on macOS). Setting "-apple-system" (a CSS keyword Qt does
    # not resolve) only triggers a fallback warning. Mono is set explicitly
    # where it's wanted, using families that actually exist.
    return f"""
* {{
    color: {p['text']};
    font-size: 13px;
}}

QMainWindow, QWidget {{
    background-color: {p['bg']};
}}

/* --- sidebar ---------------------------------------------------------- */

QFrame#Sidebar {{
    background-color: {p['panel']};
    border-right: 1px solid {p['line']};
}}

QLabel#Wordmark {{
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.5px;
}}

QLabel#Tagline {{
    color: {p['muted']};
    font-size: 12px;
}}

QLabel#SectionLabel {{
    color: {p['muted']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
}}

QLabel#FieldLabel {{
    color: {p['muted']};
    font-size: 12px;
}}

QFrame#Rule {{
    background-color: {p['line']};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* --- text inputs ----------------------------------------------------- */

QLineEdit, QComboBox, QSpinBox {{
    background-color: {p['surface']};
    border: 1px solid {p['line']};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {p['text']};
    selection-color: {p['bg']};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {p['text']};
}}

QLineEdit::placeholder {{
    color: {p['faint']};
}}

QComboBox {{
    padding-right: 30px;
}}
QComboBox:hover {{
    border: 1px solid {p['line_strong']};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border: none;
    border-left: 1px solid {p['line']};
}}
QComboBox::down-arrow {{
    image: url({_CHEVRON_SVG});
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {p['surface']};
    border: 1px solid {p['line']};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {p['line']};
    selection-color: {p['text']};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 26px;
    padding: 2px 8px;
    border-radius: 4px;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {p['line']};
    color: {p['text']};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 0px;
    border: none;
}}

/* --- buttons --------------------------------------------------------- */

QPushButton#PrimaryButton {{
    background-color: {p['accent']};
    color: {p['on_accent']};
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background-color: {p['accent_hover']}; }}
QPushButton#PrimaryButton:pressed {{ background-color: {p['accent_pressed']}; }}
QPushButton#PrimaryButton:disabled {{
    background-color: {p['line']};
    color: {p['faint']};
}}

QPushButton#GhostButton {{
    background-color: transparent;
    color: {p['text']};
    border: 1px solid {p['line']};
    border-radius: 6px;
    padding: 8px 14px;
}}
QPushButton#GhostButton:hover {{
    border: 1px solid {p['line_strong']};
    background-color: {p['surface']};
}}
QPushButton#GhostButton:pressed {{ background-color: {p['line']}; }}
QPushButton#GhostButton:disabled {{ color: {p['faint']}; }}

/* --- checkboxes ------------------------------------------------------ */

QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p['line_strong']};
    border-radius: 4px;
    background-color: {p['bg']};
}}
QCheckBox::indicator:checked {{
    background-color: {p['bg']};
    image: url({_CHECK_SVG});
}}
QCheckBox::indicator:hover, QCheckBox::indicator:checked:hover {{
    border: 1px solid {p['text']};
}}

/* --- slider ---------------------------------------------------------- */

QSlider::groove:horizontal {{
    height: 2px;
    background: {p['line']};
    border-radius: 1px;
}}
QSlider::sub-page:horizontal {{
    background: {p['text']};
    height: 2px;
    border-radius: 1px;
}}
QSlider::handle:horizontal {{
    background: {p['text']};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}

/* --- progress -------------------------------------------------------- */

QProgressBar {{
    background-color: {p['surface']};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {p['text']};
    border-radius: 3px;
}}

/* --- readouts, status, log ------------------------------------------ */

QLabel#ValueReadout {{
    font-family: {mono};
    color: {p['text']};
}}

QLabel#StatusLabel {{
    font-family: {mono};
    font-size: 12px;
    color: {p['muted']};
}}

QPlainTextEdit#LogView {{
    background-color: {p['surface']};
    border: 1px solid {p['line']};
    border-radius: 6px;
    font-family: {mono};
    font-size: 12px;
    color: {p['text']};
    padding: 8px;
}}

/* --- preview --------------------------------------------------------- */

QLabel#Placeholder {{
    color: {p['faint']};
}}

QLabel#Thumb {{
    border: 1px solid {p['line']};
    background-color: {p['surface']};
}}

QLabel#ThumbCaption {{
    color: {p['muted']};
    font-family: {mono};
    font-size: 11px;
}}

/* --- scrollbars ------------------------------------------------------ */

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p['line']};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {p['line_strong']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {p['line']};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {p['line_strong']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* --- splitter -------------------------------------------------------- */

QSplitter::handle {{
    background-color: {p['line']};
}}
QSplitter::handle:vertical {{ height: 1px; }}
"""
