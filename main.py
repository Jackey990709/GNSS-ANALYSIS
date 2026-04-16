import sys
from PySide6.QtWidgets import QApplication
from src.controller import MainController


def main():
    try:
        app = QApplication(sys.argv)

        font = app.font()
        font.setFamily("Microsoft YaHei")
        app.setFont(font)

        ui = MainController()
        ui.show()

        return app.exec()
    except Exception:
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()
