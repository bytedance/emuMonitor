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
