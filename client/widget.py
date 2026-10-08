import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSystemTrayIcon, QMenu, QStyle, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QObject, QPoint, Slot, QMetaObject
)

class LatestPoller(QObject):
    """Polls /latest on a worker thread and emits only when the fingerprint changes."""

    new_result = Signal(dict)   # emitted with the full payload when a NEW fingerprint appears
    polled = Signal()           # emitted on every successful poll
    error = Signal(str)         # emitted when the server is unreachable / returns garbage

    def __init__(self, url: str, interval_ms: int = 2000):
        super().__init__()
        self._url = url
        self._interval_ms = interval_ms
        self._last_fingerprint = None
        self._timer = None  # created inside start() so it lives on the worker thread

    @Slot()
    def start(self):
        """Runs on the worker thread — creates the timer there so it is thread-owned."""
        self._timer = QTimer()
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @Slot()
    def stop(self):
        """Must only run on the worker thread — invoked via queued signal from the GUI."""
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None

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
        except Exception as exc:  # noqa: BLE001 — defensive: never crash the thread
            self.error.emit(str(exc))
            return

        self.polled.emit()

        fp = data.get("fingerprint")
        if fp and fp != self._last_fingerprint:
            self._last_fingerprint = fp
            self.new_result.emit(data)


#  The widget                                                                 
class DevMentorWidget(QWidget):
    """Floating, always-on-top error-explanation widget."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevMentor AI")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Resizable window instead of setFixedSize — avoids layout thrash on repaint.
        self.resize(380, 210)
        self.setMinimumSize(320, 160)

        # Top-right placement using the available (non-taskbar) screen area.
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.width() - self.width() - 24, geo.top() + 24)

        self._build_ui()

        # Drag state.
        self._drag_offset: QPoint | None = None

        # --- Polling thread ---
        self._thread = QThread(self)
        self._poller = LatestPoller("http://localhost:8765/latest", interval_ms=2000)
        self._poller.moveToThread(self._thread)

        self._thread.started.connect(self._poller.start)
        self._poller.new_result.connect(self._on_new_result)
        self._thread.start()

        # Tray icon.
        self._setup_tray_icon()

    # UI 
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = QLabel("DevMentor AI")
        header.setStyleSheet("font-weight: 600; font-size: 13px; color: #cfd8dc;")
        root.addWidget(header)

        self.label = QLabel("Watching for errors...")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label.setStyleSheet("color: #eceff1; font-size: 12px;")
        root.addWidget(self.label, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)

        self.copy_button = QPushButton("Copy")
        self.copy_button.clicked.connect(self._copy_explanation)

        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.clicked.connect(self.hide)

        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.dismiss_button)
        root.addLayout(button_row)

        self.setStyleSheet(
            """
            QWidget { background-color: #1f2933; }
            QPushButton {
                background-color: #323f4b; color: #eceff1;
                border: 1px solid #3e4c59; border-radius: 4px;
                padding: 5px 10px; font-size: 12px;
            }
            QPushButton:hover { background-color: #3e4c59; }
            QPushButton:pressed { background-color: #52606d; }
            """
        )

    def _setup_tray_icon(self):
        icon = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("DevMentor AI")

        menu = QMenu()
        show_action = menu.addAction("Show Widget")
        show_action.triggered.connect(self.show)
        hide_action = menu.addAction("Hide Widget")
        hide_action.triggered.connect(self.hide)
        menu.addSeparator()
        quit_action = menu.addAction("Exit")
        quit_action.triggered.connect(self._full_shutdown)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_new_result(self, data: dict):
        """Runs on the GUI thread — safe to touch widgets here."""
        category = data.get("category", "")
        explanation = data.get("explanation", "")
        confidence = data.get("confidence")
        source = data.get("source", "ml")  # 'ml' or 'rules'

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
            # Rules-based fallback — no numeric confidence to show.
            header = f"[{category}] \u00b7 pattern-matched"
        else:
            header = "DevMentor AI"

        text = f"{header}\n\n{explanation}" if explanation else header

        # Only repaint when the text actually differs.
        if self.label.text() != text:
            self.label.setText(text)

    def _copy_explanation(self):
        QApplication.clipboard().setText(self.label.text())
        self.copy_button.setText("Copied!")
        QTimer.singleShot(900, lambda: self.copy_button.setText("Copy"))

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.hide() if self.isVisible() else self.show()

    #  drag 
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
        """Clean teardown: stop poller on its own thread, kill tray, quit the loop."""
        # Queue the stop onto the worker thread so the QTimer is stopped by its owner.
        # Calling .stop() directly from the GUI thread triggers:
        #   QObject::killTimer: Timers cannot be stopped from another thread
        if self._poller is not None:
            QMetaObject.invokeMethod(self._poller, "stop", Qt.QueuedConnection)

        if self._thread is not None and self._thread.isRunning():
            # Give the queued stop() a moment to run on the worker, then quit its loop.
            self._thread.quit()
            self._thread.wait(1500)

        if self.tray_icon is not None:
            self.tray_icon.hide()

        QApplication.instance().quit()

    def closeEvent(self, event):
        """Clicking the OS ✕ button fully terminates the process (no zombie in terminal)."""
        self._full_shutdown()
        event.accept()
        super().closeEvent(event)


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Keep the tray alive when the widget is hidden via Dismiss.
    # ✕ / tray-Exit still quit the whole app via _full_shutdown().
    app.setQuitOnLastWindowClosed(False)
    window = DevMentorWidget()
    window.show()
    sys.exit(app.exec())