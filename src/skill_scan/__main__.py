"""
Entry point.

  python -m skill_scan                   # launch main window + satellite tray
  python -m skill_scan --scan <path>     # scan a path (from context menu / CLI)
"""

import sys


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="skill_scan", add_help=False)
    parser.add_argument("--scan", metavar="PATH", default=None)
    args, _ = parser.parse_known_args()

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    from .ui.tray import TrayApp
    from .ui.main_window import MainWindow

    tray = TrayApp(app, initial_scan=args.scan)  # satellite tray
    window = MainWindow(tray_app=tray)  # primary window
    tray.set_main_window(window)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
