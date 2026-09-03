import logging
import sys
import traceback
from PySide6.QtGui import QFont, QIcon, QTextCursor
from PySide6.QtCore import QDateTime, QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QCheckBox,
    QFileDialog,
    QListWidgetItem,
    QApplication,
)
from pathlib import Path


from src import CLIENT_VERSION, title
from src.libs.parser import write_yml
from src.libs.license import LicenseValidationError, LicenseValidator
from src.util.const import File
from src.util.msg import DialogMessage, Message
from src.util.param import parameters
from src.ui.Main_ui import Ui_MainView
from src.util.utils import check_log_file

logger = logging.getLogger(__name__)
LICENSE_CHECK_INTERVAL_MS = 12 * 60 * 60 * 1000


class LicenseCheckWorker(QObject):
    """在后台线程执行 license 校验，避免阻塞 GUI 主线程。"""

    finished = Signal(object)  # None=成功，否则为错误文案

    def run(self) -> None:
        print("LicenseCheckWorker: run() called in thread:", QThread.currentThread())
        try:
            license_path = Path(sys.argv[0]).resolve().parent / "license.lic"
            LicenseValidator(license_path).validate()
            self.finished.emit(None)
        except LicenseValidationError as exc:
            logger.warning("License validation failed: %s", exc)
            self.finished.emit(str(exc))


