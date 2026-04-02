from typing import Optional

from PySide6.QtWidgets import QDialog, QMessageBox, QComboBox

from src.libs.parser import write_yml
from src.ui.antenna_ui import Ui_Antenna
from src.util.msg import Message
from src.util.param import parameters


class AntennaUI(QDialog, Ui_Antenna):
    def __init__(self, combox: Optional[QComboBox] = None, *args):
        super(AntennaUI, self).__init__()
        self.setupUi(self)
        self.combox: Optional[QComboBox] = combox
        self.args = args

    def show(self) -> None:
        super(AntennaUI, self).show()
        if self.combox:
            self.edit_name.setText(self.combox.currentText())

    def add_antenna(self):
        text = self.edit_name.text().strip()
        if not text or not self.args:
            QMessageBox.warning(
                self,
                Message.MSG_LABEL,
                Message.MSG_COORDINATE_NAME_EMPTY,
                QMessageBox.StandardButton.Yes,
            )
            return
        parameters["coordinates"][text] = self.args
        write_yml(parameters)
        if self.combox:
            self.combox.clear()
            self.combox.addItems(list(parameters["coordinates"].keys()))

        self.close()
