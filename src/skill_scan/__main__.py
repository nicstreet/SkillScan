"""
Entry point.

  python -m skill_scan                   # launch main window + satellite tray
  python -m skill_scan --scan <path>     # scan a path (from context menu / CLI)
"""

import os
import sys

os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="skill_scan", add_help=False)
    parser.add_argument("--scan", metavar="PATH", default=None)
    args, _ = parser.parse_known_args()

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPalette
    from PyQt6.QtWidgets import QProxyStyle, QStyle
    from .ui._palette import SYS_ACTION_PRIMARY, SYS_ACTION_HOVER, SYS_TXT_PRIMARY

    class _TooltipStyle(QProxyStyle):
        _BG = QColor(SYS_ACTION_PRIMARY)
        _BORDER = QColor(SYS_ACTION_HOVER)

        def drawPrimitive(self, element, option, painter, widget=None):
            if element == QStyle.PrimitiveElement.PE_PanelTipLabel:
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(self._BG))
                painter.setPen(QPen(self._BORDER, 1))
                painter.drawRoundedRect(option.rect.adjusted(0, 0, -1, -1), 4, 4)
                painter.restore()
            else:
                super().drawPrimitive(element, option, painter, widget)

    app.setStyle(_TooltipStyle())
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(SYS_TXT_PRIMARY))
    app.setPalette(palette)

    from .ui._icons import load_fonts

    load_fonts()

    from .ui.tray import TrayApp
    from .ui.main_window import MainWindow

    tray = TrayApp(app, initial_scan=args.scan)  # satellite tray
    window = MainWindow(tray_app=tray)  # primary window
    tray.set_main_window(window)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
