"""SkillScan UI colour palette — single source of truth.

Derived from Palette.md in the Obsidian vault:
  03. Projects / Development / SkillScan - AI Skill Scanning Tool / palette.md

Every colour used anywhere in the UI must reference a token from this module.
Never hardcode hex strings in UI files.
"""

# ── Primary tokens (SYS_* naming — use these in all new and refactored code) ──

# Backgrounds
SYS_BG_PRIMARY = "#0F172A"  # 60% base — canvas, main bars, tooltips
SYS_BG_SECONDARY = "#1E293B"  # 30% structure — panels, rail, toolbar, menus
SYS_BG_ROW_HOVER = "#162033"  # list / row hover (subdued)
SYS_HEADER_BG = "#0F172A"  # QHeaderView section background

# Text
SYS_TXT_PRIMARY = "#F0FDFA"  # primary reading text, labels
SYS_TXT_SECONDARY = "#CBD5E1"  # secondary text — tile descriptions, badge labels
SYS_TXT_MUTED = "#475569"  # captions, metadata, disabled, status bar
SYS_CONTROL_TXT = "#F0FDFA"  # menu item text, combo selected text
SYS_CONTROL_TXT_MUTED = "#475569"  # inactive button icons, combo placeholder

# Actions / focal
SYS_ACTION_PRIMARY = "#0D9488"  # CTA buttons, active nav, active toggles
SYS_ACTION_HOVER = "#0F766E"  # hover on action elements
SYS_CONTROL_BG_ACCENT_HOVER = "#0D9488"  # context menu item hover (accent fill)

# Strokes / borders
SYS_STROKE_DIVIDER = "#243846"  # 1px HLine / VLine dividers
SYS_STROKE_SUBTLE = "#334155"  # badge borders, combo borders, scrollbar handle

# Tile backgrounds
SYS_TILE_BG_UNSCANNED = "#475569"  # unscanned tile card background
SYS_TILE_BG_HOVER = "#3D4D5E"  # tile card hover background

# Interactive states
SYS_CONTROL_BG = "#1E293B"  # QMenu, QLineEdit, QComboBox dropdown bg
SYS_CONTROL_BG_HOVER_ALPHA = "rgba(30,41,59,200)"  # nav rail item hover overlay
SYS_CONTROL_BG_PRESSED = "#263347"  # minimise button pressed
SYS_CONTROL_BG_CRITICAL_PRESSED = "#B91C1C"  # close button pressed

# Scrollbar
SYS_SCROLL_TRACK = "#0F172A"  # scrollbar track background
SYS_SCROLL_HANDLE = "#334155"  # scrollbar thumb
SYS_SCROLL_BUTTON = "#475569"  # scrollbar arrow buttons

# Tooltip
SYS_TOOLTIP_BG = "#0F172A"  # QToolTip background
SYS_TOOLTIP_TXT = "#F0FDFA"  # QToolTip text

# Progress
SYS_PROGRESS_BAR_FILL = "#0D9488"  # QProgressBar chunk fill
SYS_TXT_SCAN_PROGRESS = "#D97706"  # scan progress label text (amber)

# Status dots
SYS_STATUS_DOT_OK = "#10B981"  # nominal / ready
SYS_STATUS_DOT_WARNING = "#EA580C"  # warning state
SYS_STATUS_DOT_CRITICAL = "#E11D48"  # critical / error state

# ── Cyber alert severity system ──────────────────────────────────────────────

# CRITICAL (P1) — Red
SYS_BADGE_UNSAFE = "#E11D48"
SYS_BORDER_CRITICAL = "#E11D48"
SYS_CRITICAL_BG = "#2D1217"
SYS_CRITICAL_LIGHT = "#FFF1F2"

# WARNING / HIGH (P2) — Orange
SYS_BORDER_WARNING = "#EA580C"
SYS_HIGH_BG = "#2D1A10"
SYS_HIGH_LIGHT = "#FFF7ED"
SYS_BG_WARNING = "#FFF7ED"  # light warning fill — CLEAN badge background

# ADVISORY / MEDIUM (P3) — Amber
SYS_BORDER_ADVISORY = "#D97706"
SYS_MEDIUM_BG = "#2A200E"
SYS_MEDIUM_LIGHT = "#FEF3C7"

# SAFE / PASS — Emerald
SYS_BADGE_SAFE = "#059669"
SYS_BORDER_SAFE = "#059669"
SYS_SAFE_BG = "#022C22"
SYS_SAFE_LIGHT = "#D1FAE5"

# LOW severity — subdued
SYS_BORDER_LOW = "#CCFBF1"  # low-severity tile border / link colour
SYS_LOW_BG = SYS_BG_SECONDARY

# ── Backward-compat aliases (do not use in new code) ─────────────────────────

ANCHOR = SYS_BG_PRIMARY
DEEP_SURFACE = SYS_BG_SECONDARY
LIGHT_CANVAS = SYS_TXT_PRIMARY
MUTED_TEXT = SYS_TXT_MUTED
ACCENT = SYS_ACTION_PRIMARY
HOVER_FOCUS = SYS_ACTION_HOVER
DIVIDER = SYS_STROKE_DIVIDER
SOFT_SURFACE = SYS_BORDER_LOW
LOW_BORDER = "#99F6E4"  # kept — no SYS_* equivalent yet
CRITICAL_ACCENT = SYS_BADGE_UNSAFE
CRITICAL_BG = SYS_CRITICAL_BG
CRITICAL_LIGHT = SYS_CRITICAL_LIGHT
HIGH_ACCENT = SYS_BORDER_WARNING
HIGH_BG = SYS_HIGH_BG
HIGH_LIGHT = SYS_HIGH_LIGHT
MEDIUM_ACCENT = SYS_BORDER_ADVISORY
MEDIUM_BG = SYS_MEDIUM_BG
MEDIUM_LIGHT = SYS_MEDIUM_LIGHT
SAFE_ACCENT = SYS_BADGE_SAFE
SAFE_BG = SYS_SAFE_BG
SAFE_LIGHT = SYS_SAFE_LIGHT
LOW_BG = SYS_LOW_BG
ALERT_ACCENT = SYS_STATUS_DOT_OK
