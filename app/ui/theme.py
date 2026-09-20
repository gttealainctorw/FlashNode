"""Design tokens and the application stylesheet.

Everything visual (colors, spacing, radii, typography) is defined once here.
The QSS is generated from these tokens so there is a single source of truth:
change a token, and every component picks it up.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #

class Colors:
    # Backgrounds (darkest -> lightest)
    WELL = "#0B0D11"            # console / deep wells
    BG = "#0F1115"              # application background
    BG_ELEVATED = "#13161C"     # top bar, status bar, toolbars
    SURFACE = "#171A21"         # cards, rows, inputs
    SURFACE_HOVER = "#1C2029"
    SURFACE_ACTIVE = "#20252F"

    # Borders
    BORDER = "#262B35"
    BORDER_STRONG = "#343A47"

    # Text
    TEXT = "#E6E8EC"
    TEXT_SECONDARY = "#9AA3B2"
    TEXT_MUTED = "#6B7382"
    TEXT_DISABLED = "#4A515E"
    TEXT_ON_PRIMARY = "#FFFFFF"

    # Brand / primary
    PRIMARY = "#4F8CFF"
    PRIMARY_HOVER = "#6AA0FF"
    PRIMARY_ACTIVE = "#3B78EA"
    PRIMARY_SOFT = "rgba(79, 140, 255, 0.14)"
    PRIMARY_BORDER = "rgba(79, 140, 255, 0.55)"

    # Semantic
    SUCCESS = "#3DD68C"
    SUCCESS_SOFT = "rgba(61, 214, 140, 0.14)"
    WARNING = "#F5B94A"
    WARNING_SOFT = "rgba(245, 185, 74, 0.14)"
    ERROR = "#F0605E"
    ERROR_SOFT = "rgba(240, 96, 94, 0.14)"
    INFO = PRIMARY
    INFO_SOFT = PRIMARY_SOFT
    NEUTRAL_SOFT = "rgba(154, 163, 178, 0.12)"


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24
    XXXL = 32


class Radius:
    SM = 6      # controls: buttons, inputs, badges
    MD = 8      # rows, console


class Sizes:
    CONTROL = 32        # default control height
    CONTROL_LG = 36     # primary call-to-action
    ROW = 56            # device row height
    TOPBAR = 56
    STATUSBAR = 30
    ICON = 16


class Typography:
    FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "Arial"]
    MONO_FAMILIES = ["Cascadia Mono", "Consolas", "JetBrains Mono", "Menlo", "monospace"]

    TITLE = 17          # window / page titles
    HEADING = 14        # section headings
    BODY = 13
    SECONDARY = 12
    CAPTION = 11
    MONO = 12


# Semantic tone -> (foreground, soft background). Used by Badge, StatusDot, ProgressBar.
TONES = {
    "neutral": (Colors.TEXT_SECONDARY, Colors.NEUTRAL_SOFT),
    "primary": (Colors.PRIMARY, Colors.PRIMARY_SOFT),
    "success": (Colors.SUCCESS, Colors.SUCCESS_SOFT),
    "warning": (Colors.WARNING, Colors.WARNING_SOFT),
    "error": (Colors.ERROR, Colors.ERROR_SOFT),
    "info": (Colors.INFO, Colors.INFO_SOFT),
}


# --------------------------------------------------------------------------- #
# Fonts
# --------------------------------------------------------------------------- #

def font(size: int = Typography.BODY, weight: int = QFont.Weight.Normal,
         families: list[str] | None = None) -> QFont:
    """Build a QFont from the typography tokens with family fallback."""
    f = QFont()
    f.setFamilies(families or Typography.FAMILIES)
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


def mono_font(size: int = Typography.MONO) -> QFont:
    return font(size, families=Typography.MONO_FAMILIES)


# --------------------------------------------------------------------------- #
# Stylesheet
# --------------------------------------------------------------------------- #

def _tone_rules(selector: str, prop: str) -> str:
    """Generate `[tone="x"]` rules (text on soft background) from the TONES table."""
    rules = []
    for name, (fg, soft) in TONES.items():
        rules.append(f'{selector}[{prop}="{name}"] {{ color: {fg}; background-color: {soft}; }}')
    return "\n".join(rules)


def build_stylesheet() -> str:
    c, s, r, z, t = Colors, Spacing, Radius, Sizes, Typography

    return f"""
