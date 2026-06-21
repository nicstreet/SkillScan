"""All 13 DashboardWidget implementations."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..._icons import (
    ICON_HERO,
    ICON_INTEGRATION,
    ICON_SECURITY,
    ICON_ACTION_ITEMS,
    ICON_AI_USAGE,
    ICON_UPDATES,
    ICON_RECENT,
    ICON_LIBRARY,
    ICON_SCAN_VEL,
    ICON_AI_BOM,
    ICON_TRUST,
    ICON_SYS_SETUP,
    ICON_QUICK,
)
from ..._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BORDER_ADVISORY,
    SYS_BORDER_WARNING,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
    SYS_TXT_SECONDARY,
)
from ..._widgets import SCROLLBAR_STYLE
from ....core import config as _cfg
from ....core.config import get_llm_creds
from ....core.db import BomSnapshot, Folder, Skill, ScanResult, session

from sqlalchemy import func, text as sqla_text
from sqlalchemy import exists as sqla_exists

from ._base import DashboardWidget

logger = logging.getLogger(__name__)

_ACTIVITY_LOG = Path(os.environ.get("APPDATA", "~")) / "SkillScan" / "activity.log"
_LOG_RE = re.compile(
    r"\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2} UTC)\]\s+(.+?)(?:\s+—\s+(.*))?$"
)

SEVERITY_ORDER = ["CLEAN", "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"]
SEVERITY_COLORS = {
    "CLEAN": SYS_BADGE_SAFE,
    "LOW": SYS_BORDER_ADVISORY,
    "MEDIUM": SYS_BORDER_WARNING,
    "HIGH": SYS_BADGE_UNSAFE,
    "CRITICAL": SYS_BADGE_UNSAFE,
    "UNKNOWN": SYS_TXT_MUTED,
}


# ── Shared UI helpers ──────────────────────────────────────────────────────────


def _make_value_label(value: str = "—", color: str = SYS_TXT_PRIMARY) -> QLabel:
    lbl = QLabel(value)
    lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color:{color};background:transparent;border:none;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _make_sub_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 8))
    lbl.setStyleSheet(f"color:{SYS_TXT_MUTED};background:transparent;border:none;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _make_row_label(text: str, muted: bool = False) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 9))
    color = SYS_TXT_MUTED if muted else SYS_TXT_SECONDARY
    lbl.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return lbl


def _make_badge(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color:{color};background:transparent;border:none;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return lbl


def _make_action_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFont(QFont("Segoe UI", 9))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
        "border:none;border-radius:4px;padding:5px 16px;}"
        "QPushButton:hover{background:#0f9e92;}"
    )
    return btn


def _make_ghost_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFont(QFont("Segoe UI", 9))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton{{background:transparent;color:{SYS_TXT_SECONDARY};"
        f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:4px;padding:5px 16px;}}"
        f"QPushButton:hover{{border-color:{SYS_ACTION_PRIMARY};color:{SYS_ACTION_PRIMARY};}}"
    )
    return btn


def _status_dot(ok: bool) -> QLabel:
    dot = QLabel("●")
    dot.setFont(QFont("Segoe UI", 9))
    color = SYS_BADGE_SAFE if ok else SYS_TXT_MUTED
    dot.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return dot


# ── Data helpers ───────────────────────────────────────────────────────────────


def _latest_severity_counts() -> dict[str, int]:
    """Return severity -> count from the latest ScanResult per skill."""
    counts: dict[str, int] = {s: 0 for s in SEVERITY_ORDER}
    try:
        with session() as s_:
            rows = s_.execute(
                sqla_text(
                    "SELECT sr.severity FROM scan_results sr "
                    "INNER JOIN (SELECT skill_id, MAX(id) as max_id FROM scan_results "
                    "            WHERE skill_id IS NOT NULL GROUP BY skill_id) latest "
                    "ON sr.id = latest.max_id"
                )
            ).fetchall()
        for (sev,) in rows:
            key = (sev or "unknown").upper()
            if key not in counts:
                key = "UNKNOWN"
            counts[key] += 1
    except Exception:
        logger.debug("_latest_severity_counts failed", exc_info=True)
    return counts


def _read_activity_lines(n: int = 10) -> list[tuple[str, str]]:
    """Return last n lines as (timestamp, event) tuples."""
    lines: list[tuple[str, str]] = []
    if not _ACTIVITY_LOG.exists():
        return lines
    try:
        raw = _ACTIVITY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in reversed(raw):
            m = _LOG_RE.match(line.strip())
            if m:
                ts = f"{m.group(1)} {m.group(2)}"
                event = m.group(3) or ""
                lines.append((ts, event))
                if len(lines) >= n:
                    break
    except Exception:
        logger.debug("_read_activity_lines failed", exc_info=True)
    return lines


# ══════════════════════════════════════════════════════════════════════════════
# 1. Hero Metrics
# ══════════════════════════════════════════════════════════════════════════════


class HeroMetricsWidget(DashboardWidget):
    WIDGET_ID = "hero_metrics"
    TITLE = "Library Snapshot"
    ICON = ICON_HERO  # Library
    SIZE = "full"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setSpacing(0)

        self._v_skills = _make_value_label()
        self._v_clean = _make_value_label(color=SYS_BADGE_SAFE)
        self._v_issues = _make_value_label(color=SYS_BADGE_UNSAFE)
        self._v_folders = _make_value_label(color=SYS_ACTION_PRIMARY)

        for col, (val_lbl, sub_text) in enumerate(
            [
                (self._v_skills, "Total Skills"),
                (self._v_clean, "Clean"),
                (self._v_issues, "Issues"),
                (self._v_folders, "Folders"),
            ]
        ):
            cell = QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            lay = QVBoxLayout(cell)
            lay.setContentsMargins(8, 8, 8, 8)
            lay.setSpacing(2)
            lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(val_lbl)
            lay.addWidget(_make_sub_label(sub_text))
            grid.addWidget(cell, 0, col)

        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            with session() as s:
                total = s.query(Skill).count()
                folders = s.query(Folder).count()
            sev = _latest_severity_counts()
            clean = sev.get("CLEAN", 0)
            issues = sum(sev.get(k, 0) for k in ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
            self._v_skills.setText(str(total))
            self._v_clean.setText(str(clean))
            self._v_issues.setText(str(issues))
            self._v_folders.setText(str(folders))
        except Exception:
            logger.debug("HeroMetrics refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Integration Health
# ══════════════════════════════════════════════════════════════════════════════


class IntegrationHealthWidget(DashboardWidget):
    WIDGET_ID = "integration_health"
    TITLE = "Integration Health"
    ICON = ICON_INTEGRATION  # PlugConnected
    SIZE = "full"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(4)

        self._rows: dict[str, tuple[QLabel, QLabel]] = {}
        labels = [
            ("llm", "LLM Analyzer"),
            ("virustotal", "VirusTotal"),
            ("aidefense", "AI Defense"),
            ("mcp_llm", "MCP LLM Judge"),
            ("mcp_api", "MCP AI Defense"),
        ]
        for key, display in labels:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setFont(QFont("Segoe UI", 9))
            name_lbl = _make_row_label(display)
            status_lbl = _make_badge("—", SYS_TXT_MUTED)
            rl.addWidget(dot)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(status_lbl)
            self._rows[key] = (dot, status_lbl)
            lay.addWidget(row)

        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            cfg = _cfg.load()
            sc = get_llm_creds(cfg, "scanner")
            scanner_llm_ok = bool(sc["api_key"] or sc["is_local"])
            checks = {
                "llm": bool(scanner_llm_ok and cfg.get("use_llm")),
                "virustotal": bool(
                    cfg.get("virustotal_api_key") and cfg.get("use_virustotal")
                ),
                "aidefense": bool(
                    cfg.get("ai_defense_api_key") and cfg.get("use_aidefense")
                ),
                "mcp_llm": bool(scanner_llm_ok and cfg.get("mcp_use_llm")),
                "mcp_api": bool(cfg.get("mcp_api_key") and cfg.get("mcp_use_api")),
            }
            details = {
                "llm": sc["model"].split("/")[-1] if checks["llm"] else "disabled",
                "virustotal": "enabled" if checks["virustotal"] else "disabled",
                "aidefense": "enabled" if checks["aidefense"] else "disabled",
                "mcp_llm": "enabled" if checks["mcp_llm"] else "disabled",
                "mcp_api": "enabled" if checks["mcp_api"] else "disabled",
            }
            for key, (dot, status_lbl) in self._rows.items():
                ok = checks[key]
                dot.setStyleSheet(
                    f"color:{SYS_BADGE_SAFE if ok else SYS_TXT_MUTED};"
                    "background:transparent;border:none;"
                )
                status_lbl.setText(details[key])
                status_lbl.setStyleSheet(
                    f"color:{SYS_TXT_SECONDARY if ok else SYS_TXT_MUTED};"
                    "background:transparent;border:none;"
                )
        except Exception:
            logger.debug("IntegrationHealth refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Security Posture
# ══════════════════════════════════════════════════════════════════════════════


class SecurityPostureWidget(DashboardWidget):
    WIDGET_ID = "security_posture"
    TITLE = "Security Posture"
    ICON = ICON_SECURITY  # Shield
    SIZE = "half"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(3)

        self._sev_labels: dict[str, QLabel] = {}
        for sev in SEVERITY_ORDER:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setFont(QFont("Segoe UI", 9))
            dot.setStyleSheet(
                f"color:{SEVERITY_COLORS[sev]};background:transparent;border:none;"
            )
            name_lbl = _make_row_label(sev.title())
            count_lbl = _make_badge("—", SEVERITY_COLORS[sev])
            rl.addWidget(dot)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(count_lbl)
            self._sev_labels[sev] = count_lbl
            lay.addWidget(row)

        self._total_lbl = _make_row_label("", muted=True)
        lay.addSpacing(4)
        lay.addWidget(self._total_lbl)
        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            counts = _latest_severity_counts()
            total = sum(counts.values())
            for sev, lbl in self._sev_labels.items():
                lbl.setText(str(counts.get(sev, 0)))
            self._total_lbl.setText(f"{total} skills scanned")
        except Exception:
            logger.debug("SecurityPosture refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Action Items
# ══════════════════════════════════════════════════════════════════════════════


class ActionItemsWidget(DashboardWidget):
    WIDGET_ID = "action_items"
    TITLE = "Action Items"
    ICON = ICON_ACTION_ITEMS  # Important
    SIZE = "half"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(3)

        items = [
            ("unscanned", "Not yet scanned", SYS_TXT_MUTED),
            ("critical", "Critical / High severity", SYS_BADGE_UNSAFE),
            ("aging", "Aging trust (>30 days)", SYS_BORDER_WARNING),
            ("revoked", "Previously trusted, now revoked", SYS_BORDER_ADVISORY),
        ]
        self._action_labels: dict[str, QLabel] = {}
        for key, label, color in items:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setFont(QFont("Segoe UI", 9))
            dot.setStyleSheet(f"color:{color};background:transparent;border:none;")
            name_lbl = _make_row_label(label)
            count_lbl = _make_badge("—", color)
            rl.addWidget(dot)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(count_lbl)
            self._action_labels[key] = count_lbl
            lay.addWidget(row)

        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            threshold = datetime.now(timezone.utc) - timedelta(days=30)
            with session() as s:
                # skills with no scan result
                unscanned = (
                    s.query(Skill)
                    .filter(~sqla_exists().where(ScanResult.skill_id == Skill.id))
                    .count()
                )

                aging = (
                    s.query(Skill)
                    .filter(
                        Skill.trusted.is_(True),
                        Skill.trust_signed_at.isnot(None),
                        Skill.trust_signed_at < threshold,
                    )
                    .count()
                )

                revoked = (
                    s.query(Skill)
                    .filter(
                        Skill.trusted.is_(False),
                        Skill.trust_signed_at.isnot(None),
                    )
                    .count()
                )

            sev_counts = _latest_severity_counts()
            critical = sev_counts.get("CRITICAL", 0) + sev_counts.get("HIGH", 0)

            for key, val in [
                ("unscanned", unscanned),
                ("critical", critical),
                ("aging", aging),
                ("revoked", revoked),
            ]:
                lbl = self._action_labels[key]
                lbl.setText(str(val) if val else "0")
        except Exception:
            logger.debug("ActionItems refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 5. AI Usage
# ══════════════════════════════════════════════════════════════════════════════


class AIUsageWidget(DashboardWidget):
    WIDGET_ID = "ai_usage"
    TITLE = "AI Usage"
    ICON = ICON_AI_USAGE  # Brain / AI
    SIZE = "half"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(3)

        rows = [
            ("total_scans", "Total scans run"),
            ("avg_duration", "Avg scan duration"),
            ("llm_scans", "LLM-assisted scans"),
            ("analyzers", "Most used analyzer"),
        ]
        self._ai_labels: dict[str, QLabel] = {}
        for key, label in rows:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            name_lbl = _make_row_label(label)
            val_lbl = _make_badge("—", SYS_TXT_SECONDARY)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(val_lbl)
            self._ai_labels[key] = val_lbl
            lay.addWidget(row)

        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            import json as _json
            from collections import Counter

            with session() as s:
                results = (
                    s.query(ScanResult).filter(ScanResult.skill_id.isnot(None)).all()
                )

            total = len(results)
            durations = [r.duration_ms for r in results if r.duration_ms]
            avg_ms = sum(durations) // len(durations) if durations else 0

            analyzer_counter: Counter = Counter()
            for r in results:
                try:
                    used = _json.loads(r.analyzers_used or "[]")
                    for a in used:
                        analyzer_counter[a] += 1
                except Exception:
                    pass

            llm_scans = analyzer_counter.get("llm", 0)
            top_analyzer = (
                analyzer_counter.most_common(1)[0][0] if analyzer_counter else "—"
            )

            avg_text = (
                f"{avg_ms // 1000}s"
                if avg_ms >= 1000
                else f"{avg_ms}ms" if avg_ms else "—"
            )

            self._ai_labels["total_scans"].setText(str(total))
            self._ai_labels["avg_duration"].setText(avg_text)
            self._ai_labels["llm_scans"].setText(str(llm_scans))
            self._ai_labels["analyzers"].setText(top_analyzer)
        except Exception:
            logger.debug("AIUsage refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Updates
# ══════════════════════════════════════════════════════════════════════════════


class UpdatesWidget(DashboardWidget):
    WIDGET_ID = "updates"
    TITLE = "Updates"
    ICON = ICON_UPDATES  # Download
    SIZE = "half"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(6)

        rows = [
            ("skillscan", "SkillScan"),
            ("skill_scanner", "cisco-ai-skill-scanner"),
            ("mcp_scanner", "cisco-ai-mcp-scanner"),
        ]
        self._update_labels: dict[str, QLabel] = {}
        for key, label in rows:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            name_lbl = _make_row_label(label)
            val_lbl = _make_badge("—", SYS_TXT_MUTED)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(val_lbl)
            self._update_labels[key] = val_lbl
            lay.addWidget(row)

        lay.addStretch()
        self.refresh()
        return container

    def refresh(self) -> None:
        import subprocess

        checks = {
            "skillscan": ("skillscan", "--version"),
            "skill_scanner": ("cisco-ai-skill-scanner", "--version"),
            "mcp_scanner": ("cisco-ai-mcp-scanner", "--version"),
        }
        for key, (cmd, flag) in checks.items():
            try:
                proc = subprocess.run(
                    [cmd, flag],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                ver = proc.stdout.strip() or proc.stderr.strip() or "installed"
                self._update_labels[key].setText(ver[:24])
                self._update_labels[key].setStyleSheet(
                    f"color:{SYS_BADGE_SAFE};background:transparent;border:none;"
                )
            except FileNotFoundError:
                self._update_labels[key].setText("not installed")
                self._update_labels[key].setStyleSheet(
                    f"color:{SYS_TXT_MUTED};background:transparent;border:none;"
                )
            except Exception:
                self._update_labels[key].setText("—")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Recent Activity
# ══════════════════════════════════════════════════════════════════════════════


class RecentActivityWidget(DashboardWidget):
    WIDGET_ID = "recent_activity"
    TITLE = "Recent Activity"
    ICON = ICON_RECENT  # History
    SIZE = "half"

    def build_content(self) -> Optional[QWidget]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;border:none;")
        scroll.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;border:none;")
        self._activity_lay = QVBoxLayout(inner)
        self._activity_lay.setContentsMargins(0, 0, 4, 0)
        self._activity_lay.setSpacing(2)
        self._activity_lay.addStretch()
        scroll.setWidget(inner)
        self.refresh()
        return scroll

    def refresh(self) -> None:
        # Clear existing items (keep stretch at end)
        while self._activity_lay.count() > 1:
            item = self._activity_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lines = _read_activity_lines(10)
        if not lines:
            lbl = _make_row_label("No activity logged yet.", muted=True)
            self._activity_lay.insertWidget(0, lbl)
            return

        for ts, event in lines:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 1, 0, 1)
            rl.setSpacing(6)
            ts_lbl = _make_row_label(ts[:10], muted=True)
            ts_lbl.setFixedWidth(68)
            ev_lbl = _make_row_label(event[:60] + ("..." if len(event) > 60 else ""))
            rl.addWidget(ts_lbl)
            rl.addWidget(ev_lbl, 1)
            self._activity_lay.insertWidget(self._activity_lay.count() - 1, row)


# ══════════════════════════════════════════════════════════════════════════════
# 8. Library Composition
# ══════════════════════════════════════════════════════════════════════════════


class LibraryCompositionWidget(DashboardWidget):
    WIDGET_ID = "library_composition"
    TITLE = "Library Composition"
    ICON = ICON_LIBRARY  # ViewAll
    SIZE = "half"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(3)

        spec_types = [
            ("skill", "Skill files", SYS_BADGE_SAFE),
            ("mcp", "MCP manifests", SYS_ACTION_PRIMARY),
            ("a2a", "A2A agent cards", SYS_BORDER_ADVISORY),
            ("unknown", "Unrecognised", SYS_TXT_MUTED),
        ]
        self._comp_labels: dict[str, QLabel] = {}
        for key, label, color in spec_types:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setFont(QFont("Segoe UI", 9))
            dot.setStyleSheet(f"color:{color};background:transparent;border:none;")
            name_lbl = _make_row_label(label)
            count_lbl = _make_badge("—", color)
            rl.addWidget(dot)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(count_lbl)
            self._comp_labels[key] = count_lbl
            lay.addWidget(row)

        self._total_comp_lbl = _make_row_label("", muted=True)
        lay.addSpacing(4)
        lay.addWidget(self._total_comp_lbl)
        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            with session() as s:
                counts_raw = (
                    s.query(Skill.spec_type, func.count(Skill.id))
                    .group_by(Skill.spec_type)
                    .all()
                )

            counts = {(st or "unknown"): c for st, c in counts_raw}
            total = sum(counts.values())
            for key, lbl in self._comp_labels.items():
                lbl.setText(str(counts.get(key, 0)))
            self._total_comp_lbl.setText(f"{total} skills total")
        except Exception:
            logger.debug("LibraryComposition refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 9. Scan Velocity
# ══════════════════════════════════════════════════════════════════════════════


class ScanVelocityWidget(DashboardWidget):
    WIDGET_ID = "scan_velocity"
    TITLE = "Scan Velocity"
    ICON = ICON_SCAN_VEL  # History/Chart
    SIZE = "third"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(2)

        self._vel_rows: list[tuple[QLabel, QLabel]] = []
        for _ in range(7):
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            date_lbl = _make_row_label("", muted=True)
            date_lbl.setFixedWidth(56)
            count_lbl = _make_badge("", SYS_ACTION_PRIMARY)
            rl.addWidget(date_lbl)
            rl.addWidget(count_lbl)
            self._vel_rows.append((date_lbl, count_lbl))
            lay.addWidget(row)

        self._vel_total = _make_row_label("", muted=True)
        lay.addSpacing(4)
        lay.addWidget(self._vel_total)
        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            today = datetime.now(timezone.utc).date()
            with session() as s:
                rows = (
                    s.query(func.date(ScanResult.timestamp), func.count(ScanResult.id))
                    .group_by(func.date(ScanResult.timestamp))
                    .order_by(func.date(ScanResult.timestamp).desc())
                    .limit(7)
                    .all()
                )

            by_date = {str(r[0]): r[1] for r in rows}
            total = sum(by_date.values())

            for i, (date_lbl, count_lbl) in enumerate(self._vel_rows):
                d = today - timedelta(days=i)
                ds = d.strftime("%d %b")
                key = str(d)
                count = by_date.get(key, 0)
                date_lbl.setText(ds)
                count_lbl.setText(str(count) if count else "—")
                count_lbl.setStyleSheet(
                    f"color:{SYS_ACTION_PRIMARY if count else SYS_TXT_MUTED};"
                    "background:transparent;border:none;"
                )
            self._vel_total.setText(f"{total} in last 7 days")
        except Exception:
            logger.debug("ScanVelocity refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 10. AI BOM
# ══════════════════════════════════════════════════════════════════════════════


class AIBomWidget(DashboardWidget):
    WIDGET_ID = "ai_bom"
    TITLE = "AI BOM"
    ICON = ICON_AI_BOM  # Certificate
    SIZE = "third"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(3)

        rows = [
            ("total", "Total snapshots"),
            ("folders", "Folders covered"),
            ("latest", "Latest snapshot"),
            ("format", "Format"),
        ]
        self._bom_labels: dict[str, QLabel] = {}
        for key, label in rows:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            name_lbl = _make_row_label(label)
            val_lbl = _make_badge("—", SYS_TXT_SECONDARY)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(val_lbl)
            self._bom_labels[key] = val_lbl
            lay.addWidget(row)

        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            with session() as s:
                total = s.query(BomSnapshot).count()
                covered_folders = s.query(BomSnapshot.folder_id).distinct().count()
                latest = (
                    s.query(BomSnapshot).order_by(BomSnapshot.created_at.desc()).first()
                )

            self._bom_labels["total"].setText(str(total))
            self._bom_labels["folders"].setText(str(covered_folders))
            if latest:
                self._bom_labels["latest"].setText(
                    latest.created_at.strftime("%Y-%m-%d") if latest.created_at else "—"
                )
                self._bom_labels["format"].setText(latest.format or "—")
            else:
                self._bom_labels["latest"].setText("none")
                self._bom_labels["format"].setText("—")
        except Exception:
            logger.debug("AIBom refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 11. Trust Health
# ══════════════════════════════════════════════════════════════════════════════


class TrustHealthWidget(DashboardWidget):
    WIDGET_ID = "trust_health"
    TITLE = "Trust Health"
    ICON = ICON_TRUST  # Shield check
    SIZE = "third"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(3)

        items = [
            ("trusted", "Trusted", SYS_BADGE_SAFE),
            ("untrusted", "Untrusted", SYS_TXT_MUTED),
            ("aging", "Aging (>30d)", SYS_BORDER_WARNING),
            ("revoked", "Revoked", SYS_BADGE_UNSAFE),
        ]
        self._trust_labels: dict[str, QLabel] = {}
        for key, label, color in items:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setFont(QFont("Segoe UI", 9))
            dot.setStyleSheet(f"color:{color};background:transparent;border:none;")
            name_lbl = _make_row_label(label)
            count_lbl = _make_badge("—", color)
            rl.addWidget(dot)
            rl.addWidget(name_lbl, 1)
            rl.addWidget(count_lbl)
            self._trust_labels[key] = count_lbl
            lay.addWidget(row)

        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            threshold = datetime.now(timezone.utc) - timedelta(days=30)
            with session() as s:
                trusted = s.query(Skill).filter(Skill.trusted.is_(True)).count()
                untrusted = s.query(Skill).filter(Skill.trusted.is_(False)).count()
                aging = (
                    s.query(Skill)
                    .filter(
                        Skill.trusted.is_(True),
                        Skill.trust_signed_at.isnot(None),
                        Skill.trust_signed_at < threshold,
                    )
                    .count()
                )
                revoked = (
                    s.query(Skill)
                    .filter(
                        Skill.trusted.is_(False),
                        Skill.trust_signed_at.isnot(None),
                    )
                    .count()
                )

            for key, val in [
                ("trusted", trusted),
                ("untrusted", untrusted),
                ("aging", aging),
                ("revoked", revoked),
            ]:
                self._trust_labels[key].setText(str(val))
        except Exception:
            logger.debug("TrustHealth refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 12. System Setup
# ══════════════════════════════════════════════════════════════════════════════


class SystemSetupWidget(DashboardWidget):
    WIDGET_ID = "system_setup"
    TITLE = "System Setup"
    ICON = ICON_SYS_SETUP  # Settings
    SIZE = "full"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setSpacing(4)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        checks = [
            ("llm_key", "LLM API Key"),
            ("vt_key", "VirusTotal Key"),
            ("ad_key", "AI Defense Key"),
            ("policy", "Scan Policy"),
            ("hotkey", "Global Hotkey"),
            ("clipboard", "Clipboard Watch"),
        ]
        self._setup_dots: dict[str, QLabel] = {}
        self._setup_vals: dict[str, QLabel] = {}

        for idx, (key, label) in enumerate(checks):
            row, col = divmod(idx, 2)
            base_col = col * 3

            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setFont(QFont("Segoe UI", 9))
            dot.setStyleSheet(
                f"color:{SYS_TXT_MUTED};background:transparent;border:none;"
            )

            name_lbl = _make_row_label(label)
            val_lbl = _make_badge("—", SYS_TXT_MUTED)

            grid.addWidget(dot, row, base_col)
            grid.addWidget(name_lbl, row, base_col + 1)
            grid.addWidget(val_lbl, row, base_col + 2)

            self._setup_dots[key] = dot
            self._setup_vals[key] = val_lbl

        self.refresh()
        return container

    def refresh(self) -> None:
        try:
            cfg = _cfg.load()
            checks = {
                "llm_key": (
                    bool(
                        get_llm_creds(cfg, "inapp")["api_key"]
                        or get_llm_creds(cfg, "inapp")["is_local"]
                    ),
                    (
                        "configured"
                        if (
                            get_llm_creds(cfg, "inapp")["api_key"]
                            or get_llm_creds(cfg, "inapp")["is_local"]
                        )
                        else "not set"
                    ),
                ),
                "vt_key": (
                    bool(cfg.get("virustotal_api_key")),
                    "configured" if cfg.get("virustotal_api_key") else "not set",
                ),
                "ad_key": (
                    bool(cfg.get("ai_defense_api_key")),
                    "configured" if cfg.get("ai_defense_api_key") else "not set",
                ),
                "policy": (True, cfg.get("policy", "permissive")),
                "hotkey": (bool(cfg.get("scan_hotkey")), cfg.get("scan_hotkey", "—")),
                "clipboard": (
                    bool(cfg.get("clipboard_watch_enabled")),
                    "enabled" if cfg.get("clipboard_watch_enabled") else "disabled",
                ),
            }
            for key, (ok, val) in checks.items():
                color = SYS_BADGE_SAFE if ok else SYS_TXT_MUTED
                self._setup_dots[key].setStyleSheet(
                    f"color:{color};background:transparent;border:none;"
                )
                self._setup_vals[key].setText(str(val))
                self._setup_vals[key].setStyleSheet(
                    f"color:{SYS_TXT_SECONDARY if ok else SYS_TXT_MUTED};"
                    "background:transparent;border:none;"
                )
        except Exception:
            logger.debug("SystemSetup refresh failed", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 13. Quick Actions
# ══════════════════════════════════════════════════════════════════════════════


class QuickActionsWidget(DashboardWidget):
    WIDGET_ID = "quick_actions"
    TITLE = "Quick Actions"
    ICON = ICON_QUICK  # Flash / Lightning
    SIZE = "full"

    navigate_to_folders = pyqtSignal()
    navigate_to_activity = pyqtSignal()
    navigate_to_options = pyqtSignal()
    scan_all_requested = pyqtSignal()

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(8)

        scan_btn = _make_action_btn("  Scan All Folders")
        scan_btn.setFont(QFont("Segoe UI", 9))
        scan_btn.clicked.connect(self.scan_all_requested)

        folders_btn = _make_ghost_btn("  Open Folders")
        folders_btn.clicked.connect(self.navigate_to_folders)

        activity_btn = _make_ghost_btn("  Activity Log")
        activity_btn.clicked.connect(self.navigate_to_activity)

        options_btn = _make_ghost_btn("  Options")
        options_btn.clicked.connect(self.navigate_to_options)

        for btn in (scan_btn, folders_btn, activity_btn, options_btn):
            btn.setFixedHeight(32)
            btn.setSizePolicy(
                btn.sizePolicy().horizontalPolicy(),
                btn.sizePolicy().verticalPolicy(),
            )
            lay.addWidget(btn)

        lay.addStretch()
        return container

    def refresh(self) -> None:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 14. AI Module Map
# ══════════════════════════════════════════════════════════════════════════════

_S_ACTIVE = ("Active", SYS_BADGE_SAFE)
_S_NO_KEY = ("No key", SYS_BORDER_ADVISORY)
_S_DISABLED = ("Disabled", SYS_TXT_MUTED)

_MODULE_DEFS: list[tuple] = [
    ("section", "inapp_hdr", "Skill Studio"),
    ("row", "inapp_optimize", "Optimize Description"),
    ("row", "inapp_review", "AI Review & Improve"),
    ("row", "inapp_seceval", "Security Evaluation"),
    ("section", "skill_hdr", "Skill Scanner"),
    ("row", "skill_behavioral", "Behavioral Analysis"),
    ("row", "skill_llm", "LLM Step"),
    ("row", "skill_aidefense", "AI Defense"),
    ("row", "skill_virustotal", "VirusTotal"),
    ("row", "skill_trigger", "Trigger Analysis"),
    ("section", "mcp_hdr", "MCP Scanner"),
    ("row", "mcp_yara", "YARA (offline)"),
    ("row", "mcp_llm", "LLM Judge"),
    ("row", "mcp_api", "AI Defense"),
]


def _ai_module_states(cfg: dict) -> dict[str, tuple[str, str, tuple[str, str]]]:
    inapp_creds = get_llm_creds(cfg, "inapp")
    scanner_creds = get_llm_creds(cfg, "scanner")

    def _llm_state(creds: dict, enabled: bool) -> tuple[str, str, tuple]:
        prov = creds["provider"]
        model = creds["model"].split("/")[-1] if creds["model"] else "—"
        ready = bool(creds["api_key"] or creds["is_local"])
        if not enabled:
            return prov, "—", _S_DISABLED
        if not ready:
            return prov, "—", _S_NO_KEY
        return prov, model, _S_ACTIVE

    def _keyed(enabled: bool, has: bool, prov_name: str) -> tuple[str, str, tuple]:
        if not enabled:
            return prov_name, "—", _S_DISABLED
        if not has:
            return prov_name, "—", _S_NO_KEY
        return prov_name, "—", _S_ACTIVE

    def _offline(enabled: bool) -> tuple[str, str, tuple]:
        return "—", "—", _S_ACTIVE if enabled else _S_DISABLED

    inapp = _llm_state(inapp_creds, True)
    return {
        "inapp_optimize": inapp,
        "inapp_review": inapp,
        "inapp_seceval": inapp,
        "skill_behavioral": _offline(cfg.get("use_behavioral", True)),
        "skill_llm": _llm_state(scanner_creds, cfg.get("use_llm", True)),
        "skill_aidefense": _keyed(
            cfg.get("use_aidefense", False),
            bool(cfg.get("ai_defense_api_key", "").strip()),
            "cisco",
        ),
        "skill_virustotal": _keyed(
            cfg.get("use_virustotal", False),
            bool(cfg.get("virustotal_api_key", "").strip()),
            "virustotal",
        ),
        "skill_trigger": _offline(cfg.get("use_trigger", False)),
        "mcp_yara": ("—", "—", _S_ACTIVE),
        "mcp_llm": _llm_state(scanner_creds, cfg.get("mcp_use_llm", False)),
        "mcp_api": _keyed(
            cfg.get("mcp_use_api", False),
            bool(cfg.get("mcp_api_key", "").strip()),
            "cisco",
        ),
    }


class AiModuleMapWidget(DashboardWidget):
    WIDGET_ID = "ai_module_map"
    TITLE = "AI Module Map"
    ICON = ICON_AI_USAGE
    SIZE = "full"

    def build_content(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 2, 0, 4)
        outer.setSpacing(0)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(1)
        grid.setHorizontalSpacing(0)
        grid.setColumnMinimumWidth(0, 16)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(2, 86)
        grid.setColumnMinimumWidth(3, 116)
        grid.setColumnMinimumWidth(4, 68)

        hdr_style = (
            f"color:{SYS_TXT_MUTED};font-size:8px;font-weight:700;"
            "letter-spacing:1px;background:transparent;border:none;"
        )
        for col, txt in enumerate(["", "MODULE", "PROVIDER", "MODEL", "STATUS"]):
            h = QLabel(txt)
            h.setStyleSheet(hdr_style)
            h.setContentsMargins(0, 0, 0, 6)
            grid.addWidget(h, 0, col)

        self._rows: dict[str, tuple[QLabel, QLabel, QLabel, QLabel]] = {}
        gr = 1

        for kind, mid, name in _MODULE_DEFS:
            if kind == "section":
                sec = QLabel(name.upper())
                sec.setStyleSheet(
                    f"color:{SYS_ACTION_PRIMARY};font-size:8px;font-weight:700;"
                    "letter-spacing:1px;background:transparent;border:none;"
                )
                sec.setContentsMargins(0, 10, 0, 4)
                grid.addWidget(sec, gr, 0, 1, 5)
                gr += 1
                continue

            dot = QLabel("●")
            dot.setFixedWidth(16)
            dot.setFont(QFont("Segoe UI", 8))
            dot.setStyleSheet(
                f"color:{SYS_TXT_MUTED};background:transparent;border:none;"
            )

            name_lbl = QLabel(name)
            name_lbl.setFont(QFont("Segoe UI", 9))
            name_lbl.setStyleSheet(
                f"color:{SYS_TXT_SECONDARY};background:transparent;border:none;"
            )

            prov_lbl = QLabel("—")
            prov_lbl.setFont(QFont("Segoe UI", 9))
            prov_lbl.setStyleSheet(
                f"color:{SYS_TXT_MUTED};background:transparent;border:none;"
            )

            model_lbl = QLabel("—")
            model_lbl.setFont(QFont("Segoe UI", 9))
            model_lbl.setStyleSheet(
                f"color:{SYS_TXT_MUTED};background:transparent;border:none;"
            )

            status_lbl = QLabel("—")
            status_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            status_lbl.setStyleSheet(
                f"color:{SYS_TXT_MUTED};background:transparent;border:none;"
            )

            grid.addWidget(dot, gr, 0)
            grid.addWidget(name_lbl, gr, 1)
            grid.addWidget(prov_lbl, gr, 2)
            grid.addWidget(model_lbl, gr, 3)
            grid.addWidget(status_lbl, gr, 4)

            self._rows[mid] = (dot, prov_lbl, model_lbl, status_lbl)
            gr += 1

        outer.addLayout(grid)
        outer.addStretch()
        self.refresh()
        return container

    def refresh(self) -> None:
        if not hasattr(self, "_rows"):
            return
        try:
            cfg = _cfg.load()
            states = _ai_module_states(cfg)
            for mid, (dot, prov_lbl, model_lbl, status_lbl) in self._rows.items():
                prov, model, (status_text, status_color) = states[mid]
                muted = status_color == SYS_TXT_MUTED
                text_color = SYS_TXT_MUTED if muted else SYS_TXT_SECONDARY
                dot.setStyleSheet(
                    f"color:{status_color};background:transparent;border:none;"
                )
                prov_lbl.setText(prov)
                prov_lbl.setStyleSheet(
                    f"color:{text_color};background:transparent;border:none;"
                )
                model_lbl.setText(model)
                model_lbl.setStyleSheet(
                    f"color:{text_color};background:transparent;border:none;"
                )
                status_lbl.setText(status_text)
                status_lbl.setStyleSheet(
                    f"color:{status_color};background:transparent;border:none;"
                )
        except Exception:
            logger.debug("AiModuleMapWidget refresh failed", exc_info=True)
