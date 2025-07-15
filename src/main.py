import sys, os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QGridLayout, QVBoxLayout,
    QCheckBox, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import steg
import unsteg


class ImageLabel(QLabel):
    def __init__(self, text):
        super().__init__()

        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText('\n\n ' + text + ' \n\n')
        self.path = None
        self.setStyleSheet('''
            QLabel{
                border: 4px dashed #aaa
            }
        ''')

    def dragEnterEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasImage:
            event.setDropAction(Qt.DropAction.CopyAction)
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.path = file_path
            self.setPixmap(QPixmap(file_path).scaled(
                self.width(), self.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

            event.accept()
        else:
            event.ignore()

    def setPixmap(self, image):
        super().setPixmap(image)

class AppDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(1280, 1024)
        self.setWindowTitle("Steganography")

        mainLayout = QGridLayout()
        
        mainLayout.setRowStretch(0, 3)
        mainLayout.setRowStretch(1, 0)
        mainLayout.setRowStretch(2, 1)

        self.inputImg = ImageLabel("Drop the image you want to hide here")
        self.targetImg = ImageLabel("Drop the cover image here")
        self.saveFlag = QCheckBox("Save the original image into the result")
        self.saveFlag.setChecked(True)
        self.stegButton = QPushButton(text="Hide", parent=self)
        self.unstegButton = QPushButton(text="Retrieve", parent=self)

        mainLayout.addWidget(self.inputImg, 0, 0)
        mainLayout.addWidget(self.targetImg, 0, 1)
        mainLayout.addWidget(self.saveFlag, 1, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        mainLayout.addWidget(self.stegButton, 2, 0)
        mainLayout.addWidget(self.unstegButton, 2, 1)
        self.stegButton.clicked.connect(self.hide)
        self.unstegButton.clicked.connect(self.retrieve)

        self.stegButton.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)
        self.unstegButton.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)

        self.setLayout(mainLayout)

    def hide(self):
        if self.inputImg.path == None or self.targetImg.path == None:
            dlg = QMessageBox.critical(
                self,
                "Alert",
                "You did not upload the images!"
            )
        else:
            if self.saveFlag.isChecked():
                steg.init_params(self.inputImg.path, self.targetImg.path, 1)
            else:
                steg.init_params(self.inputImg.path, self.targetImg.path, 0)
            output_path = steg.return_output_path(self.targetImg.path)
            steg.resize_input_image()
            steg.stegano_image(self.targetImg.path, output_path)
        
            dlg = QMessageBox.information(
                self,
                "Info",
                "Done!"
            )
            

    def retrieve(self):
        if self.targetImg.path == None:
            dlg = QMessageBox.critical(
                self,
                "Alert",
                "You did not upload the cover image!"
            )
        else:
            if self.saveFlag.isChecked():
                unsteg.init_params(None, self.targetImg.path)
            else:
                unsteg.init_params(self.inputImg.path, self.targetImg.path)
            unsteg.unstegano_image(self.targetImg.path)

            dlg = QMessageBox.information(
                self,
                "Info",
                "Done!"
            )

app = QApplication(sys.argv)
demo = AppDemo()
demo.show()
sys.exit(app.exec())