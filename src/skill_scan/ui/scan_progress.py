"""Floating scan progress / results window."""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.llm import LLMJob
from ..core.result_store import ScanResult
from ..core.scanner import ScanJob
from ._icons import fa, ICON_CLOSE
from ._palette import (
    SYS_ACTION_PRIMARY,
    SYS_ACTION_HOVER,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BADGE_UNSAFE,
    SYS_BADGE_SAFE,
    SYS_BORDER_WARNING,
    SYS_BORDER_ADVISORY,
    SYS_BORDER_LOW,
    SYS_CRITICAL_BG,
    SYS_STROKE_DIVIDER,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
    SYS_CONTROL_BG_CRITICAL_PRESSED,
)
from ._widgets import card_divider, SCROLLBAR_STYLE
from .result_formatter import format_result_html

# ── Severity badge tables (mirrors skill_tile.py) ─────────────────────────────

_BADGE_BASE = (
    "font-size:8px;font-weight:700;padding:1px 4px;"
    "border-radius:4px;letter-spacing:1px;"
)
_SEV_BADGE_STYLE: dict[str, str] = {
    "clean": f"color:{SYS_BADGE_SAFE};background:transparent;border:1px solid {SYS_BADGE_SAFE};",
    "safe": f"color:{SYS_BADGE_SAFE};background:transparent;border:1px solid {SYS_BADGE_SAFE};",
    "low": f"color:{SYS_BORDER_LOW};background:transparent;border:1px solid {SYS_BORDER_LOW};",
    "medium": f"color:{SYS_BORDER_ADVISORY};background:transparent;border:1px solid {SYS_BORDER_ADVISORY};",
    "high": f"color:{SYS_BORDER_WARNING};background:transparent;border:1px solid {SYS_BORDER_WARNING};",
    "critical": f"color:{SYS_BADGE_UNSAFE};background:{SYS_CRITICAL_BG};border:1px solid {SYS_BADGE_UNSAFE};",
    "unknown": f"color:{SYS_TXT_MUTED};background:transparent;border:1px solid {SYS_TXT_MUTED};",
}
_SEV_BADGE_TEXT: dict[str, str] = {
    "clean": "CLEAN",
    "safe": "CLEAN",
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
    "unknown": "UNKNOWN",
}

# ── Widget helpers ────────────────────────────────────────────────────────────

_CLOSE_BTN = (
    "QPushButton{{color:{fg};background:transparent;border:none;border-radius:5px;"
    "font-family:'Font Awesome 6 Free';font-weight:900;font-size:10px;}}"
    "QPushButton:hover{{background:{hover};color:{hover_fg};}}"
    "QPushButton:pressed{{background:{press};color:{hover_fg};}}"
)


class _ScanTitleBar(QWidget):
    """32 px title bar matching the main window — SKILLSCAN wordmark + close."""

    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet("background:transparent;")
        self._drag_pos = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 6, 0)
        lay.setSpacing(4)

        wordmark = QLabel(
            f"<span style='color:{SYS_TXT_PRIMARY};font-weight:700;"
            f"letter-spacing:2px;font-size:13px;'>SKILL</span>"
            f"<span style='color:{SYS_ACTION_PRIMARY};font-weight:700;"
            f"letter-spacing:2px;font-size:13px;'>SCAN</span>"
        )
        wordmark.setStyleSheet("background:transparent;")
        lay.addWidget(wordmark)
        lay.addStretch()

        close_btn = QPushButton(ICON_CLOSE)  # xmark
        close_btn.setFont(fa(9))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(
            _CLOSE_BTN.format(
                fg=SYS_TXT_MUTED,
                hover=SYS_BADGE_UNSAFE,
                hover_fg=SYS_TXT_PRIMARY,
                press=SYS_CONTROL_BG_CRITICAL_PRESSED,
            )
        )
        close_btn.clicked.connect(self.close_requested)
        lay.addWidget(close_btn)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _e) -> None:
        self._drag_pos = None


class _ScanCard(QWidget):
    """Two-tone rounded card: SYS_BG_PRIMARY title strip + SYS_BG_SECONDARY body."""

    _TITLE_H = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        p.fillPath(path, QColor(SYS_BG_PRIMARY))
        p.end()


