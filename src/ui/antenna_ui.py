# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Antenna.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_Antenna(object):
    def setupUi(self, Antenna):
        if not Antenna.objectName():
            Antenna.setObjectName(u"Antenna")
        Antenna.setWindowModality(Qt.WindowModality.ApplicationModal)
        Antenna.resize(259, 116)
        self.verticalLayout_2 = QVBoxLayout(Antenna)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.frame = QFrame(Antenna)
        self.frame.setObjectName(u"frame")
        self.frame.setStyleSheet(u"* {\n"
"	background-color: rgb(240, 240, 240);\n"
"	font-family:\"\u5fae\u8f6f\u96c5\u9ed1\";\n"
"	font-size:12px;\n"
"}\n"
"\n"
"QPushButton{\n"
"	height: 22px;\n"
"	width: 60px;\n"
"	border: 1px solid silver;\n"
"	border-radius: 3px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"	background-color: rgba(180, 180, 180, 80);\n"
"}\n"
"\n"
"#lineEdit_coordinate_name {\n"
"	border: 1px solid silver;\n"
"	border-radius: 3px;\n"
"}")
        self.frame.setFrameShape(QFrame.Shape.Box)
        self.frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.verticalLayout = QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.label)

        self.edit_name = QLineEdit(self.frame)
        self.edit_name.setObjectName(u"edit_name")

        self.verticalLayout.addWidget(self.edit_name)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label_2)

        self.btn_ok = QPushButton(self.frame)
        self.btn_ok.setObjectName(u"btn_ok")
        self.btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.horizontalLayout.addWidget(self.btn_ok, 0, Qt.AlignmentFlag.AlignRight)

        self.btn_cancel = QPushButton(self.frame)
        self.btn_cancel.setObjectName(u"btn_cancel")
        self.btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.horizontalLayout.addWidget(self.btn_cancel, 0, Qt.AlignmentFlag.AlignRight)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.verticalLayout_2.addWidget(self.frame)


        self.retranslateUi(Antenna)
        self.btn_cancel.clicked.connect(Antenna.close)

        QMetaObject.connectSlotsByName(Antenna)
    # setupUi

    def retranslateUi(self, Antenna):
        Antenna.setWindowTitle(QCoreApplication.translate("Antenna", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("Antenna", u"\u5750\u6807\u540d\u79f0\uff1a", None))
        self.label_2.setText("")
        self.btn_ok.setText(QCoreApplication.translate("Antenna", u"OK", None))
        self.btn_cancel.setText(QCoreApplication.translate("Antenna", u"Cancel", None))
    # retranslateUi

