"""Floating scan progress / results window."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from ..core.result_store import ScanResult
from ..core.scanner import ScanJob
from ._palette import (
    ACCENT, ANCHOR, CRITICAL_ACCENT, DEEP_SURFACE,
    HIGH_ACCENT, HOVER_FOCUS, LIGHT_CANVAS, MEDIUM_ACCENT,
    MUTED_TEXT, SAFE_ACCENT,
)
from ._widgets import RoundedCard, TitleBar, card_divider
from .result_formatter import format_result_html


class ScanProgressDialog(QDialog):
    def __init__(self, job: ScanJob, path: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(740, 520)
        self._job = job
        self._finished = False
        self._raw_lines: list[str] = []
        self._showing_raw = False
        self._build_ui(path)
        job.output_line.connect(self._append)
        job.finished.connect(self._on_finished)
        job.error.connect(self._on_error)

    def _build_ui(self, path: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        card = RoundedCard(radius=14, parent=self)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # ── Title bar ─────────────────────────────────────────────────────
        self._title_bar = TitleBar("SkillScan", parent=card)
        self._title_bar.close_requested.connect(self._cancel)
        inner.addWidget(self._title_bar)
        inner.addWidget(card_divider())

        # ── Content ───────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 12, 18, 14)
        body_layout.setSpacing(10)

        # File name (left) · status (right)
        meta = QHBoxLayout()
        self._file_lbl = QLabel(Path(path).name)
        self._file_lbl.setStyleSheet(f"color:{MUTED_TEXT};font-size:11px;")
        meta.addWidget(self._file_lbl)
        meta.addStretch()
        self._status = QLabel("Running scan…")
        self._status.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:11px;font-weight:600;"
        )
        meta.addWidget(self._status)
        body_layout.addLayout(meta)

        # Raw streaming output — DEEP_SURFACE bg (subordinate terminal region)
        self._raw_view = QTextEdit()
        self._raw_view.setReadOnly(True)
        self._raw_view.setFont(QFont("Consolas", 9))
        self._raw_view.setStyleSheet(f"""
            QTextEdit {{
                background: {DEEP_SURFACE};
                color: {MUTED_TEXT};
                border: 1px solid {MUTED_TEXT}33;
                border-radius: 8px;
            }}
        """)
        body_layout.addWidget(self._raw_view)

        # Formatted results — ANCHOR bg (matches HTML body)
        self._result_view = QTextBrowser()
        self._result_view.setOpenExternalLinks(True)
        self._result_view.setStyleSheet(f"""
            QTextBrowser {{
                background: {ANCHOR};
                border: 1px solid {MUTED_TEXT}33;
                border-radius: 8px;
            }}
        """)
        self._result_view.setVisible(False)
        body_layout.addWidget(self._result_view)

        # Bottom button row
        btn_row = QHBoxLayout()

        self._raw_btn = QPushButton("Show Raw Output")
        self._raw_btn.setFixedWidth(150)
        self._raw_btn.setVisible(False)
        self._raw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._raw_btn.setStyleSheet(f"""
            QPushButton {{
                background: {DEEP_SURFACE}; color: {MUTED_TEXT};
                border: 1px solid {MUTED_TEXT}55; border-radius: 6px;
                padding: 5px 12px; font-size: 11px;
            }}
            QPushButton:hover   {{ color: {LIGHT_CANVAS}; border-color: {MUTED_TEXT}; }}
            QPushButton:pressed {{ background: {ANCHOR}; }}
        """)
        self._raw_btn.clicked.connect(self._toggle_raw)
        btn_row.addWidget(self._raw_btn)
        btn_row.addStretch()

        self._action_btn = QPushButton("Cancel")
        self._action_btn.setFixedWidth(90)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: {LIGHT_CANVAS};
                border: none; border-radius: 6px;
                padding: 5px 12px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover   {{ background: {HOVER_FOCUS}; }}
            QPushButton:pressed {{ background: {HOVER_FOCUS}; }}
        """)
        self._action_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self._action_btn)

        body_layout.addLayout(btn_row)
        inner.addWidget(body)
        outer.addWidget(card)

    # ── Scan event handlers ───────────────────────────────────────────────

    def _append(self, line: str):
        self._raw_lines.append(line)
        self._raw_view.append(line)

    def _on_finished(self, result: ScanResult):
        self._finished = True
        sev = result.severity_label.upper()

        if result.is_clean:
            self._status.setText("Clean")
            self._status.setStyleSheet(
                f"color:{SAFE_ACCENT};font-size:11px;font-weight:600;"
            )
        elif sev != "UNKNOWN":
            color = {
                "CRITICAL": CRITICAL_ACCENT,
                "HIGH":     HIGH_ACCENT,
                "MEDIUM":   MEDIUM_ACCENT,
            }.get(sev, MEDIUM_ACCENT)
            self._status.setText("Processing Report")
            self._status.setStyleSheet(
                f"color:{color};font-size:11px;font-weight:600;"
            )
        else:
            self._status.setText(f"Error (exit {result.returncode})")
            self._status.setStyleSheet(
                f"color:{CRITICAL_ACCENT};font-size:11px;font-weight:600;"
            )

        self._action_btn.setText("Close")

        if result.parsed:
            self._result_view.setHtml(format_result_html(result))
            self._raw_view.setVisible(False)
            self._result_view.setVisible(True)
            self._raw_btn.setVisible(True)

    def _on_error(self, msg: str):
        self._status.setText("Error")
        self._status.setStyleSheet(
            f"color:{CRITICAL_ACCENT};font-size:11px;font-weight:600;"
        )
        self._raw_view.append(f"\n[ERROR] {msg}")
        self._action_btn.setText("Close")

    def _toggle_raw(self):
        self._showing_raw = not self._showing_raw
        if self._showing_raw:
            self._raw_view.setVisible(True)
            self._result_view.setVisible(False)
            self._raw_btn.setText("Show Results")
        else:
            self._raw_view.setVisible(False)
            self._result_view.setVisible(True)
            self._raw_btn.setText("Show Raw Output")

    def _cancel(self):
        if not self._finished:
            self._job.cancel()
        self.accept()