class _ContentBlock(QWidget):
    """SYS_BG_SECONDARY rounded card — contrasts with SYS_BG_PRIMARY card for visible corners."""

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        p.fillPath(path, QColor(SYS_BG_SECONDARY))
        p.end()


# ── Main dialog ───────────────────────────────────────────────────────────────


class ScanProgressDialog(QDialog):
    def __init__(self, job: ScanJob, path: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # +20 % width, −20 % height vs original 740 × 520
        self.setMinimumSize(888, 416)
        self.resize(888, 416)
        self._job = job
        self._scan_path = path
        self._finished = False
        self._raw_lines: list[str] = []
        self._showing_raw = False
        self._llm_job = None
        self._build_ui(path)
        job.output_line.connect(self._append)
        job.finished.connect(self._on_finished)
        job.error.connect(self._on_error)

    def _build_ui(self, path: str) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        card = _ScanCard(self)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # ── Title bar ─────────────────────────────────────────────────────────
        self._title_bar = _ScanTitleBar(card)
        self._title_bar.close_requested.connect(self._cancel)
        inner.addWidget(self._title_bar)
        inner.addWidget(card_divider())

        # ── Body ──────────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(18, 12, 18, 14)
        body_lay.setSpacing(10)

        # Meta row: full path · severity tag (shown post-scan)
        meta = QHBoxLayout()
        meta.setSpacing(0)

        self._file_lbl = QLabel(str(path))
        self._file_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        meta.addWidget(self._file_lbl)

        meta.addSpacing(8)

        self._sev_tag = QLabel()
        self._sev_tag.setStyleSheet(
            f"{_BADGE_BASE}color:{SYS_TXT_MUTED};background:transparent;border:none;"
        )
        self._sev_tag.setVisible(False)
        meta.addWidget(self._sev_tag)

        meta.addStretch()
        body_lay.addLayout(meta)

        # Content block (SYS_BG_SECONDARY rounded card — contrasts with SYS_BG_PRIMARY card)
        content_block = _ContentBlock()
        block_lay = QVBoxLayout(content_block)
        block_lay.setContentsMargins(4, 4, 4, 4)
        block_lay.setSpacing(0)

        # Progress indicator — shown during scan, hidden after
        self._progress_widget = QWidget()
        self._progress_widget.setStyleSheet("background:transparent;")
        pw_lay = QVBoxLayout(self._progress_widget)
        pw_lay.setContentsMargins(40, 0, 40, 0)
        pw_lay.addStretch()
        scan_lbl = QLabel("Scanning…")
        scan_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        pw_lay.addWidget(scan_lbl)
        pw_lay.addSpacing(8)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setStyleSheet(
            f"QProgressBar{{background:{SYS_STROKE_DIVIDER};border:none;border-radius:2px;}}"
            f"QProgressBar::chunk{{background:{SYS_ACTION_PRIMARY};border-radius:2px;}}"
        )
        pw_lay.addWidget(self._progress_bar)
        pw_lay.addStretch()
        block_lay.addWidget(self._progress_widget)

        self._raw_view = QTextEdit()
        self._raw_view.setReadOnly(True)
        self._raw_view.setFont(QFont("Consolas", 9))
        self._raw_view.setStyleSheet(
            f"QTextEdit{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:none;border-radius:8px;padding:8px;}}"
        )
        self._raw_view.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._raw_view.setVisible(
            False
        )  # hidden during scan; accessible via button after
        block_lay.addWidget(self._raw_view)

        self._result_view = QTextBrowser()
        self._result_view.setOpenExternalLinks(True)
        self._result_view.setStyleSheet(
            "QTextBrowser{background:transparent;border:none;border-radius:8px;padding:0px;}"
        )
        self._result_view.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._result_view.setVisible(False)
        block_lay.addWidget(self._result_view)

        body_lay.addWidget(content_block, 1)

        # Button row
        btn_row = QHBoxLayout()

        self._raw_btn = QPushButton("Show Raw Output")
        self._raw_btn.setFixedWidth(150)
        self._raw_btn.setVisible(False)
        self._raw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._raw_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};"
            f"border:1px solid {SYS_TXT_MUTED}55;border-radius:6px;"
            f"padding:5px 12px;font-size:11px;}}"
            f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};border-color:{SYS_TXT_MUTED};}}"
            f"QPushButton:pressed{{background:{SYS_BG_SECONDARY};}}"
        )
        self._raw_btn.clicked.connect(self._toggle_raw)
        btn_row.addWidget(self._raw_btn)

        self._ai_eval_btn = QPushButton("AI Security Evaluation")
        self._ai_eval_btn.setFixedWidth(180)
        self._ai_eval_btn.setVisible(False)
        self._ai_eval_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_eval_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            f"border:none;border-radius:6px;padding:5px 12px;"
            f"font-size:11px;font-weight:600;}}"
            f"QPushButton:hover{{background:{SYS_ACTION_HOVER};}}"
            f"QPushButton:disabled{{background:{SYS_BG_SECONDARY};color:{SYS_TXT_MUTED};}}"
        )
        self._ai_eval_btn.clicked.connect(self._run_ai_evaluation)
        btn_row.addWidget(self._ai_eval_btn)

        btn_row.addStretch()

        self._action_btn = QPushButton("Cancel")
        self._action_btn.setFixedWidth(90)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            f"border:none;border-radius:6px;padding:5px 12px;"
            f"font-size:12px;font-weight:600;}}"
            f"QPushButton:hover{{background:{SYS_ACTION_HOVER};}}"
            f"QPushButton:pressed{{background:{SYS_ACTION_HOVER};}}"
        )
        self._action_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self._action_btn)

        body_lay.addLayout(btn_row)
        inner.addWidget(body)
        outer.addWidget(card)

    # ── Scan event handlers ───────────────────────────────────────────────────

    def _append(self, line: str) -> None:
        self._raw_lines.append(line)
        self._raw_view.append(line)

    def _on_finished(self, result: ScanResult) -> None:
        self._finished = True
        sev = result.severity_label.upper()
        sev_lower = (
            result.severity_label.lower() if result.severity_label else "unknown"
        )

        if result.is_clean:
            sev_lower = "clean"
        elif sev in ("", "UNKNOWN"):
            sev_lower = "unknown"

        self._progress_widget.setVisible(False)

        badge_style = _SEV_BADGE_STYLE.get(sev_lower, _SEV_BADGE_STYLE["unknown"])
        badge_text = _SEV_BADGE_TEXT.get(sev_lower, sev_lower.upper())
        self._sev_tag.setStyleSheet(f"{_BADGE_BASE}{badge_style}")
        self._sev_tag.setText(badge_text)
        self._sev_tag.setVisible(True)

        self._action_btn.setText("Close")

        if result.parsed:
            self._result_view.setHtml(format_result_html(result))
            self._result_view.setVisible(True)
            self._raw_btn.setVisible(True)
        else:
            self._raw_view.setVisible(True)

        if result.llm_skipped:
            self._ai_eval_btn.setVisible(True)

    def _on_error(self, msg: str) -> None:
        self._progress_widget.setVisible(False)
        self._raw_view.append(f"\n[ERROR] {msg}")
        self._raw_view.setVisible(True)
        self._action_btn.setText("Close")

    def _toggle_raw(self) -> None:
        self._showing_raw = not self._showing_raw
        if self._showing_raw:
            self._raw_view.setVisible(True)
            self._result_view.setVisible(False)
            self._raw_btn.setText("Show Results")
        else:
            self._raw_view.setVisible(False)
            self._result_view.setVisible(True)
            self._raw_btn.setText("Show Raw Output")

    _AI_EVAL_SYSTEM = (
        "You are a security analyst reviewing an AI skill definition file.\n"
        "The scanner's LLM evaluation step was skipped for this skill.\n"
        "Evaluate the skill for security risks and respond in this exact XML format:\n\n"
        "<SEVERITY>low|medium|high|critical</SEVERITY>\n"
        "<FINDINGS>\n"
        "- [CATEGORY] Description of issue\n"
        "</FINDINGS>\n"
        "<SUMMARY>One paragraph overall assessment (max 300 chars).</SUMMARY>\n\n"
        "Categories to check: PROMPT_INJECTION, INTENT_ALIGNMENT, PRIVILEGE_ESCALATION, "
        "DATA_EXFILTRATION, DECEPTIVE_PATTERN, SCOPE_CREEP, TRUST_BOUNDARY.\n"
        "If no issues found, use SEVERITY: low and state 'No significant issues detected' in FINDINGS."
    )

    def _run_ai_evaluation(self) -> None:
        self._ai_eval_btn.setEnabled(False)
        self._ai_eval_btn.setText("Evaluating…")

        try:
            p = Path(self._scan_path)
            if p.is_dir():
                candidates = list(p.glob("*.md")) + list(p.glob("**/*.md"))
                skill_file = next(
                    (f for f in candidates if f.stem.upper() == "SKILL"), None
                ) or (candidates[0] if candidates else None)
                if skill_file is None:
                    self._on_ai_eval_error("No skill file found in scan path.")
                    return
                p = skill_file
            skill_text = p.read_text(encoding="utf-8")
        except Exception as exc:
            self._on_ai_eval_error(f"Could not read skill file: {exc}")
            return

        self._llm_job = LLMJob(skill_text, system=self._AI_EVAL_SYSTEM)
        self._llm_job.finished.connect(self._on_ai_eval_done)
        self._llm_job.error.connect(self._on_ai_eval_error)
        self._llm_job.start()

    def _on_ai_eval_done(self, response: str) -> None:
        self._ai_eval_btn.setText("AI Evaluation Done")

        raw = response.strip()
        sev_s = raw.find("<SEVERITY>")
        sev_e = raw.find("</SEVERITY>")
        findings_s = raw.find("<FINDINGS>")
        findings_e = raw.find("</FINDINGS>")
        summary_s = raw.find("<SUMMARY>")
        summary_e = raw.find("</SUMMARY>")

        severity = (
            raw[sev_s + 10 : sev_e].strip()
            if sev_s >= 0 and sev_e > sev_s
            else "unknown"
        )
        findings_raw = (
            raw[findings_s + 10 : findings_e].strip()
            if findings_s >= 0 and findings_e > findings_s
            else raw
        )
        summary = (
            raw[summary_s + 9 : summary_e].strip()
            if summary_s >= 0 and summary_e > summary_s
            else ""
        )

        sev_color = {
            "critical": "#ef4444",
            "high": "#f97316",
            "medium": "#eab308",
            "low": "#22c55e",
        }.get(severity.lower(), SYS_TXT_MUTED)

        findings_html = "".join(
            f"<li style='margin:2px 0;'>{line.lstrip('- ').strip()}</li>"
            for line in findings_raw.splitlines()
            if line.strip() and line.strip() != "-"
        )

        html = (
            f"<div style='font-family:Segoe UI,sans-serif;font-size:12px;"
            f"color:{SYS_TXT_PRIMARY};padding:8px;'>"
            f"<p style='color:{SYS_TXT_MUTED};font-size:10px;letter-spacing:1px;"
            f"font-weight:700;margin:0 0 8px;'>IN-APP AI SECURITY EVALUATION</p>"
            f"<p style='margin:0 0 6px;'>"
            f"<span style='font-weight:700;color:{sev_color};"
            f"text-transform:uppercase;'>{severity}</span></p>"
            f"<ul style='margin:0 0 8px;padding-left:18px;'>{findings_html}</ul>"
        )
        if summary:
            html += (
                f"<p style='color:{SYS_TXT_MUTED};font-size:11px;"
                f"margin:0;border-top:1px solid {SYS_STROKE_DIVIDER};"
                f"padding-top:6px;'>{summary}</p>"
            )
        html += "</div>"

        current = self._result_view.toHtml()
        divider = (
            f"<hr style='border:none;border-top:1px solid {SYS_STROKE_DIVIDER};"
            f"margin:8px 0;'/>"
        )
        self._result_view.setHtml(current + divider + html)
        self._result_view.setVisible(True)

    def _on_ai_eval_error(self, msg: str) -> None:
        self._ai_eval_btn.setText("Evaluation Failed")
        error_html = (
            f"<p style='color:#ef4444;font-size:11px;padding:8px;'>"
            f"AI evaluation failed: {msg}</p>"
        )
        current = self._result_view.toHtml()
        self._result_view.setHtml(current + error_html)
        self._result_view.setVisible(True)

    def _cancel(self) -> None:
        if not self._finished:
            self._job.cancel()
        self.accept()
