"""Font Awesome 6 Free - font loader and icon codepoint constants.

Call load_fonts() once after QApplication is created (done in __main__.py).
Use fa(size) / fa_reg(size) wherever QFont("Segoe Fluent Icons", size) was used.
QSS stylesheets: replace the Segoe font-family line with FA_SOLID_CSS.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase

_FONT_DIR = Path(__file__).parent.parent / "resources" / "fonts"

_SOLID_FAMILY: str = "Font Awesome 6 Free"
_REG_FAMILY: str = "Font Awesome 6 Free"


def load_fonts() -> None:
    """Register the bundled FA6 .otf files with Qt. Call once at startup."""
    global _SOLID_FAMILY, _REG_FAMILY
    solid = _FONT_DIR / "fa-solid-900.otf"
    regular = _FONT_DIR / "fa-regular-400.otf"
    if solid.exists():
        fid = QFontDatabase.addApplicationFont(str(solid))
        fams = QFontDatabase.applicationFontFamilies(fid)
        if fams:
            _SOLID_FAMILY = fams[0]
    if regular.exists():
        fid = QFontDatabase.addApplicationFont(str(regular))
        fams = QFontDatabase.applicationFontFamilies(fid)
        if fams:
            _REG_FAMILY = fams[0]


def fa(size: int) -> QFont:
    """QFont for Font Awesome 6 Free Solid."""
    f = QFont(_SOLID_FAMILY)
    f.setPointSize(size)
    f.setStyleName("Solid")
    return f


def fa_reg(size: int) -> QFont:
    """QFont for Font Awesome 6 Free Regular."""
    f = QFont(_REG_FAMILY)
    f.setPointSize(size)
    f.setStyleName("Regular")
    return f


# QSS font snippet - drop into any stylesheet that uses icon text
FA_SOLID_CSS = "font-family:'Font Awesome 6 Free';font-weight:900;"

# -- Window chrome ------------------------------------------------------------
ICON_CLOSE = ""  # xmark
ICON_MINIMIZE = ""  # window-minimize
ICON_MAXIMIZE = ""  # window-maximize
ICON_RESTORE = ""  # window-restore
ICON_BACK = ""  # chevron-left
ICON_MINUS = ""  # minus (regular weight)

# -- Navigation rail ----------------------------------------------------------
ICON_DASHBOARD = ""  # gauge-high
ICON_FOLDERS = ""  # folder
ICON_INVENTORY = ""  # list
ICON_MANAGE = ""  # wrench
ICON_TESTING = ""  # flask
ICON_ACTIVITY = ""  # chart-line
ICON_OPTIONS = ""  # gear
ICON_ABOUT = ""  # circle-info
ICON_EXIT = ""  # right-from-bracket

# -- Dashboard widget headers -------------------------------------------------
ICON_HERO = ""  # chart-line (hero metrics)
ICON_INTEGRATION = ""  # plug
ICON_SECURITY = ""  # shield
ICON_SHIELD_HALVED = ""  # shield-halved
ICON_ACTION_ITEMS = ""  # triangle-exclamation
ICON_AI_USAGE = ""  # robot
ICON_UPDATES = ""  # bell
ICON_BELL = ""  # bell (alerts)
ICON_RECENT = ""  # clock-rotate-left
ICON_LIBRARY = ""  # book
ICON_SCAN_VEL = ""  # bolt
ICON_AI_BOM = ""  # microchip
ICON_TRUST = ""  # heart-pulse
ICON_SYS_SETUP = ""  # gears
ICON_QUICK = ""  # bolt

# -- Skill Manager buttons ----------------------------------------------------
ICON_LOAD_FILE = ""  # folder-open
ICON_PASTE = ""  # clipboard
ICON_OPTIMIZE = ""  # wand-magic
ICON_REVIEW = ""  # eye
ICON_SCAN = ""  # arrows-rotate
ICON_SAVE = ""  # floppy-disk
ICON_BUILD = ""  # box-archive

# -- Folders view -------------------------------------------------------------
ICON_GRID_SM = ""  # table-cells (th)
ICON_GRID_LG = ""  # table-cells-large (th-large)
ICON_LIST_VIEW = ""  # list

# -- General ------------------------------------------------------------------
ICON_MENU = ""  # bars (hamburger)
ICON_REMOVE = ""  # xmark
ICON_SORT = ""  # sort
ICON_FILTER = ""  # filter
ICON_SEARCH = ""  # magnifying-glass
ICON_PLUS = ""  # plus
ICON_TRASH = ""  # trash
ICON_EDIT_PEN = ""  # pen-to-square
ICON_COPY = ""  # copy
ICON_EYE = ""  # eye
ICON_LOCK = ""  # lock
ICON_UNLOCK = ""  # lock-open
ICON_KEY = ""  # key
ICON_ELLIPSIS = ""  # ellipsis
ICON_CHEVRON_RIGHT = ""  # chevron-right
ICON_CHEVRON_DOWN = ""  # chevron-down
ICON_CHEVRON_UP = ""  # chevron-up
ICON_CIRCLE = ""  # circle (solid dot)
ICON_WARNING = ""  # triangle-exclamation
ICON_CHECK = ""  # check
ICON_INFO = ""  # circle-info
ICON_CIRCLE_QUESTION = ""  # circle-question (help)
ICON_RIGHT_LEFT = ""  # right-left (compare / toggle)
ICON_BULLHORN = ""  # bullhorn (status indicator)
ICON_NEW_SKILL = ""  # square-plus (new skill)
