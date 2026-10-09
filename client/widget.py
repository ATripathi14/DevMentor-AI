import sys
import threading
import requests

try:
    import keyboard   # pip install keyboard  — provides OS-level global hotkeys
except ImportError:
    keyboard = None   # widget still works without it; hotkey is just disabled

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSystemTrayIcon, QMenu, QStyle, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint
from PySide6.QtGui import QShortcut, QKeySequence


#  Background poller — plain QThread run() loop, no QTimer on the worker.     
class LatestPoller(QThread):
    new_result = Signal(dict)
    error = Signal(str)

    def __init__(self, url: str, interval_s: float = 2.0, parent=None):
        super().__init__(parent)
        self._url = url
        self._interval_s = interval_s
        self._stop_event = threading.Event()
        self._last_fingerprint = None

    def stop(self):
        """Thread-safe: set flag, return immediately. Called from the GUI thread."""
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            self._tick()
            if self._stop_event.wait(self._interval_s):
                break

    def _tick(self):
        try:
            resp = requests.get(self._url, timeout=1.5)
            if resp.status_code != 200:
                self.error.emit(f"HTTP {resp.status_code}")
                return
            data = resp.json()
        except requests.exceptions.Timeout:
            self.error.emit("timeout")
            return
        except requests.exceptions.ConnectionError:
            # Server not running — expected during dev, stay silent.
            return
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
            return

        fp = data.get("fingerprint")
        if fp and fp != self._last_fingerprint:
            self._last_fingerprint = fp
            self.new_result.emit(data)


