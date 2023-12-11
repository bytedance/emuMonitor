import datetime
import re
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from matplotlib.dates import num2date
from PyQt5.QtWidgets import QDesktopWidget, QComboBox, QLineEdit, QListWidget, QCheckBox, QListWidgetItem
from PyQt5.QtGui import QTextCursor


def center_window(window):
    """
    Move the input GUI window into the center of the computer windows.
    """
    qr = window.frameGeometry()
    cp = QDesktopWidget().availableGeometry().center()
    qr.moveCenter(cp)
    window.move(qr.topLeft())


def text_edit_visible_position(text_edit_item, position='End'):
    """
    For QTextEdit widget, show the 'Start' or 'End' part of the text.
    """
    cursor = text_edit_item.textCursor()

    if position == 'Start':
        cursor.movePosition(QTextCursor.Start)
    elif position == 'End':
        cursor.movePosition(QTextCursor.End)

    text_edit_item.setTextCursor(cursor)
    text_edit_item.ensureCursorVisible()


class QComboCheckBox(QComboBox):
    """
    QComboCheckBox is a QComboBox with checkbox.
    """
    def __init__(self, parent):
        super(QComboCheckBox, self).__init__(parent)

        # self.qLineWidget is used to load QCheckBox items.
        self.qListWidget = QListWidget()
        self.setModel(self.qListWidget.model())
        self.setView(self.qListWidget)

        # self.qLineEdit is used to show selected items on QLineEdit.
        self.qLineEdit = QLineEdit()
        self.qLineEdit.setReadOnly(True)
        self.setLineEdit(self.qLineEdit)

        # self.checkBoxList is used to save QCheckBox items.
        self.checkBoxList = []

    def addCheckBoxItem(self, text):
        """
        Add QCheckBox format item into QListWidget(QComboCheckBox).
        """
        qItem = QListWidgetItem(self.qListWidget)
        qBox = QCheckBox(text)
        qBox.stateChanged.connect(self.updateLineEdit)
        self.checkBoxList.append(qBox)
        self.qListWidget.setItemWidget(qItem, qBox)

    def addCheckBoxItems(self, text_list):
        """
        Add multi QCheckBox format items.
        """
        for text in text_list:
            self.addCheckBoxItem(text)

    def updateLineEdit(self):
        """
        Update QComboCheckBox show message with self.qLineEdit.
        """
        selectedItemString = ' '.join(self.selectedItems().values())
        self.qLineEdit.setReadOnly(False)
        self.qLineEdit.clear()
        self.qLineEdit.setText(selectedItemString)
        self.qLineEdit.setReadOnly(True)

    def selectedItems(self):
        """
        Get all selected items (location and value).
        """
        selectedItemDic = {}

        for (i, qBox) in enumerate(self.checkBoxList):
            if qBox.isChecked() is True:
                selectedItemDic.setdefault(i, qBox.text())

        return selectedItemDic

    def selectAllItems(self):
        """
        Select all items.
        """
        for (i, qBox) in enumerate(self.checkBoxList):
            if qBox.isChecked() is False:
                self.checkBoxList[i].setChecked(True)

    def unselectAllItems(self):
        """
        Unselect all items.
        """
        for (i, qBox) in enumerate(self.checkBoxList):
            if qBox.isChecked() is True:
                self.checkBoxList[i].setChecked(False)

    def clear(self):
        """
        Clear all items.
        """
        super().clear()
        self.checkBoxList = []


class FigureCanvasQTAgg(FigureCanvasQTAgg):
    """
    Generate a new figure canvas.
    """
    def __init__(self):
        self.figure = Figure()
        self.axes = None
        super().__init__(self.figure)


class NavigationToolbar2QT(NavigationToolbar2QT):
    """
    Enhancement for NavigationToolbar2QT, can get and show label value.
    """
    def __init__(self, canvas, parent, coordinates=True, x_is_date=True):
        super().__init__(canvas, parent, coordinates)
        self.x_is_date = x_is_date

    @staticmethod
    def bisection(event_xdata, xdata_list):
        xdata = None
        index = None
        lower = 0
        upper = len(xdata_list) - 1
        bisection_index = (upper - lower) // 2

        if xdata_list:
            if event_xdata > xdata_list[upper]:
                xdata = xdata_list[upper]
                index = upper
            elif (event_xdata < xdata_list[lower]) or (len(xdata_list) <= 2):
                xdata = xdata_list[lower]
                index = lower
            elif event_xdata in xdata_list:
                xdata = event_xdata
                index = xdata_list.index(event_xdata)

            while xdata is None:
                if upper - lower == 1:
                    if event_xdata - xdata_list[lower] <= xdata_list[upper] - event_xdata:
                        xdata = xdata_list[lower]
                        index = lower
                    else:
                        xdata = xdata_list[upper]
                        index = upper

                    break

                if event_xdata > xdata_list[bisection_index]:
                    lower = bisection_index
                elif event_xdata < xdata_list[bisection_index]:
                    upper = bisection_index

                bisection_index = (upper - lower) // 2 + lower

        return (xdata, index)

    def _mouse_event_to_message(self, event):
        if event.inaxes and event.inaxes.get_navigate():
            try:
                if self.x_is_date:
                    event_xdata = num2date(event.xdata).strftime('%Y,%m,%d,%H,%M,%S')
                else:
                    event_xdata = event.xdata
            except (ValueError, OverflowError):
                pass
            else:
                if self.x_is_date and (len(event_xdata.split(',')) == 6):
                    (year, month, day, hour, minute, second) = event_xdata.split(',')
                    event_xdata = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))

                xdata_list = list(self.canvas.figure.gca().get_lines()[0].get_xdata())
                (xdata, index) = self.bisection(event_xdata, sorted(xdata_list))

                if xdata is not None:
                    info_list = []

                    for line in self.canvas.figure.gca().get_lines():
                        label = line.get_label()
                        ydata_string = line.get_ydata()
                        ydata_list = list(ydata_string)
                        ydata = ydata_list[index]

                        info_list.append('%s=%s' % (label, round(ydata, 0)))

                    info_string = '  '.join(info_list)

                    if self.x_is_date:
                        xdata_string = xdata.strftime('%Y-%m-%d %H:%M:%S')
                        xdata_string = re.sub(r' 00:00:00', '', xdata_string)
                        info_string = '[%s]\n%s' % (xdata_string, info_string)

                    return info_string
        return ''
