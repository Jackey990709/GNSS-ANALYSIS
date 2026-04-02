# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Main.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QTextBrowser, QVBoxLayout,
    QWidget)
import res_rc

class Ui_MainView(object):
    def setupUi(self, MainView):
        if not MainView.objectName():
            MainView.setObjectName(u"MainView")
        MainView.setWindowModality(Qt.WindowModality.NonModal)
        MainView.resize(999, 604)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainView.sizePolicy().hasHeightForWidth())
        MainView.setSizePolicy(sizePolicy)
        MainView.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.actionSetting = QAction(MainView)
        self.actionSetting.setObjectName(u"actionSetting")
        self.actionAbout = QAction(MainView)
        self.actionAbout.setObjectName(u"actionAbout")
        self.centralWidget = QWidget(MainView)
        self.centralWidget.setObjectName(u"centralWidget")
        self.verticalLayout_4 = QVBoxLayout(self.centralWidget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.frame = QFrame(self.centralWidget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.frame)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.frame_2 = QFrame(self.frame)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_2)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.frame_5 = QFrame(self.frame_2)
        self.frame_5.setObjectName(u"frame_5")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_5.sizePolicy().hasHeightForWidth())
        self.frame_5.setSizePolicy(sizePolicy1)
        font = QFont()
        font.setFamilies([u"Calibri"])
        font.setPointSize(9)
        self.frame_5.setFont(font)
        self.frame_5.setStyleSheet(u"background-color: rgb(240, 240, 240);")
        self.frame_5.setFrameShape(QFrame.Shape.Box)
        self.frame_5.setFrameShadow(QFrame.Shadow.Sunken)
        self.frame_5.setLineWidth(1)
        self.verticalLayout_7 = QVBoxLayout(self.frame_5)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lineEditFolder = QLineEdit(self.frame_5)
        self.lineEditFolder.setObjectName(u"lineEditFolder")
        font1 = QFont()
        font1.setFamilies([u"Microsoft YaHei UI"])
        self.lineEditFolder.setFont(font1)
        self.lineEditFolder.setStyleSheet(u"#lineEditFolder {\n"
"	border-radius: 3px;\n"
"	border: 1px solid silver;\n"
"	height: 22px;\n"
"}")

        self.horizontalLayout.addWidget(self.lineEditFolder)

        self.btn_open = QPushButton(self.frame_5)
        self.btn_open.setObjectName(u"btn_open")
        font2 = QFont()
        font2.setFamilies([u"Microsoft YaHei UI"])
        font2.setPointSize(9)
        self.btn_open.setFont(font2)
        self.btn_open.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open.setStyleSheet(u"#pushButton_open_folder:hover{\n"
"	background-color: rgb(180, 180, 180);\n"
"}\n"
"\n"
"#pushButton_open_folder{\n"
"	border: 1px solid silver;\n"
"	border-radius: 3px;\n"
"	width: 80px;\n"
"	height: 22px;\n"
"}")

        self.horizontalLayout.addWidget(self.btn_open)


        self.verticalLayout_7.addLayout(self.horizontalLayout)

        self.widget_log_file = QListWidget(self.frame_5)
        self.widget_log_file.setObjectName(u"widget_log_file")
        self.widget_log_file.setEnabled(True)
        sizePolicy1.setHeightForWidth(self.widget_log_file.sizePolicy().hasHeightForWidth())
        self.widget_log_file.setSizePolicy(sizePolicy1)
        font3 = QFont()
        font3.setFamilies([u"Calibri"])
        font3.setPointSize(10)
        self.widget_log_file.setFont(font3)
        self.widget_log_file.setLineWidth(1)
        self.widget_log_file.setAutoScroll(True)
        self.widget_log_file.setAutoScrollMargin(16)
        self.widget_log_file.setSpacing(1)

        self.verticalLayout_7.addWidget(self.widget_log_file)


        self.verticalLayout_2.addWidget(self.frame_5)

        self.frame_6 = QFrame(self.frame_2)
        self.frame_6.setObjectName(u"frame_6")
        sizePolicy.setHeightForWidth(self.frame_6.sizePolicy().hasHeightForWidth())
        self.frame_6.setSizePolicy(sizePolicy)
        self.frame_6.setMinimumSize(QSize(0, 0))
        self.frame_6.setMaximumSize(QSize(16777215, 16777215))
        font4 = QFont()
        font4.setFamilies([u"Agency FB"])
        self.frame_6.setFont(font4)
        self.frame_6.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.frame_6.setStyleSheet(u"background-color: rgb(240, 240, 240);")
        self.frame_6.setFrameShape(QFrame.Shape.Box)
        self.frame_6.setFrameShadow(QFrame.Shadow.Sunken)
        self.frame_6.setLineWidth(1)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(6, 6, 6, 6)
        self.textBrowser_log = QTextBrowser(self.frame_6)
        self.textBrowser_log.setObjectName(u"textBrowser_log")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.textBrowser_log.sizePolicy().hasHeightForWidth())
        self.textBrowser_log.setSizePolicy(sizePolicy2)
        self.textBrowser_log.setFont(font3)
        self.textBrowser_log.viewport().setProperty(u"cursor", QCursor(Qt.CursorShape.ArrowCursor))
        self.textBrowser_log.setFrameShape(QFrame.Shape.StyledPanel)

        self.horizontalLayout_4.addWidget(self.textBrowser_log)


        self.verticalLayout_2.addWidget(self.frame_6)


        self.horizontalLayout_6.addWidget(self.frame_2)

        self.frame_3 = QFrame(self.frame)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(500, 16777215))
        font5 = QFont()
        font5.setFamilies([u"\u5fae\u8f6f\u96c5\u9ed1"])
        font5.setPointSize(14)
        font5.setBold(False)
        self.frame_3.setFont(font5)
        self.frame_3.setStyleSheet(u"QFrame {\n"
"	background-color: rgb(240, 240, 240);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"	selection-background-color: #1E90FF;\n"
"}\n"
"\n"
"")
        self.frame_3.setFrameShape(QFrame.Shape.Box)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame_3)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(3, -1, 3, -1)
        self.label_7 = QLabel(self.frame_3)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_13.addWidget(self.label_7, 0, Qt.AlignmentFlag.AlignLeft)

        self.box_mode = QComboBox(self.frame_3)
        self.box_mode.addItem("")
        self.box_mode.addItem("")
        self.box_mode.setObjectName(u"box_mode")
        self.box_mode.setStyleSheet(u"")

        self.horizontalLayout_13.addWidget(self.box_mode, 0, Qt.AlignmentFlag.AlignLeft)

        self.label_2 = QLabel(self.frame_3)
        self.label_2.setObjectName(u"label_2")
        sizePolicy2.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy2)

        self.horizontalLayout_13.addWidget(self.label_2)


        self.verticalLayout_5.addLayout(self.horizontalLayout_13)

        self.frame_static = QFrame(self.frame_3)
        self.frame_static.setObjectName(u"frame_static")
        self.frame_static.setFrameShape(QFrame.Shape.Box)
        self.frame_static.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout = QVBoxLayout(self.frame_static)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(3, -1, 3, -1)
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_ref = QLabel(self.frame_static)
        self.label_ref.setObjectName(u"label_ref")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.label_ref.sizePolicy().hasHeightForWidth())
        self.label_ref.setSizePolicy(sizePolicy3)

        self.horizontalLayout_7.addWidget(self.label_ref)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.box_antenna = QComboBox(self.frame_static)
        self.box_antenna.setObjectName(u"box_antenna")
        self.box_antenna.setMinimumSize(QSize(110, 0))

        self.horizontalLayout_2.addWidget(self.box_antenna)

        self.btn_add = QPushButton(self.frame_static)
        self.btn_add.setObjectName(u"btn_add")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.btn_add.sizePolicy().hasHeightForWidth())
        self.btn_add.setSizePolicy(sizePolicy4)
        self.btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add.setStyleSheet(u"#btn_add:hover{\n"
"	background-color: rgb(0, 0, 255);\n"
"}")

        self.horizontalLayout_2.addWidget(self.btn_add)

        self.btn_del = QPushButton(self.frame_static)
        self.btn_del.setObjectName(u"btn_del")
        self.btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_del.setStyleSheet(u"#btn_del:hover{\n"
"	background-color: rgb(234, 199, 152);\n"
"}")

        self.horizontalLayout_2.addWidget(self.btn_del)


        self.horizontalLayout_7.addLayout(self.horizontalLayout_2)

        self.box_std = QCheckBox(self.frame_static)
        self.box_std.setObjectName(u"box_std")

        self.horizontalLayout_7.addWidget(self.box_std)


        self.verticalLayout.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_3 = QLabel(self.frame_static)
        self.label_3.setObjectName(u"label_3")
        sizePolicy4.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy4)
        self.label_3.setMinimumSize(QSize(0, 0))
        self.label_3.setMaximumSize(QSize(16777215, 16777215))
        font6 = QFont()
        font6.setFamilies([u"\u5fae\u8f6f\u96c5\u9ed1"])
        self.label_3.setFont(font6)

        self.horizontalLayout_3.addWidget(self.label_3)

        self.edit_lat = QLineEdit(self.frame_static)
        self.edit_lat.setObjectName(u"edit_lat")

        self.horizontalLayout_3.addWidget(self.edit_lat)

        self.label_4 = QLabel(self.frame_static)
        self.label_4.setObjectName(u"label_4")
        sizePolicy4.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy4)
        self.label_4.setMinimumSize(QSize(0, 0))
        self.label_4.setMaximumSize(QSize(16777215, 16777215))
        self.label_4.setStyleSheet(u"")

        self.horizontalLayout_3.addWidget(self.label_4)

        self.edit_lng = QLineEdit(self.frame_static)
        self.edit_lng.setObjectName(u"edit_lng")

        self.horizontalLayout_3.addWidget(self.edit_lng)

        self.label_6 = QLabel(self.frame_static)
        self.label_6.setObjectName(u"label_6")
        sizePolicy4.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy4)
        self.label_6.setMinimumSize(QSize(0, 0))
        self.label_6.setMaximumSize(QSize(16777215, 16777215))

        self.horizontalLayout_3.addWidget(self.label_6)

        self.edit_hgt = QLineEdit(self.frame_static)
        self.edit_hgt.setObjectName(u"edit_hgt")

        self.horizontalLayout_3.addWidget(self.edit_hgt)


        self.verticalLayout.addLayout(self.horizontalLayout_3)


        self.verticalLayout_5.addWidget(self.frame_static)

        self.frame_dynamic = QFrame(self.frame_3)
        self.frame_dynamic.setObjectName(u"frame_dynamic")
        self.frame_dynamic.setFrameShape(QFrame.Shape.Box)
        self.frame_dynamic.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_dynamic)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(3, -1, 3, -1)
        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setSpacing(0)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_5 = QLabel(self.frame_dynamic)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_10.addWidget(self.label_5)

        self.edit_ref = QLineEdit(self.frame_dynamic)
        self.edit_ref.setObjectName(u"edit_ref")

        self.horizontalLayout_10.addWidget(self.edit_ref)

        self.btn_ref = QPushButton(self.frame_dynamic)
        self.btn_ref.setObjectName(u"btn_ref")
        self.btn_ref.setMinimumSize(QSize(30, 0))
        self.btn_ref.setMaximumSize(QSize(30, 16777215))

        self.horizontalLayout_10.addWidget(self.btn_ref)


        self.verticalLayout_3.addLayout(self.horizontalLayout_10)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.check_split = QCheckBox(self.frame_dynamic)
        self.check_split.setObjectName(u"check_split")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.check_split.sizePolicy().hasHeightForWidth())
        self.check_split.setSizePolicy(sizePolicy5)

        self.horizontalLayout_5.addWidget(self.check_split)

        self.btn_check_json = QPushButton(self.frame_dynamic)
        self.btn_check_json.setObjectName(u"btn_check_json")

        self.horizontalLayout_5.addWidget(self.btn_check_json, 0, Qt.AlignmentFlag.AlignLeft)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setSpacing(0)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.label_10 = QLabel(self.frame_dynamic)
        self.label_10.setObjectName(u"label_10")

        self.horizontalLayout_9.addWidget(self.label_10)

        self.label_8 = QLabel(self.frame_dynamic)
        self.label_8.setObjectName(u"label_8")
        sizePolicy3.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy3)
        self.label_8.setStyleSheet(u"")

        self.horizontalLayout_9.addWidget(self.label_8)

        self.box_fix = QComboBox(self.frame_dynamic)
        self.box_fix.addItem("")
        self.box_fix.addItem("")
        self.box_fix.setObjectName(u"box_fix")
        sizePolicy5.setHeightForWidth(self.box_fix.sizePolicy().hasHeightForWidth())
        self.box_fix.setSizePolicy(sizePolicy5)
        self.box_fix.setMinimumSize(QSize(66, 0))
        self.box_fix.setMaximumSize(QSize(66, 16777215))

        self.horizontalLayout_9.addWidget(self.box_fix)


        self.horizontalLayout_5.addLayout(self.horizontalLayout_9)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)


        self.verticalLayout_5.addWidget(self.frame_dynamic)

        self.label = QLabel(self.frame_3)
        self.label.setObjectName(u"label")
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.verticalLayout_5.addWidget(self.label)

        self.btn_start = QPushButton(self.frame_3)
        self.btn_start.setObjectName(u"btn_start")
        self.btn_start.setFont(font6)
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.setStyleSheet(u"")

        self.verticalLayout_5.addWidget(self.btn_start, 0, Qt.AlignmentFlag.AlignRight)


        self.horizontalLayout_6.addWidget(self.frame_3)


        self.verticalLayout_4.addWidget(self.frame)

        MainView.setCentralWidget(self.centralWidget)
        self.menuBar = QMenuBar(MainView)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 999, 33))
        self.menuFile = QMenu(self.menuBar)
        self.menuFile.setObjectName(u"menuFile")
        self.menu = QMenu(self.menuBar)
        self.menu.setObjectName(u"menu")
        MainView.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuBar.addAction(self.menu.menuAction())
        self.menuFile.addAction(self.actionSetting)
        self.menu.addAction(self.actionAbout)

        self.retranslateUi(MainView)

        QMetaObject.connectSlotsByName(MainView)
    # setupUi

    def retranslateUi(self, MainView):
        MainView.setWindowTitle(QCoreApplication.translate("MainView", u"MainWindow", None))
        self.actionSetting.setText(QCoreApplication.translate("MainView", u"\u8bbe\u7f6e", None))
        self.actionAbout.setText(QCoreApplication.translate("MainView", u"\u5173\u4e8e", None))
        self.btn_open.setText(QCoreApplication.translate("MainView", u"\u6253\u5f00\u76ee\u5f55", None))
        self.label_7.setText(QCoreApplication.translate("MainView", u"\u5904\u7406\u6a21\u5f0f\uff1a", None))
        self.box_mode.setItemText(0, QCoreApplication.translate("MainView", u"static", None))
        self.box_mode.setItemText(1, QCoreApplication.translate("MainView", u"dynamic", None))

        self.label_2.setText("")
        self.label_ref.setText(QCoreApplication.translate("MainView", u"\u53c2\u8003\u5750\u6807\uff1a", None))
        self.btn_add.setText(QCoreApplication.translate("MainView", u"\u6dfb\u52a0/\u4fee\u6539", None))
        self.btn_del.setText(QCoreApplication.translate("MainView", u"\u5220\u9664", None))
        self.box_std.setText(QCoreApplication.translate("MainView", u"\u53c2\u8003\u672a\u77e5", None))
        self.label_3.setText(QCoreApplication.translate("MainView", u"\u7eac\u5ea6\uff1a", None))
        self.label_4.setText(QCoreApplication.translate("MainView", u"\u7ecf\u5ea6\uff1a", None))
        self.label_6.setText(QCoreApplication.translate("MainView", u"\u9ad8\u5ea6\uff1a", None))
        self.label_5.setText(QCoreApplication.translate("MainView", u"\u53c2\u8003\u6587\u4ef6\uff1a", None))
        self.btn_ref.setText(QCoreApplication.translate("MainView", u"...", None))
        self.check_split.setText(QCoreApplication.translate("MainView", u"\u6309\u8def\u6bb5\u5206\u5272", None))
        self.btn_check_json.setText(QCoreApplication.translate("MainView", u"\u67e5\u770b\u914d\u7f6e", None))
        self.label_10.setText("")
        self.label_8.setText(QCoreApplication.translate("MainView", u"\u53c2\u8003\u5b9a\u4f4d\u7b26\uff1a", None))
        self.box_fix.setItemText(0, QCoreApplication.translate("MainView", u"All", None))
        self.box_fix.setItemText(1, QCoreApplication.translate("MainView", u"4", None))

        self.label.setText("")
        self.btn_start.setText(QCoreApplication.translate("MainView", u"\u5f00\u59cb", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainView", u"\u914d\u7f6e", None))
        self.menu.setTitle(QCoreApplication.translate("MainView", u"\u5e2e\u52a9", None))
    # retranslateUi

