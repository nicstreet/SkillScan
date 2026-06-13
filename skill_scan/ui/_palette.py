"""SkillScan UI colour palette — single source of truth.

Derived from Palette.md in the Obsidian vault:
  03. Personal / SkillScan - AI Skill Scanning Tool / Palette.md

Every colour used anywhere in the UI should reference a token from this
module rather than a hard-coded hex string.
"""

# ── Core 8-Color UI System ────────────────────────────────────────────────────

ANCHOR       = "#0F172A"   # 60% base — canvas, cards, panels, terminals
DEEP_SURFACE = "#1E293B"   # 30% structure — subordinate surfaces within panels
MUTED_TEXT   = "#475569"   # Secondary typography: captions, metadata, disabled
HOVER_FOCUS  = "#0F766E"   # Interactive hover / focus state
ACCENT       = "#0D9488"   # 10% focal — CTA buttons, active links, focal lines
LOW_BORDER   = "#99F6E4"   # Subtle borders / dividers (apply at ~15 % opacity)
SOFT_SURFACE = "#CCFBF1"   # High-contrast accent text, interactive elements
LIGHT_CANVAS = "#F0FDFA"   # Master typography — primary reading text

# ── Cyber Alert System ────────────────────────────────────────────────────────

# CRITICAL (P1) — Red
CRITICAL_ACCENT = "#E11D48"
CRITICAL_BG     = "#2D1217"
CRITICAL_LIGHT  = "#FFF1F2"

# WARNING / HIGH (P2) — Orange
HIGH_ACCENT = "#EA580C"
HIGH_BG     = "#2D1A10"
HIGH_LIGHT  = "#FFF7ED"

# ADVISORY / MEDIUM (P3) — Amber
MEDIUM_ACCENT = "#D97706"
MEDIUM_BG     = "#2A200E"
MEDIUM_LIGHT  = "#FEF3C7"

# ── Extended tokens (derived, not in spec) ────────────────────────────────────

# Pre-blended LOW_BORDER @ 15 % opacity on ANCHOR — for QFrame dividers
# Calculated: R=36 G=56 B=70  →  #243846
DIVIDER = "#243846"

# SAFE / PASS — emerald, distinct from the teal ACCENT
SAFE_ACCENT = "#059669"
SAFE_BG     = "#022C22"
SAFE_LIGHT  = "#D1FAE5"

# LOW severity — subdued; reuses DEEP_SURFACE bg, SOFT_SURFACE text
LOW_BG = DEEP_SURFACE
