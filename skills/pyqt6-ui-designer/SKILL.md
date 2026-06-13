---
name: pyqt6-ui-designer
description: Design and implement professional PyQt6 desktop UI — frameless windows, dark-theme palettes, custom widgets, responsive layouts, and signal/slot patterns for Windows applications
version: "1.0.0"
authors:
  - name: SkillScan Project
license: MIT
tags: [python, pyqt6, ui, desktop, windows, dark-theme, widgets]
allowed-tools: [Python, Read, Write, Edit]
---

# PyQt6 UI Designer

You are an expert PyQt6 UI engineer specialising in professional-grade Windows desktop applications. When this skill is active, apply all guidance below to every piece of UI code you write or review.

---

## Design Principles

### 60-30-10 Colour Rule
Every UI must respect a three-tier colour hierarchy:
- **60% — Canvas / anchor**: the dominant background applied to the window, main panels, and cards. Dark theme default: `#0F172A`.
- **30% — Structure**: subordinate surfaces — title bars, sidebars, toolbars, sub-panes. Dark theme default: `#1E293B`.
- **10% — Accent**: CTA buttons, active nav indicators, focus rings, links. Dark theme default: `#0D9488`.

Never invert this ratio. More than three active hues creates visual noise.

### Colour Tokens
Always define colours as named constants in a `_palette.py` module. Never hardcode hex values in widget files. Import tokens by name:

```python
# _palette.py
ANCHOR       = "#0F172A"   # 60% canvas
DEEP_SURFACE = "#1E293B"   # 30% structure
DIVIDER      = "#243846"   # borders at ~15% opacity on ANCHOR
ACCENT       = "#0D9488"   # 10% CTA
HOVER_FOCUS  = "#0F766E"   # button hover
LIGHT_CANVAS = "#F0FDFA"   # primary text
MUTED_TEXT   = "#475569"   # secondary text
SOFT_SURFACE = "#CCFBF1"   # accent text / highlight
```

### Typography
- Primary reading text: `LIGHT_CANVAS` (`#F0FDFA`) — headings, tile names, labels
- Secondary / metadata: `MUTED_TEXT` (`#475569`) — dates, subtitles, helper text
- Accent emphasis: `SOFT_SURFACE` (`#CCFBF1`) — links, highlighted values
- Font: **Segoe UI** at 10–13px; monospace sections use **Consolas** 10px
- Never use pure white (`#FFFFFF`) or pure black (`#000000`)

### Severity / Status Colours
Use these consistently across badges, borders, and indicators:

| State | Accent | Background | Light text |
|---|---|---|---|
| Critical | `#E11D48` | `#2D1217` | `#FFF1F2` |
| High | `#EA580C` | `#2D1A10` | `#FFF7ED` |
| Medium | `#D97706` | `#2A200E` | `#FEF3C7` |
| Clean / Safe | `#059669` | `#022C22` | `#D1FAE5` |

---

## Window Patterns

### Frameless Window (preferred for primary windows and dialogs)

Always use this pattern for main windows and modal dialogs — it gives full control over chrome and avoids Windows title bar theming conflicts:

```python
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QPainter, QPainterPath, QColor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos: QPoint | None = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(8, 8, -8, -8), 12, 12)
        p.fillPath(path, QColor("#0F172A"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
```

### Drop Shadow
Apply to the outermost card or window frame:

```python
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor

shadow = QGraphicsDropShadowEffect()
shadow.setBlurRadius(28)
shadow.setOffset(0, 6)
shadow.setColor(QColor(0, 0, 0, 160))
widget.setGraphicsEffect(shadow)
```

### Custom Title Bar
Every frameless window needs a custom title bar. Provide:
- App name / wordmark (left)
- Drag region (full width)
- Segoe Fluent Icons buttons right-aligned: minimise ``, close `` (no maximise unless explicitly required)
- Close button hover: `#E11D48` background

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

