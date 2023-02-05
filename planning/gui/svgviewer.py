# -*- coding: utf-8 -*-
"""SVG Viewer widget"""

# pylint: disable=no-name-in-module
# pylint: disable=no-member

import os
import os.path as osp

from qtpy.QtCore import QSize, Qt, QUrl
from qtpy.QtGui import QPixmap
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy.QtWidgets import QLabel


class OldSVGViewer(QLabel):
    """SVG Viewer widget based on QLabel"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.__cached_pixmap = None
        self.__filename = None

    def update_scale(self, size):
        """Update scale"""
        if self.__cached_pixmap is not None:
            self.setPixmap(
                self.__cached_pixmap.scaled(
                    size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

    def load(self, fname):
        """Load from filename"""
        self.__filename = fname
        self.__cached_pixmap = QPixmap(fname)
        self.update_scale(self.size())

    def clear(self):
        """Clear widget"""
        self.__filename = None
        self.__cached_pixmap = None
        super().clear()

    def sizeHint(self):  # pylint: disable=C0103
        """Reimplement Qt method"""
        if self.__cached_pixmap:
            return self.__cached_pixmap.size()
        return QSize(1, 1)

    def resizeEvent(self, event):  # pylint: disable=C0103
        """Reimplement Qt method"""
        self.update_scale(event.size())
        return super().resizeEvent(event)

    def mouseDoubleClickEvent(self, event):  # pylint: disable=C0103
        """Reimplement Qt method"""
        if self.__filename is not None:
            os.startfile(osp.dirname(self.__filename))
        return super().mouseDoubleClickEvent(event)


class SVGViewer(QWebEngineView):
    """SVG Viewer widget based on QWebEngineView"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setZoomFactor(0.8)
        self.__filename = None

    def load(self, fname):
        """Load from filename"""
        self.__filename = fname
        super().load(QUrl(fname.replace("\\", "/")))

    def clear(self):
        """Clear widget"""
        self.__filename = None
        super().clear()

    def mouseDoubleClickEvent(self, event):  # pylint: disable=C0103
        """Reimplement Qt method"""
        if self.__filename is not None:
            os.startfile(osp.dirname(self.__filename))
        return super().mouseDoubleClickEvent(event)