class MainView(Ui_MainView, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        QApplication.setStyle("Fusion")

        self.setWindowIcon(QIcon(rf".//res//images//icon.ico"))
        self.setWindowTitle(f"GNSSAnalysis{title}-{CLIENT_VERSION}")

        self.filepath: str = ""
        self.temp_filepath: str = ""
        self.check_list: list[QCheckBox] = []
        self.endswith = [".log"]

        self.on_box_mode_currentIndexChanged(0)
        self.on_combo_type_currentIndexChanged(0)

        # license 校验通过前禁用"开始"，避免用户在结果出来前触发同步校验造成卡顿。
        self.btn_start.setEnabled(False)
        self._license_check_timer = QTimer(self)
        self._license_check_timer.setInterval(LICENSE_CHECK_INTERVAL_MS)
        self._license_check_timer.timeout.connect(self._start_background_license_check)
        self._start_background_license_check()

    def _start_background_license_check(self) -> None:
        """后台校验 license，避免启动时阻塞 GUI 主线程。"""
        self._license_worker = LicenseCheckWorker()
        self._license_thread = QThread(self)
        self._license_worker.moveToThread(self._license_thread)
        self._license_thread.started.connect(self._license_worker.run)
        self._license_worker.finished.connect(self._on_license_check_done)
        self._license_worker.finished.connect(self._license_thread.quit)
        self._license_worker.finished.connect(self._license_worker.deleteLater)
        self._license_thread.finished.connect(self._license_thread.deleteLater)
        self._license_thread.start()

    @Slot(object)
    def _on_license_check_done(self, error: object) -> None:
        if error:
            self.show_warning(str(error))
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return
        # 校验通过，启用"开始"按钮。
        self.btn_start.setEnabled(True)
        if not self._license_check_timer.isActive():
            self._license_check_timer.start()

    @Slot(int)
    def on_box_mode_currentIndexChanged(self, index: int):
        self.frame_static.setEnabled(not bool(index))
        self.frame_dynamic.setEnabled(bool(index))

    @Slot(str)
    def on_box_antenna_currentTextChanged(self, text: str):
        if text in parameters["coordinates"]:
            self.edit_lat.setText(str(parameters["coordinates"][text][0]))
            self.edit_lng.setText(str(parameters["coordinates"][text][1]))
            self.edit_hgt.setText(str(parameters["coordinates"][text][2]))

    @Slot()
    def on_btn_del_clicked(self):
        if (
            self.show_warning(
                Message.MSG_COORDINATE_DELETE % self.box_antenna.currentText()
            )
            == QMessageBox.StandardButton.Ok
        ):
            text = self.box_antenna.currentText()
            if text in parameters["coordinates"]:
                del parameters["coordinates"][text]
                self.init_coordinates()
                write_yml(parameters)

    @Slot(bool)
    def on_box_std_toggled(self, checked: bool):
        self.box_antenna.setEnabled(not checked)

    @Slot()
    def on_btn_ref_clicked(self):
        filepath: str = QFileDialog.getOpenFileName(
            self,
            DialogMessage.SELECTED_FILE,
            self.filepath,
            "Log Files (*)",
        )[0]

        if filepath:
            self.edit_ref.setText(filepath)

    @Slot(int)
    def on_combo_type_currentIndexChanged(self, index: int):
        self.frame_position.setEnabled(index == 0)
        self.frame_pps.setEnabled(index == 1)
        self.endswith = [".log"] if index == 0 else [".log", ".txt", ".ubx"]
        self.refresh_ui()

    @Slot()
    def on_btn_json_clicked(self):
        json_path: str = QFileDialog.getOpenFileName(
            self,
            DialogMessage.SELECTED_FILE,
            self.filepath + f"\\{File.JSON_NAME}",
            "JSON Files (*.json)",
        )[0]

        if json_path:
            self.edit_json.setText(json_path)

    def init_coordinates(self):
        self.box_antenna.clear()
        self.box_antenna.addItems(list(parameters["coordinates"].keys()))

    def open_folder(self):
        self.temp_filepath = QFileDialog.getExistingDirectory(
            self, DialogMessage.SELECTED_FOLDER, self.filepath
        )

        if not self.temp_filepath:
            return

        self.filepath = self.temp_filepath
        self.refresh_ui()

    def refresh_ui(self):
        self.check_list.clear()
        self.widget_log_file.clear()

        try:
            for file in check_log_file(self.filepath, endswith=self.endswith):
                filename = file.split("/")[-1]
                checkbox = QCheckBox(filename)
                font = QFont()
                font.setFamily("Calibri")
                font.setPointSize(9)
                checkbox.setFont(font)
                item = QListWidgetItem()
                self.widget_log_file.addItem(item)
                self.widget_log_file.setItemWidget(item, checkbox)
                checkbox.setChecked(True)
                self.check_list.append(checkbox)

            if self.filepath:
                self.lineEditFolder.setText(self.filepath.replace("/", "\\"))
                self.edit_json.setText(
                    self.filepath.replace("/", "\\") + f"\\{File.JSON_NAME}"
                )
        except FileNotFoundError:
            return

    def get_file_list(self) -> list:
        check_list = [item for item in self.check_list if item.isChecked()]
        if not check_list:
            self.show_warning(Message.MSG_NO_FILE_SELECT)
            return []
        return check_list

    def log_signal_call(self, msg):
        self.textBrowser_log.moveCursor(QTextCursor.MoveOperation.End)
        current_date_time = QDateTime.currentDateTime().toString(
            "yyyy-MM-dd HH:mm:ss.zzz"
        )
        self.textBrowser_log.insertHtml(f"<p>{current_date_time} - {msg}</p>")
        self.textBrowser_log.insertHtml("<p><br/></p>")

    def end_signal_call(self):
        self.set_element_enable(True)

    def set_element_enable(self, enabled):
        self.frame.setEnabled(enabled)
        self.frame_2.setEnabled(enabled)
        self.frame_3.setEnabled(enabled)

    def show_warning(self, message: str) -> QMessageBox.StandardButton:
        return QMessageBox.warning(
            self,
            Message.MSG_LABEL,
            message,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )

    def catch_exceptions(self, tr, value, tb):
        traceback_format = traceback.format_exception(tr, value, tb)
        traceback_string = "".join(traceback_format)
        error_log_path = Path(self.filepath) / "tool_error.trace"
        with open(error_log_path, "w", encoding="utf-8") as f:
            f.write(f"{QDateTime.currentDateTime().toString('yyyy-MM-ddTHH:mm:ss')}")
            f.write("\n" + traceback_string + "\n")
        self.show_warning(traceback_string)
