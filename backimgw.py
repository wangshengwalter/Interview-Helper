# This Python file uses the following encoding: utf-8
from PySide2.QtWidgets import QWidget
from PySide2.QtGui import QPainter, QPixmap



class BackImgW(QWidget):
    imgname = None
    def __init__(self, parent=None):
        super(BackImgW,self).__init__(parent)

    def setbackimg(self, backimgname):
        self.imgname = backimgname

    def paintEvent(self, evt):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)


        widgetw = self.rect().width()
        widgeth = self.rect().height()


        backimg = QPixmap(self.imgname)
        imgw = backimg.width()
        imgh = backimg.height()

        wratio = float(widgetw/imgw)
        hratio = float(widgeth/imgh)


        if wratio < hratio:
            img_scaledW = imgw*hratio
            backimg = backimg.scaled(img_scaledW, self.rect().height())
        else:
            img_scaledH = imgh*wratio
            backimg = backimg.scaled(self.rect().width(), img_scaledH)

        painter.drawPixmap(0,0, backimg)
