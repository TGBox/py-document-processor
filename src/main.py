import sys

from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow

APP_NAME = "py-document-processor"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
