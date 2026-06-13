"""Wrap-on-overflow flow layout — items fill left to right and wrap to the next row."""
from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QSizePolicy, QWidget, QWidgetItem


class FlowLayout(QLayout):
    def __init__(self, parent=None, h_spacing: int = 10, v_spacing: int = 10):
        super().__init__(parent)
        self._items: list[QWidgetItem] = []
        self._h_space = h_spacing
        self._v_space = v_spacing

    # ── QLayout interface ────────────────────────────────────────────────────

    def addWidget(self, widget: QWidget) -> None:
        # addChildWidget reparents the widget to the layout's owner and handles
        # Qt's internal bookkeeping — must be called before wrapping in QWidgetItem.
        self.addChildWidget(widget)
        item = QWidgetItem(widget)
        self._items.append(item)
        self.invalidate()

    def addItem(self, item) -> None:
        self._items.append(item)
        self.invalidate()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def reorder_by(self, widgets: list) -> None:
        """Rearrange existing items to match the given widget order, in place."""
        item_map = {item.widget(): item for item in self._items if item.widget()}
        self._items = [item_map[w] for w in widgets if w in item_map]
        self.invalidate()

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        # Return the height needed to lay out all items at the current parent width.
        pw = self.parentWidget()
        w = pw.width() if pw else 0
        h = self._do_layout(QRect(0, 0, w or 800, 0), test_only=True)
        return QSize(w or 200, h)

    def minimumSizeHint(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    # ── Layout engine ─────────────────────────────────────────────────────────

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, row_h = r.x(), r.y(), 0

        right_edge = r.x() + r.width()  # exclusive; r.right() is inclusive (off-by-one)
        for item in self._items:
            iw = item.sizeHint().width()
            ih = item.sizeHint().height()
            next_x = x + iw + self._h_space
            if next_x - self._h_space > right_edge and row_h > 0:
                x = r.x()
                y += row_h + self._v_space
                next_x = x + iw + self._h_space
                row_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            row_h = max(row_h, ih)

        return y + row_h - rect.y() + m.bottom()


class FlowContainer(QWidget):
    """
    QWidget wrapper for FlowLayout.
    - Overrides sizeHint/hasHeightForWidth so QScrollArea sizes content correctly.
    - Responds to resize events to stretch tiles to fill each row.
    """

    def __init__(self, h_spacing: int = 10, v_spacing: int = 10,
                 min_tile_w: int = 260, parent=None):
        super().__init__(parent)
        self._min_tile_w = min_tile_w
        self._forced_cols: int | None = None
        self._flow = FlowLayout(self, h_spacing=h_spacing, v_spacing=v_spacing)
        sp = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

    def set_min_tile_w(self, w: int) -> None:
        self._min_tile_w = w
        self._forced_cols = None
        self._update_tile_widths()
        self.updateGeometry()

    def set_cols(self, n: int) -> None:
        """Force an exact column count, bypassing the min-tile-width heuristic."""
        self._forced_cols = n
        self._update_tile_widths()
        self.updateGeometry()

    @property
    def flow(self) -> FlowLayout:
        return self._flow

    def addWidget(self, widget: QWidget) -> None:
        self._flow.addWidget(widget)
        self._update_tile_widths()
        self.updateGeometry()

    def setContentsMargins(self, left, top, right, bottom) -> None:
        self._flow.setContentsMargins(left, top, right, bottom)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._update_tile_widths()

    def _update_tile_widths(self) -> None:
        m = self._flow.contentsMargins()
        avail = self.width() - m.left() - m.right()
        if avail <= 0:
            return
        h_sp = self._flow._h_space
        if self._forced_cols is not None:
            n_cols = max(1, self._forced_cols)
        else:
            n_cols = max(1, (avail + h_sp) // (self._min_tile_w + h_sp))
        tile_w = (avail - (n_cols - 1) * h_sp) // n_cols
        for i in range(self._flow.count()):
            item = self._flow.itemAt(i)
            if item and item.widget():
                item.widget().setFixedWidth(tile_w)
        self.updateGeometry()

    def hasHeightForWidth(self) -> bool:
        return True

    def sizeHint(self) -> QSize:
        w = self.width() or 800
        h = self._flow.heightForWidth(w)
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        return QSize(200, 100)