/* ============================================================ */
/* Base                                                          */
/* ============================================================ */
QWidget {{
    color: {c.TEXT};
    font-size: {t.BODY}px;
    selection-background-color: {c.PRIMARY};
    selection-color: {c.TEXT_ON_PRIMARY};
}}
QWidget:disabled {{ color: {c.TEXT_DISABLED}; }}

MainWindow {{ background-color: {c.BG}; }}
QToolTip {{
    background-color: {c.SURFACE_ACTIVE};
    color: {c.TEXT};
    border: 1px solid {c.BORDER_STRONG};
    border-radius: {r.SM}px;
    padding: {s.XS}px {s.SM}px;
}}

/* ============================================================ */
/* Layout chrome                                                 */
/* ============================================================ */
TopBar {{
    background-color: {c.BG_ELEVATED};
    border-bottom: 1px solid {c.BORDER};
}}
StatusBar {{
    background-color: {c.BG_ELEVATED};
    border-top: 1px solid {c.BORDER};
}}
QLabel#appName {{ font-size: {t.HEADING}px; font-weight: 600; }}
QLabel#appTagline {{ font-size: {t.SECONDARY}px; color: {c.TEXT_MUTED}; }}
QLabel#appLogo {{ background: transparent; }}

/* ============================================================ */
/* Typography helpers                                            */
/* ============================================================ */
QLabel#pageTitle {{ font-size: {t.TITLE}px; font-weight: 600; }}
QLabel#sectionTitle {{ font-size: {t.HEADING}px; font-weight: 600; }}
QLabel#secondary {{ color: {c.TEXT_SECONDARY}; font-size: {t.SECONDARY}px; }}
QLabel#muted {{ color: {c.TEXT_MUTED}; font-size: {t.SECONDARY}px; }}
QLabel#caption {{ color: {c.TEXT_MUTED}; font-size: {t.CAPTION}px; }}

/* ============================================================ */
/* Buttons                                                       */
/* ============================================================ */
QPushButton {{
    background-color: {c.SURFACE};
    color: {c.TEXT};
    border: 1px solid {c.BORDER_STRONG};
    border-radius: {r.SM}px;
    padding: 0 {s.MD}px;
    min-height: {z.CONTROL}px;
    max-height: {z.CONTROL}px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: {c.SURFACE_HOVER}; border-color: {c.BORDER_STRONG}; }}
QPushButton:pressed {{ background-color: {c.SURFACE_ACTIVE}; }}
QPushButton:focus {{ outline: none; border-color: {c.PRIMARY_BORDER}; }}
QPushButton:disabled {{
    background-color: {c.SURFACE};
    color: {c.TEXT_DISABLED};
    border-color: {c.BORDER};
}}

Button[variant="primary"] {{
    background-color: {c.PRIMARY};
    color: {c.TEXT_ON_PRIMARY};
    border: 1px solid {c.PRIMARY};
    font-weight: 600;
}}
Button[variant="primary"]:hover {{ background-color: {c.PRIMARY_HOVER}; border-color: {c.PRIMARY_HOVER}; }}
Button[variant="primary"]:pressed {{ background-color: {c.PRIMARY_ACTIVE}; border-color: {c.PRIMARY_ACTIVE}; }}
Button[variant="primary"]:focus {{ border-color: {c.TEXT_ON_PRIMARY}; }}
Button[variant="primary"]:disabled {{
    background-color: {c.SURFACE_ACTIVE};
    color: {c.TEXT_DISABLED};
    border-color: {c.SURFACE_ACTIVE};
}}

Button[variant="ghost"] {{
    background-color: transparent;
    color: {c.TEXT_SECONDARY};
    border: 1px solid transparent;
}}
Button[variant="ghost"]:hover {{ background-color: {c.SURFACE_HOVER}; color: {c.TEXT}; }}
Button[variant="ghost"]:pressed {{ background-color: {c.SURFACE_ACTIVE}; }}
Button[variant="ghost"]:disabled {{ background-color: transparent; color: {c.TEXT_DISABLED}; }}

