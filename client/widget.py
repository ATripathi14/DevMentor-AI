import sys
import requests
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer


class DevMentorWidget(QWidget):
    """The main floating widget window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevMentor AI")

        # Always-on-top so the widget stays visible over the IDE/terminal.
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Small, fixed size — this is a notification widget, not a full app window.
        self.setFixedSize(360, 180)

        # Positioned in the top-right corner of the screen.
        screen_geometry = QApplication.primaryScreen().geometry()
        x = screen_geometry.width() - self.width() - 20
        y = 40
        self.move(x, y)

        layout = QVBoxLayout()

        self.label = QLabel("Watching for errors...")
        self.label.setWordWrap(True)  # long explanations wrap instead of overflowing
        layout.addWidget(self.label)

        dismiss_button = QPushButton("Dismiss")
        dismiss_button.clicked.connect(self.hide)  # hides the widget, doesn't close it
        layout.addWidget(dismiss_button)

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_explanation) #copies the current explanation text to clipboard 
        layout.addWidget(copy_button)

        self.setLayout(layout)

        # Tracking the fingerprint of the last error displayed, so we only
        # update the label when something genuinely new comes in.
        self.last_fingerprint = None

        # Poll the local service every 2 seconds for a new result.
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(2000)  # milliseconds -> 2 seconds

    def check_for_updates(self):
        """Polls /latest and updates the label if a new error has appeared."""
        try:
            response = requests.get("http://localhost:8765/latest", timeout=2)
            data = response.json()

            fingerprint = data.get("fingerprint")
            # Only updating if it is a new result that we haven't shown yet.
            if fingerprint and fingerprint != self.last_fingerprint:
                self.last_fingerprint = fingerprint
                explanation = data.get("explanation", "")
                category = data.get("category", "")
                self.label.setText(f"[{category}] {explanation}")
        except requests.exceptions.ConnectionError:
            pass   # Local service not running — leave the current label as-it-is.

    def copy_explanation(self):
        """Copies the current label text to the system clipboard."""
        QApplication.clipboard().setText(self.label.text())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DevMentorWidget()
    window.show()
    sys.exit(app.exec())