class TitleBar(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: #F0FDFA; font-weight: 600;")
        layout.addWidget(lbl)
        layout.addStretch()

        for icon, slot in [("", parent.showMinimized), ("", parent.close)]:
            btn = QPushButton(icon)
            btn.setFont(QFont("Segoe Fluent Icons", 12))
            btn.setFixedSize(32, 28)
            btn.setFlat(True)
            btn.clicked.connect(slot)
            layout.addWidget(btn)
```

---

## Layout Guidance

### Hierarchy of layout types

1. **`QVBoxLayout` / `QHBoxLayout`** — use for simple linear stacks. Set `setContentsMargins(0, 0, 0, 0)` and `setSpacing(0)` on root layouts; use explicit `addSpacing(N)` for intentional gaps.
2. **`QSplitter`** — use for resizable two-pane layouts (folder list | content, master | detail). Always set `setSizes([left_px, right_px])` as a sensible default.
3. **`QStackedWidget`** — use for nav-driven pane switching. Switch with `setCurrentIndex(n)`; each pane manages its own lazy load.
4. **`QGridLayout`** — use for form-style label/value rows. Prefer `QFormLayout` for simple forms.
5. **`QFlowLayout`** — use for tile grids that reflow on resize. Implement as a custom `QLayout` subclass.

### Content margins
- Root window layout: `(14, 14, 14, 14)` minimum to give shadow room at edges
- Card inner content: `(16, 16, 16, 16)`
- Toolbar rows: `(10, 6, 10, 6)`
- Never use negative margins

### Spacing rhythm
- Between related elements: 4–6px
- Between groups: 12–16px
- Section headers to content: 8px
- Cards in a grid: 10px gap

---

## Widget Patterns

### Styled push buttons
```python
btn.setStyleSheet(f"""
    QPushButton {{
        background: {ACCENT};
        color: {LIGHT_CANVAS};
        border-radius: 6px;
        padding: 6px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {HOVER_FOCUS}; }}
    QPushButton:pressed {{ background: #0a5e58; }}
    QPushButton:disabled {{ background: {DEEP_SURFACE}; color: {MUTED_TEXT}; }}
""")
```

### Coloured badge / pill
Use `QLabel` with stylesheet. Always include horizontal padding so the background colour is visible at the sides:

```python
def make_badge(text: str, fg: str, bg: str) -> QLabel:
    lbl = QLabel(f" {text} ")   # non-breaking spaces for padding
    lbl.setStyleSheet(f"""
        QLabel {{
            color: {fg};
            background: {bg};
            border-radius: 4px;
            font-size: 9px;
            font-weight: 700;
            padding: 1px 2px;
        }}
    """)
    return lbl
```

### Card frame
```python
from PyQt6.QtWidgets import QFrame

card = QFrame()
card.setStyleSheet(f"""
    QFrame {{
        background: {DEEP_SURFACE};
        border-radius: 10px;
        border: 1px solid {DIVIDER};
    }}
""")
```

### Divider line
```python
line = QFrame()
line.setFrameShape(QFrame.Shape.HLine)
line.setStyleSheet(f"color: {DIVIDER}; background: {DIVIDER}; max-height: 1px;")
```

### Read-only text output (scan results, logs)
Use `QTextBrowser` (not `QTextEdit`) for displaying HTML content — it disables editing, enables link navigation, and handles `setHtml()` correctly:

```python
browser = QTextBrowser()
browser.setOpenExternalLinks(True)
browser.setStyleSheet(f"background: {ANCHOR}; color: {LIGHT_CANVAS}; border: none;")
browser.setHtml(html_content)
```

---

## Signal / Slot Patterns

### Long-running work — always use QThread
Never block the event loop. Any operation taking more than ~50ms (file I/O, network, subprocess) must run on a worker thread:

```python
from PyQt6.QtCore import QThread, pyqtSignal

class Worker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, object)  # success, result

    def __init__(self, task_args):
        super().__init__()
        self._args = task_args

    def run(self):
        try:
            result = do_work(self._args)
            self.finished.emit(True, result)
        except Exception as e:
            self.finished.emit(False, str(e))
```

Hold a reference to the worker on the parent object (`self._worker = Worker(...)`) to prevent garbage collection before the thread finishes.

### QProcess for subprocesses
Use `QProcess` instead of `subprocess` for long-running CLI tools. This delivers stdout asynchronously to the Qt event loop:

```python
proc = QProcess()
proc.readyReadStandardOutput.connect(lambda: handle_line(proc.readAllStandardOutput()))
proc.finished.connect(on_done)
proc.start(exe, args)
```

Inject secrets (API keys) via `QProcess.setProcessEnvironment()` — never as CLI arguments (they appear in Process Explorer / Task Manager).

---

## Performance Considerations

- **Lazy view loading**: instantiate nav pane widgets on first visit, not at startup. Wrap in `_ensure_loaded()` guard.
- **Thumbnail / image caching**: use `QPixmapCache` with a string key. Check before loading from disk.
- **Stylesheet batching**: apply stylesheets to container widgets rather than individual leaf widgets where possible — fewer style recalculations.
- **Avoid `repaint()`**: call `update()` instead — it coalesces multiple invalidations into one paint event per frame.
- **`QSizePolicy`**: set explicit size policies on widgets in splitters to prevent unexpected stretch.

---

## Constraints

- Never use `time.sleep()` or `QThread.sleep()` on the main thread.
- Never call Qt UI methods from a worker `QThread.run()` — use signals to communicate results back to the main thread.
- Never use `exec()` on `QDialog` from within a `QThread`.
- Do not use `app.processEvents()` as a workaround for blocking code — fix the threading instead.
- Always set a minimum window size (`setMinimumSize`) — never let a window collapse to zero dimensions.
- Prefer `QSplitter` over manual pixel geometry for resizable pane layouts.
- Icon fonts (Segoe Fluent Icons, Material Icons) must be loaded via `QFontDatabase.addApplicationFont()` if not system-installed; fall back gracefully to Unicode symbols or text labels.