Button[variant="danger"] {{
    background-color: transparent;
    color: {c.ERROR};
    border: 1px solid {c.BORDER_STRONG};
}}
Button[variant="danger"]:hover {{ background-color: {c.ERROR_SOFT}; border-color: {c.ERROR}; }}

Button[size="lg"] {{
    min-height: {z.CONTROL_LG}px;
    max-height: {z.CONTROL_LG}px;
    padding: 0 {s.LG}px;
}}
Button[size="sm"] {{
    min-height: 26px;
    max-height: 26px;
    padding: 0 {s.SM}px;
    font-size: {t.SECONDARY}px;
}}

/* Text-only link buttons (e.g. "Select all") */
LinkButton {{
    background: transparent;
    border: none;
    color: {c.TEXT_SECONDARY};
    font-size: {t.SECONDARY}px;
    font-weight: 500;
    padding: 0 {s.XS}px;
    min-height: 22px;
    max-height: 22px;
}}
LinkButton:hover {{ background: transparent; border: none; color: {c.PRIMARY}; }}
LinkButton:pressed {{ background: transparent; border: none; color: {c.PRIMARY_ACTIVE}; }}
LinkButton:focus {{ background: transparent; border: none; text-decoration: underline; }}
LinkButton:disabled {{ background: transparent; border: none; color: {c.TEXT_DISABLED}; }}

/* ============================================================ */
/* Badges & status                                               */
/* ============================================================ */
Badge {{
    border-radius: {r.SM}px;
    padding: 2px {s.SM}px;
    font-size: {t.CAPTION}px;
    font-weight: 600;
    min-height: 18px;
    max-height: 18px;
}}
{_tone_rules("Badge", "tone")}

StatusDot {{ border-radius: 4px; min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px; }}
StatusDot[tone="neutral"] {{ background-color: {c.TEXT_MUTED}; }}
StatusDot[tone="primary"] {{ background-color: {c.PRIMARY}; }}
StatusDot[tone="success"] {{ background-color: {c.SUCCESS}; }}
StatusDot[tone="warning"] {{ background-color: {c.WARNING}; }}
StatusDot[tone="error"] {{ background-color: {c.ERROR}; }}
StatusDot[tone="info"] {{ background-color: {c.INFO}; }}

/* ============================================================ */
/* Progress                                                      */
/* ============================================================ */
ProgressBar {{
    background-color: {c.SURFACE_ACTIVE};
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
}}
ProgressBar::chunk {{ background-color: {c.PRIMARY}; border-radius: 3px; }}
ProgressBar[tone="success"]::chunk {{ background-color: {c.SUCCESS}; }}
ProgressBar[tone="warning"]::chunk {{ background-color: {c.WARNING}; }}
ProgressBar[tone="error"]::chunk {{ background-color: {c.ERROR}; }}
ProgressBar[tone="neutral"]::chunk {{ background-color: {c.BORDER_STRONG}; }}

/* ============================================================ */
/* Device rows                                                   */
/* ============================================================ */
DeviceRow {{
    background-color: {c.SURFACE};
    border: 1px solid {c.BORDER};
    border-radius: {r.MD}px;
}}
DeviceRow:hover {{ background-color: {c.SURFACE_HOVER}; border-color: {c.BORDER_STRONG}; }}
DeviceRow[selected="true"] {{
    background-color: {c.PRIMARY_SOFT};
    border-color: {c.PRIMARY_BORDER};
}}
DeviceRow[selected="true"]:hover {{ border-color: {c.PRIMARY}; }}
/* Job states override the selection tint (also on hover) so "selected" and
   "flashing/done/error" always read differently */
