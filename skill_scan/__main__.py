"""
Entry point.

  python -m skill_scan                   # launch tray app
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
    tray = TrayApp(app, initial_scan=args.scan)  # noqa: F841  (keep reference)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
