"""SkillTableView — QTableWidget-based table view for skill items."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .skill_tile import SkillInfo, _SEV_BADGE_TEXT, _TYPE_LABEL
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BORDER_ADVISORY,
    SYS_BORDER_LOW,
    SYS_BORDER_WARNING,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
    SYS_TXT_SECONDARY,
)
from .._widgets import SCROLLBAR_STYLE

_FIND_COLOURS: dict[str, str] = {
    "critical": SYS_BADGE_UNSAFE,
    "high": SYS_BORDER_WARNING,
    "medium": SYS_BORDER_ADVISORY,
    "low": SYS_BORDER_LOW,
}

_SEV_COLOUR: dict[str, str] = {
    "critical": SYS_BADGE_UNSAFE,
    "high": SYS_BORDER_WARNING,
    "medium": SYS_BORDER_ADVISORY,
    "low": SYS_BORDER_LOW,
    "clean": SYS_BADGE_SAFE,
    "safe": SYS_BADGE_SAFE,
}

# Column indices
_C_TYPE = 0
_C_NAME = 1
_C_DESC = 2
_C_RESULTS = 3
_C_ANALYZERS = 4
_C_UNSAFE = 5
_C_SEV = 6
_C_FINDINGS = 7

_HEADERS = [
    "TYPE",
    "NAME",
    "DESCRIPTION",
    "RESULTS",
    "ANALYZERS",
    "UNSAFE",
    "SEVERITY",
    "FINDINGS",
]

_BOLD = QFont()
_BOLD.setBold(True)

_TABLE_QSS = f"""
    QTableWidget {{
        background:{SYS_BG_SECONDARY};
        alternate-background-color:{SYS_BG_PRIMARY};
        color:{SYS_TXT_PRIMARY};
        border:none;
        gridline-color:{SYS_STROKE_DIVIDER};
        selection-background-color:rgba(13,148,136,45);
        selection-color:{SYS_TXT_PRIMARY};
        outline:none;
    }}
    QTableWidget::item {{
        padding:4px 8px;
        border:none;
    }}
    QHeaderView::section {{
        background:{SYS_BG_PRIMARY};
        color:{SYS_TXT_MUTED};
        font-size:8px;
        font-weight:700;
        letter-spacing:1px;
        border:none;
        border-right:1px solid {SYS_STROKE_DIVIDER};
        border-bottom:1px solid {SYS_STROKE_DIVIDER};
        padding:4px 8px;
    }}
    QHeaderView::section:last {{
        border-right:none;
    }}
"""


def _item(
    text: str,
    fg: str = SYS_TXT_PRIMARY,
    center: bool = False,
    bold: bool = False,
) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setForeground(QColor(fg))
    it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
    align = Qt.AlignmentFlag.AlignVCenter
    align |= Qt.AlignmentFlag.AlignCenter if center else Qt.AlignmentFlag.AlignLeft
    it.setTextAlignment(align)
    if bold:
        it.setFont(_BOLD)
    return it


class SkillTableView(QWidget):
    detail_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._table = QTableWidget(0, len(_HEADERS))
        self._table.setHorizontalHeaderLabels(_HEADERS)
        self._table.setStyleSheet(_TABLE_QSS)
        self._table.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(True)
        self._table.setWordWrap(False)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(28)

        hdr = self._table.horizontalHeader()
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(_C_TYPE, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_C_NAME, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_C_DESC, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_C_RESULTS, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_C_ANALYZERS, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_C_UNSAFE, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_C_SEV, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_C_FINDINGS, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(_C_TYPE, 52)
        self._table.setColumnWidth(_C_NAME, 160)
        self._table.setColumnWidth(_C_RESULTS, 96)
        self._table.setColumnWidth(_C_ANALYZERS, 110)
        self._table.setColumnWidth(_C_UNSAFE, 68)
        self._table.setColumnWidth(_C_SEV, 108)
        self._table.setColumnWidth(_C_FINDINGS, 200)

        self._table.cellClicked.connect(self._on_cell_clicked)
        lay.addWidget(self._table)

        self._infos: list[SkillInfo] = []

    def populate(self, infos: list[SkillInfo]) -> None:
        self._infos = list(infos)
        self._table.setRowCount(0)
        self._table.setRowCount(len(infos))
        for row, info in enumerate(infos):
            self._fill_row(row, info)

    def _fill_row(self, row: int, info: SkillInfo) -> None:
        sev_lower = (info.severity or "").lower()

        self._table.setItem(
            row,
            _C_TYPE,
            _item(
                _TYPE_LABEL.get(info.spec_type, "?"),
                SYS_ACTION_PRIMARY,
                center=True,
                bold=True,
            ),
        )
        self._table.setItem(row, _C_NAME, _item(info.name, SYS_TXT_PRIMARY, bold=True))
        self._table.setItem(
            row, _C_DESC, _item(info.description or "", SYS_TXT_SECONDARY)
        )

        if info.severity is None:
            for col in (_C_RESULTS, _C_ANALYZERS, _C_UNSAFE, _C_SEV, _C_FINDINGS):
                self._table.setItem(
                    row,
                    col,
                    _item(
                        "—" if col in (_C_RESULTS, _C_ANALYZERS) else "",
                        SYS_TXT_MUTED,
                        center=True,
                    ),
                )
            return

        n = info.n_results
        self._table.setItem(
            row,
            _C_RESULTS,
            _item(
                f"{n} RESULT{'S' if n != 1 else ''}",
                SYS_TXT_PRIMARY,
                center=True,
            ),
        )
        na = info.n_analyzers
        self._table.setItem(
            row,
            _C_ANALYZERS,
            _item(
                f"{na} ANALYZER{'S' if na != 1 else ''}" if na else "—",
                SYS_TXT_PRIMARY,
                center=True,
            ),
        )
        self._table.setItem(
            row,
            _C_UNSAFE,
            _item(
                "" if info.is_safe else "UNSAFE",
                SYS_BADGE_UNSAFE,
                center=True,
                bold=True,
            ),
        )

        badge_text = _SEV_BADGE_TEXT.get(sev_lower, sev_lower.upper())
        self._table.setItem(
            row,
            _C_SEV,
            _item(
                badge_text,
                _SEV_COLOUR.get(sev_lower, SYS_TXT_MUTED),
                center=True,
                bold=True,
            ),
        )

        if info.findings:
            counts: dict[str, int] = {}
            for f in info.findings:
                s = (f.get("severity") or "unknown").lower()
                counts[s] = counts.get(s, 0) + 1
            parts = [
                f"{s.upper()}({counts[s]})"
                for s in ("critical", "high", "medium", "low")
                if s in counts
            ]
            highest = next(
                (
                    _FIND_COLOURS[s]
                    for s in ("critical", "high", "medium", "low")
                    if s in counts
                ),
                SYS_TXT_MUTED,
            )
            self._table.setItem(
                row, _C_FINDINGS, _item("  ".join(parts), highest, bold=True)
            )
        else:
            self._table.setItem(row, _C_FINDINGS, _item(""))

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._infos):
            self.detail_requested.emit(self._infos[row].skill_id)

    def apply_filter(self, filter_key: str) -> None:
        for row, info in enumerate(self._infos):
            self._table.setRowHidden(
                row, filter_key != "all" and info.spec_type != filter_key
            )

    def clear(self) -> None:
        self._infos = []
        self._table.setRowCount(0)
