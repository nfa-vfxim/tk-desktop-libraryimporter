# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialog.ui'
#
# Created: Wed Aug 11 19:44:33 2021
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(418, 313)
        self.verticalLayout_2 = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        spacerItem = QtGui.QSpacerItem(40, 10, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.verticalLayout_2.addItem(spacerItem)
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.gridLayout_8 = QtGui.QGridLayout()
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.directoryLabel = QtGui.QLabel(Dialog)
        self.directoryLabel.setObjectName("directoryLabel")
        self.gridLayout_8.addWidget(self.directoryLabel, 0, 0, 1, 1)
        self.directoryPath = QtGui.QLineEdit(Dialog)
        self.directoryPath.setText("")
        self.directoryPath.setObjectName("directoryPath")
        self.gridLayout_8.addWidget(self.directoryPath, 0, 1, 1, 1)
        self.browseDirectory = QtGui.QPushButton(Dialog)
        self.browseDirectory.setObjectName("browseDirectory")
        self.gridLayout_8.addWidget(self.browseDirectory, 0, 2, 1, 1)
        self.verticalLayout_2.addLayout(self.gridLayout_8)
        self.overwriteExisting = QtGui.QCheckBox(Dialog)
        self.overwriteExisting.setObjectName("overwriteExisting")
        self.verticalLayout_2.addWidget(self.overwriteExisting)
        self.importSubfolders = QtGui.QCheckBox(Dialog)
        self.importSubfolders.setObjectName("importSubfolders")
        self.verticalLayout_2.addWidget(self.importSubfolders)
        self.gridLayout_9 = QtGui.QGridLayout()
        self.gridLayout_9.setObjectName("gridLayout_9")
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_9.addItem(spacerItem1, 1, 0, 1, 1)
        self.console = QtGui.QTextEdit(Dialog)
        self.console.setReadOnly(True)
        self.console.setObjectName("console")
        self.gridLayout_9.addWidget(self.console, 2, 0, 1, 1)
        self.executeButton = QtGui.QPushButton(Dialog)
        self.executeButton.setObjectName("executeButton")
        self.gridLayout_9.addWidget(self.executeButton, 0, 0, 1, 1)
        self.verticalLayout_2.addLayout(self.gridLayout_9)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "The Current Sgtk Environment", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Fill in the directory to import into the library. Once clicked \"Import Library\", the import process will start.", None, QtGui.QApplication.UnicodeUTF8))
        self.directoryLabel.setText(QtGui.QApplication.translate("Dialog", "Directory path", None, QtGui.QApplication.UnicodeUTF8))
        self.browseDirectory.setText(QtGui.QApplication.translate("Dialog", "Browse...", None, QtGui.QApplication.UnicodeUTF8))
        self.overwriteExisting.setText(QtGui.QApplication.translate("Dialog", "Overwrite existing versions", None, QtGui.QApplication.UnicodeUTF8))
        self.importSubfolders.setText(QtGui.QApplication.translate("Dialog", "Select subfolders (to import the complete library)", None, QtGui.QApplication.UnicodeUTF8))
        self.executeButton.setText(QtGui.QApplication.translate("Dialog", "Import Library", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
