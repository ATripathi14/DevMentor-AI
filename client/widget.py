import sys
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt


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
        layout.addWidget(self.label)

        dismiss_button = QPushButton("Dismiss")
        dismiss_button.clicked.connect(self.hide)  # hides, doesn't close
        layout.addWidget(dismiss_button)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DevMentorWidget()
    window.show()
    sys.exit(app.exec())