DeviceRow[state="busy"], DeviceRow[state="busy"]:hover,
DeviceRow[state="flashing"], DeviceRow[state="flashing"]:hover {{
    background-color: {c.SURFACE};
    border-color: {c.PRIMARY};
}}
DeviceRow[state="queued"], DeviceRow[state="queued"]:hover {{
    background-color: {c.SURFACE};
    border-color: {c.BORDER_STRONG};
}}
DeviceRow[state="done"], DeviceRow[state="done"]:hover {{
    background-color: {c.SURFACE};
    border-color: rgba(61, 214, 140, 0.55);
}}
DeviceRow[state="error"], DeviceRow[state="error"]:hover {{
    background-color: {c.SURFACE};
    border-color: rgba(240, 96, 94, 0.6);
}}
DeviceRow QLabel#port {{ font-size: {t.BODY}px; font-weight: 600; }}
DeviceRow QLabel#description {{ font-size: {t.CAPTION}px; color: {c.TEXT_MUTED}; }}
DeviceRow QLabel#statusText {{ font-size: {t.SECONDARY}px; color: {c.TEXT_SECONDARY}; }}
DeviceRow QLabel#statusText[tone="success"] {{ color: {c.SUCCESS}; }}
DeviceRow QLabel#statusText[tone="error"] {{ color: {c.ERROR}; }}
DeviceRow QLabel#statusText[tone="warning"] {{ color: {c.WARNING}; }}
DeviceRow QLabel#statusText[tone="primary"] {{ color: {c.PRIMARY}; }}
DeviceRow QLabel#statusText[tone="neutral"] {{ color: {c.TEXT_MUTED}; }}

/* ============================================================ */
/* Scroll areas & scrollbars                                     */
/* ============================================================ */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QAbstractScrollArea {{ background: transparent; }}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 2px 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {c.BORDER_STRONG};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {c.TEXT_DISABLED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: none; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 2px 2px 2px;
}}
QScrollBar::handle:horizontal {{
    background: {c.BORDER_STRONG};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c.TEXT_DISABLED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: none; border: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* ============================================================ */
/* Console                                                       */
/* ============================================================ */
ConsoleView {{
    background-color: {c.WELL};
    color: {c.TEXT_SECONDARY};
    border: 1px solid {c.BORDER};
    border-radius: {r.MD}px;
    padding: {s.SM}px {s.MD}px;
}}

/* ============================================================ */
/* Splitter                                                      */
/* ============================================================ */
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:vertical {{ height: {s.SM}px; }}
QSplitter::handle:horizontal {{ width: {s.SM}px; }}
QSplitter::handle:hover {{ background: {c.PRIMARY_SOFT}; }}

/* ============================================================ */
/* Dialogs                                                       */
/* ============================================================ */
QMessageBox {{ background-color: {c.BG_ELEVATED}; }}
QMessageBox QLabel {{ color: {c.TEXT}; font-size: {t.BODY}px; }}
QMessageBox QPushButton {{ min-width: 80px; }}
"""


# --------------------------------------------------------------------------- #
# Application-level setup
# --------------------------------------------------------------------------- #

def _palette() -> QPalette:
    """Dark palette so anything not covered by the stylesheet still matches."""
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: Colors.BG,
        QPalette.ColorRole.WindowText: Colors.TEXT,
        QPalette.ColorRole.Base: Colors.SURFACE,
        QPalette.ColorRole.AlternateBase: Colors.SURFACE_HOVER,
        QPalette.ColorRole.Text: Colors.TEXT,
        QPalette.ColorRole.Button: Colors.SURFACE,
        QPalette.ColorRole.ButtonText: Colors.TEXT,
        QPalette.ColorRole.Highlight: Colors.PRIMARY,
        QPalette.ColorRole.HighlightedText: Colors.TEXT_ON_PRIMARY,
        QPalette.ColorRole.ToolTipBase: Colors.SURFACE_ACTIVE,
        QPalette.ColorRole.ToolTipText: Colors.TEXT,
        QPalette.ColorRole.PlaceholderText: Colors.TEXT_MUTED,
        QPalette.ColorRole.Link: Colors.PRIMARY,
        QPalette.ColorRole.Mid: Colors.BORDER,
        QPalette.ColorRole.Dark: Colors.WELL,
        QPalette.ColorRole.Light: Colors.SURFACE_ACTIVE,
    }
    for role, color in roles.items():
        p.setColor(role, QColor(color))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(Colors.TEXT_DISABLED))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(Colors.TEXT_DISABLED))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(Colors.TEXT_DISABLED))
    return p


def apply_theme(app: QApplication) -> None:
    """Install the design system on the application: style, palette, font, QSS."""
    app.setStyle("Fusion")          # predictable rendering of stylesheets on every platform
    app.setPalette(_palette())
    app.setFont(font(Typography.BODY))
    app.setStyleSheet(build_stylesheet())
