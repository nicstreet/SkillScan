"""Pill toggle switch + label row for embedding in QMenu via QWidgetAction."""
from PyQt6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, Qt, pyqtProperty, pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget, QWidgetAction


# ---------------------------------------------------------------------------
# Toggle switch pill widget — handles its own mouse events directly
# ---------------------------------------------------------------------------

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    _TRACK_W, _TRACK_H = 29, 14
    _KNOB_R = 5

    def __init__(self, checked: bool = False, color: str = "#0ea5e9", parent=None):
        super().__init__(parent)
        self.setFixedSize(self._TRACK_W + 4, self._TRACK_H + 4)
        self._checked = checked
        self._on_color = QColor(color)
        self._pos: float = 1.0 if checked else 0.0

        self._anim = QPropertyAnimation(self, b"knob_pos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    @pyqtProperty(float)
    def knob_pos(self) -> float:
        return self._pos

    @knob_pos.setter
    def knob_pos(self, v: float) -> None:
        self._pos = v
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, animate: bool = True) -> None:
        if checked == self._checked:
            return
        self._checked = checked
        target = 1.0 if checked else 0.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._pos = target
            self.update()

    def setOnColor(self, color: str) -> None:
        self._on_color = QColor(color)
        self.update()

    def toggle(self) -> None:
        self.setChecked(not self._checked)   # let setChecked own the state change + animation
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(2, 2)

        # Blend track colour during animation
        if self._pos in (0.0, 1.0):
            track_color = self._on_color if self._checked else QColor("#94a3b8")
        else:
            off, on, t = QColor("#94a3b8"), self._on_color, self._pos
            track_color = QColor(
                int(off.red()   + (on.red()   - off.red())   * t),
                int(off.green() + (on.green() - off.green()) * t),
                int(off.blue()  + (on.blue()  - off.blue())  * t),
            )

        p.setBrush(track_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self._TRACK_W, self._TRACK_H,
                          self._TRACK_H / 2, self._TRACK_H / 2)

        travel = self._TRACK_W - self._TRACK_H
        cx = self._TRACK_H / 2 + self._pos * travel
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(cx, self._TRACK_H / 2), self._KNOB_R, self._KNOB_R)
        p.end()


# ---------------------------------------------------------------------------
# Row widget: [label ·····················] [toggle]
# ---------------------------------------------------------------------------

class ToggleRow(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, label: str, checked: bool = False,
                 color: str = "#0ea5e9", parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 12, 0)
        layout.setSpacing(8)

        self._label = QLabel(label)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._label)

        self._switch = ToggleSwitch(checked=checked, color=color)
        self._switch.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._switch)

        self._hovered = False

    # ------------------------------------------------------------------
    def isChecked(self) -> bool:
        return self._switch.isChecked()

    def setChecked(self, checked: bool) -> None:
        self._switch.setChecked(checked, animate=False)

    def setOnColor(self, color: str) -> None:
        self._switch.setOnColor(color)

    # ------------------------------------------------------------------
    # Both label and switch area trigger the toggle — coordinates don't
    # matter here because we own the whole row.
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._switch.toggle()
            self.toggled.emit(self._switch.isChecked())
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        if self._hovered:
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(255, 255, 255, 18))
            p.end()


# ---------------------------------------------------------------------------
# QWidgetAction wrapper
# ---------------------------------------------------------------------------

class ToggleAction(QWidgetAction):
    toggled = pyqtSignal(bool)

    def __init__(self, label: str, checked: bool = False,
                 color: str = "#0ea5e9", parent=None):
        super().__init__(parent)
        self._row = ToggleRow(label=label, checked=checked, color=color)
        self._row.toggled.connect(self.toggled)
        self.setDefaultWidget(self._row)

    def isChecked(self) -> bool:
        return self._row.isChecked()

    def setChecked(self, checked: bool) -> None:
        self._row.setChecked(checked)

    def setOnColor(self, color: str) -> None:
        self._row.setOnColor(color)
