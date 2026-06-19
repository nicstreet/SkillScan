"""Taskbar status routines — named wrappers around _TaskBar.set_status().

Each routine drives the existing dot+text status indicator in the toolbar.
Views emit a ``status_changed = pyqtSignal(str, str)`` signal; main_window
connects it to ``_taskbar.set_status``.  Pass that emit callable here::

    self._ai_status = AiStatusRoutine(lambda m, c: self.status_changed.emit(m, c))

Then call named phase methods during each operation::

    self._ai_status.authenticating()   # amber dot
    self._ai_status.sending()          # amber dot
    self._ai_status.done("Complete")   # green, resets to Ready after 3 s
    self._ai_status.error("Timeout")   # red, stays until next call
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QTimer

from ._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BORDER_ADVISORY,
)

_SetFn = Callable[[str, str], None]
_RESET_DELAY_MS = 3000


class StatusRoutine:
    """Base — shared done/error/ready methods for all operation types."""

    def __init__(self, emit_fn: _SetFn) -> None:
        self._fn = emit_fn

    def _set(self, msg: str, color: str) -> None:
        self._fn(msg, color)

    def ready(self) -> None:
        """Immediately reset to 'Ready' with the default primary colour."""
        self._set("Ready", SYS_ACTION_PRIMARY)

    def done(self, text: str = "Done") -> None:
        """Success state with custom text, auto-resets to 'Ready' after 3 s."""
        self._set(text, SYS_BADGE_SAFE)
        QTimer.singleShot(
            _RESET_DELAY_MS, lambda: self._set("Ready", SYS_ACTION_PRIMARY)
        )

    def error(self, text: str = "Error") -> None:
        """Red dot with error text - stays until the next call."""
        self._set(text, SYS_BADGE_UNSAFE)


class AiStatusRoutine(StatusRoutine):
    """Authenticating -> Sending -> Receiving -> done / error."""

    def authenticating(self) -> None:
        self._set("Authenticating…", SYS_BORDER_ADVISORY)

    def sending(self) -> None:
        self._set("Sending…", SYS_BORDER_ADVISORY)

    def receiving(self) -> None:
        self._set("Receiving…", SYS_ACTION_PRIMARY)


class SaveStatusRoutine(StatusRoutine):
    """Validating -> Writing -> done / error."""

    def validating(self) -> None:
        self._set("Validating…", SYS_BORDER_ADVISORY)

    def writing(self) -> None:
        self._set("Writing…", SYS_BORDER_ADVISORY)


class ScanStatusRoutine(StatusRoutine):
    """Staging -> Scanning -> Analysing -> done / error."""

    def staging(self) -> None:
        self._set("Staging…", SYS_BORDER_ADVISORY)

    def scanning(self) -> None:
        self._set("Scanning…", SYS_BORDER_ADVISORY)

    def analysing(self) -> None:
        self._set("Analysing…", SYS_ACTION_PRIMARY)


class UpdateStatusRoutine(StatusRoutine):
    """Fetching -> Applying -> done / error."""

    def fetching(self) -> None:
        self._set("Fetching…", SYS_BORDER_ADVISORY)

    def applying(self) -> None:
        self._set("Applying…", SYS_ACTION_PRIMARY)