#  The widget                                                               
class DevMentorWidget(QWidget):
    """Floating, always-on-top error-explanation widget with theme + collapse."""

    # Theme
    DARK_QSS = """
        QWidget { background-color: #1f2933; }
        QLabel  { color: #eceff1; background-color: transparent; }
        QPushButton {
            background-color: #323f4b; color: #eceff1;
            border: 1px solid #3e4c59; border-radius: 4px;
            padding: 4px 8px; font-size: 12px;
        }
        QPushButton:hover   { background-color: #3e4c59; }
        QPushButton:pressed { background-color: #52606d; }
    """

    LIGHT_QSS = """
        QWidget { background-color: #f5f5f5; }
        QLabel  { color: #1f2933; background-color: transparent; }
        QPushButton {
            background-color: #e0e0e0; color: #1f2933;
            border: 1px solid #bdbdbd; border-radius: 4px;
            padding: 4px 8px; font-size: 12px;
        }
        QPushButton:hover   { background-color: #d5d5d5; }
        QPushButton:pressed { background-color: #c0c0c0; }
    """

    # --- Global hotkey to re-show the widget ------------------------------ #
    # Two forms: display string (tooltips / toasts) and the string syntax
    # expected by the `keyboard` library (lowercase, '+'-separated).
    SHOW_SHORTCUT_DISPLAY  = "Alt+D" if sys.platform == "darwin" else "Ctrl+Alt+D"
    SHOW_SHORTCUT_KEYBOARD = "alt+d" if sys.platform == "darwin" else "ctrl+alt+d"

    # Emitted from the hotkey's listener thread; delivered to the GUI thread
    # via Qt.QueuedConnection so widgets are only touched on the GUI thread.
    hotkey_pressed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevMentor AI")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.resize(380, 210)
        self.setMinimumSize(320, 160)

        geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.width() - self.width() - 24, geo.top() + 24)

        # UI state
        self._dark_mode = True
        self._collapsed = False
        self._expanded_size = None
        self._has_shown_tray_hint = False   # toast fires once per session
        self._drag_offset: QPoint | None = None

        # Build UI (order matters: tray before shortcuts) 
        self._build_ui()
        self._apply_theme()
        self._setup_tray_icon()

        # Escape: window-local. Fires only when this widget has focus — correct
        # behaviour so we never steal Escape from a terminal / editor.
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self._hide_with_hint)

        # Global hotkey to re-show the widget. Connected with QueuedConnection
        # so the slot runs on the GUI thread, not the keyboard listener thread.
        self.hotkey_pressed.connect(self._show_and_focus, Qt.QueuedConnection)
        self._register_global_hotkey()

        # Poller
        self._poller = LatestPoller(
            "http://localhost:8765/latest", interval_s=2.0, parent=self
        )
        self._poller.new_result.connect(self._on_new_result)
        self._poller.start()

    # UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # Header row: title + collapse chevron + theme toggle.
        header_row = QHBoxLayout()
        header_row.setSpacing(4)

        self.header = QLabel("DevMentor AI")
        self.header.setStyleSheet("font-weight: 600; font-size: 13px;")
        header_row.addWidget(self.header)
        header_row.addStretch(1)

        self.collapse_button = QPushButton("\u25be")  
        self.collapse_button.setFixedWidth(26)
        self.collapse_button.setToolTip("Collapse")
        self.collapse_button.clicked.connect(self._toggle_collapse)
        header_row.addWidget(self.collapse_button)

        self.theme_button = QPushButton("\u263d")     # theme icon
        self.theme_button.setFixedWidth(26)
        self.theme_button.setToolTip("Toggle light / dark")
        self.theme_button.clicked.connect(self._toggle_theme)
        header_row.addWidget(self.theme_button)

        root.addLayout(header_row)

        # Explanation label — hidden when collapsed.
        self.label = QLabel("Watching for errors...")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.label, 1)

        # Buttons wrapped in a container so we can hide the whole row at once.
        self.body_container = QWidget()
        button_row = QHBoxLayout(self.body_container)
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)

        self.copy_button = QPushButton("Copy")
        self.copy_button.clicked.connect(self._copy_explanation)
        button_row.addWidget(self.copy_button)

        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.clicked.connect(self._hide_with_hint)
        button_row.addWidget(self.dismiss_button)

        root.addWidget(self.body_container)

    def _setup_tray_icon(self):
        icon = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip(f"DevMentor AI — {self.SHOW_SHORTCUT_DISPLAY} to show")

        menu = QMenu()
        show_action = menu.addAction("Show Widget")
        show_action.triggered.connect(self._show_and_focus)
        hide_action = menu.addAction("Hide Widget")
        hide_action.triggered.connect(self._hide_with_hint)
        menu.addSeparator()
        quit_action = menu.addAction("Exit")
        quit_action.triggered.connect(self._full_shutdown)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    # hotkey
    def _register_global_hotkey(self):
        """Register the OS-level hotkey via the `keyboard` library, if available."""
        if keyboard is None:
            print(
                "[DevMentor] `keyboard` not installed — global hotkey disabled. "
                "Run: pip install keyboard",
                file=sys.stderr,
            )
            return
        try:
            keyboard.add_hotkey(self.SHOW_SHORTCUT_KEYBOARD, self.hotkey_pressed.emit)
        except Exception as exc:  # noqa: BLE001 — perms, missing /dev/input, etc.
            print(f"[DevMentor] global hotkey unavailable: {exc}", file=sys.stderr)

    # theme
    def _apply_theme(self):
        self.setStyleSheet(self.DARK_QSS if self._dark_mode else self.LIGHT_QSS)
        # Button shows what you'd get on click, not what you currently have.
        self.theme_button.setText("\u263d" if self._dark_mode else "\u2600")  # ☽ / ☀

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._apply_theme()

    # collapse
    def _toggle_collapse(self):
        if not self._collapsed:
            self._expanded_size = self.size()
            self.label.setVisible(False)
            self.body_container.setVisible(False)
            self.collapse_button.setText("\u25b8")  # ▸
            self.collapse_button.setToolTip("Expand")
            self.resize(self.width(), 44)
            self._collapsed = True
        else:
            self.label.setVisible(True)
            self.body_container.setVisible(True)
            self.collapse_button.setText("\u25be")  # ▾
            self.collapse_button.setToolTip("Collapse")
            if self._expanded_size is not None:
                self.resize(self._expanded_size)
            self._collapsed = False

    #  show / hide helpers
    def _show_and_focus(self):
        """Bring the widget back, raising it above other windows."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _hide_with_hint(self):
        """Hide the widget; first time per session, tell the user how to get it back."""
        self.hide()
        if (not self._has_shown_tray_hint
                and QSystemTrayIcon.isSystemTrayAvailable()):
            self.tray_icon.showMessage(
                "DevMentor AI is still running",
                f"Click the tray icon or press {self.SHOW_SHORTCUT_DISPLAY} to bring it back.",
                QSystemTrayIcon.Information,
                3000,
            )
            self._has_shown_tray_hint = True

    # slots
    def _on_new_result(self, data: dict):
        category = data.get("category", "")
        explanation = data.get("explanation", "")
        confidence = data.get("confidence")
        source = data.get("source", "ml")

        if confidence is not None and source == "ml":
            pct = int(confidence * 100)
            if confidence >= 0.70:
                band = "high"
            elif confidence >= 0.60:
                band = "medium"
            else:
                band = "low"
            header = f"[{category}] \u00b7 {band} confidence ({pct}%)"
        elif category:
            header = f"[{category}] \u00b7 pattern-matched"
        else:
            header = "DevMentor AI"

        text = f"{header}\n\n{explanation}" if explanation else header

        if self.label.text() != text:
            self.label.setText(text)
            # If collapsed, auto-expand so the user actually sees the new error.
            if self._collapsed:
                self._toggle_collapse()
            # If hidden, resurface the widget so the user never misses an error.
            if not self.isVisible():
                self._show_and_focus()

    def _copy_explanation(self):
        QApplication.clipboard().setText(self.label.text())
        self.copy_button.setText("Copied!")
        QTimer.singleShot(900, lambda: self.copy_button.setText("Copy"))

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            # Left-click: toggle visibility; always raise when showing.
            if self.isVisible():
                self._hide_with_hint()
            else:
                self._show_and_focus()

    # keys
    def keyPressEvent(self, event):
        # Escape is also bound via QShortcut (window-local). This is a safety net.
        if event.key() == Qt.Key_Escape:
            self._hide_with_hint()
        else:
            super().keyPressEvent(event)

    # drag
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        event.accept()

    #  shutdown 
    def _full_shutdown(self):
        # Unhook the global hotkey BEFORE the QObject dies, otherwise the
        # `keyboard` listener thread may call hotkey_pressed.emit() on a
        # QObject that's already been destroyed.
        if keyboard is not None:
            try:
                keyboard.remove_all_hotkeys()
            except Exception:
                pass

        if self._poller is not None and self._poller.isRunning():
            self._poller.stop()
            self._poller.wait(2000)

        if self.tray_icon is not None:
            self.tray_icon.hide()

        QApplication.instance().quit()

    def closeEvent(self, event):
        self._full_shutdown()
        event.accept()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = DevMentorWidget()
    window.show()
    window.activateWindow()   # give it focus so Escape works immediately
    sys.exit(app.exec())