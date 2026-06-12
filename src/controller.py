from datetime import datetime
import json
import sys
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QDesktopServices

from src import HANDLE_ITEM, HandleItem, Point
from src.handler.position import PositionUIProcessor
from src.handler.pps import PPSUIProcessor
from src.ui.antenna import AntennaUI
from src.util.const import LocalPath
from src.util.msg import Message
from src.view import MainView


class MainController(QObject):
    def __init__(self):
        super().__init__()

        self.view: MainView = MainView()
        self.position: PositionUIProcessor = PositionUIProcessor()
        self.pps: PPSUIProcessor = PPSUIProcessor()

        self.antenna_ui = AntennaUI(self.view.box_antenna)
        self.antenna_ui.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.setup_connections()

        self._hook = sys.excepthook
        sys.excepthook = self.view.catch_exceptions

        self.view.init_coordinates()

        self.action: int = HANDLE_ITEM
        self.init_ui()

    def init_ui(self):
        self.view.box_fix.setEnabled(False)
        if self.action == HandleItem.EXTERNAL:
            self.view.box_mode.setCurrentIndex(1)
            self.view.box_mode.setEnabled(False)
            self.view.frame_static.setHidden(True)
            self.view.frame_pps.setHidden(True)
            self.view.combo_type.setEnabled(False)

    def setup_connections(self):
        self.view.btn_open.clicked.connect(self.view.open_folder)
        self.view.btn_start.clicked.connect(self.start_program)
        self.view.btn_add.clicked.connect(self.show_antenna_ui)
        self.view.btn_check_json.clicked.connect(self.check_json_file)

        self.antenna_ui.btn_ok.clicked.connect(self.antenna_ui.add_antenna)

        self.pps.log_signal.connect(self.view.log_signal_call)
        self.pps.end_signal.connect(self.view.end_signal_call)
        self.position.log_signal.connect(self.view.log_signal_call)
        self.position.end_signal.connect(self.view.end_signal_call)

    def start_pps_program(self, check_list):
        self.pps.processor.filepath = self.view.filepath
        self.pps.processor.check_list = check_list
        self.pps.processor.edge_type = 1 if self.view.radio_raise.isChecked() else 0
        self.pps.start()

    def start_program(self):
        check_list = self.view.get_file_list()
        if not check_list:
            return

        is_moving = self.view.box_mode.currentIndex() == 1

        if self.view.combo_type.currentIndex() == 1:
            self.view.set_element_enable(False)
            self.start_pps_program(check_list)
            return

        if is_moving:
            if not self.view.edit_ref.text().strip():
                self.view.show_warning(Message.MSG_POINT_INVALID)
                return
        else:
            try:
                lat = float(self.view.edit_lat.text().strip())
                lng = float(self.view.edit_lng.text().strip())
                hgt = float(self.view.edit_hgt.text().strip())
            except ValueError:
                self.view.show_warning(Message.MSG_COORDINATE_TYPE_ERROR)
                return

        point = self.view.edit_ref.text() if is_moving else Point(lat, lng, hgt)
        self.view.set_element_enable(False)

        self.position.processor.filepath = self.view.filepath
        self.position.processor.std_mode = self.view.box_std.isChecked()
        self.position.processor.fix_mode = self.view.box_fix.currentIndex()
        self.position.processor.check_list = check_list
        self.position.processor.prefix_list = [
            # e.upper().encode() for e in Variable.json_settings.get("prefix_list")
        ]
        self.position.processor.is_ttff = False
        self.position.processor.is_moving = is_moving
        self.position.processor.point = point
        self.position.processor.error_list = [
            # e.upper().encode() for e in Variable.json_settings.get("error_list")
        ]
        self.position.processor.utc_date = None
        self.position.processor.action = self.action

        # 是否分割统计场景，分割信息从REPORT-UTC.json获取
        if self.view.check_split.isChecked():
            scenes = self.gen_scenes()
            if not scenes:
                self.view.end_signal_call()
                return

            self.position.processor.scenes = scenes

        self.position.start()

    def gen_scenes(self):
        scenes = []
        try:
            report_json = json.load(
                open(LocalPath.REPORT_JSON, "r", encoding="utf-8", errors="ignore")
            )
        except json.JSONDecodeError:
            self.view.show_warning(Message.MSG_REPORT_JSON_INVALID)
            return scenes
        except FileNotFoundError:
            self.view.show_warning(Message.MSG_REPORT_JSON_NOT_FOUND)
            return scenes

        date = report_json.get("Date", None)
        if not date:
            self.view.show_warning(Message.MSG_DATE_EMPTY)
            return scenes

        try:
            datetime.strptime(date, "%Y%m%d")
        except ValueError:
            self.view.show_warning(Message.MSG_DATE_INVALID)
            return scenes

        times = report_json.get("Time", [])
        if not times:
            self.view.show_warning(Message.MSG_TIME_EMPTY)
            return scenes

        for t in times:
            try:
                scenes.append(
                    {
                        "id": t["Scene"],
                        "name": t["Scene"],
                        "begin_time": datetime.strptime(
                            f"{date} {t['BeginTime']}", "%Y%m%d %H%M%S"
                        ).strftime("%Y-%m-%dT%H:%M:%S"),
                        "end_time": datetime.strptime(
                            f"{date} {t['EndTime']}", "%Y%m%d %H%M%S"
                        ).strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                )
            except ValueError:
                self.view.show_warning(
                    f"{Message.MSG_TIME_INVALID}: {t['Scene']}/{t['BeginTime']}/{t['EndTime']}"
                )
                return []

        return scenes

    def show_antenna_ui(self):
        try:
            lat = float(self.view.edit_lat.text().strip())
            lng = float(self.view.edit_lng.text().strip())

            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise OverflowError

            self.antenna_ui.args = (
                lat,
                lng,
                float(self.view.edit_hgt.text().strip()),
            )
            self.antenna_ui.combox = self.view.box_antenna
            self.antenna_ui.show()
        except ValueError:
            self.view.show_warning(Message.MSG_COORDINATE_TYPE_ERROR)
        except OverflowError:
            self.view.show_warning(Message.MSG_COORDINATE_RANGE_ERROR)

    def check_json_file(self):
        if LocalPath.REPORT_JSON.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(LocalPath.REPORT_JSON)))
        else:
            self.view.show_warning(Message.MSG_REPORT_JSON_NOT_FOUND)

    def show(self):
        self.view.show()
