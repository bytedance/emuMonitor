# -*- coding: utf-8 -*-

import os
import re
import sys
import stat
import getpass
from datetime import datetime, timedelta

# Import PyQt
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, qApp, QTabWidget, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QMessageBox, QComboBox, QHeaderView, QDateEdit, QAbstractItemView
from PyQt5.QtCore import Qt, QDate

# Import matplotlib
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# Import common file
sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/common')
import common_pyqt5
import common_zebu

# Import config file
sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config')
import config

os.environ['PYTHONUNBUFFERED'] = '1'

# ZMONITOR VERSION
VERSION = "v0.4"


# Solve some unexpected warning message.
if 'XDG_RUNTIME_DIR' not in os.environ:
    user = getpass.getuser()
    os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-' + str(user)

    if not os.path.exists(os.environ['XDG_RUNTIME_DIR']):
        os.makedirs(os.environ['XDG_RUNTIME_DIR'])

    os.chmod(os.environ['XDG_RUNTIME_DIR'], stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)


# Init FigureCanvas
class FigureCanvas(FigureCanvasQTAgg):
    """
    Generate a new figure canvas.
    """
    def __init__(self):
        self.figure = Figure()
        super().__init__(self.figure)


# Generate GUI MainWindow
class MainWindow(QMainWindow):
    """
    Main window.
    """
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        """
        Main process, draw the main graphic frame.
        """
        # Add menubar.
        self.gen_menubar()

        # Define main Tab widget
        self.main_tab = QTabWidget(self)
        self.setCentralWidget(self.main_tab)

        # Define sub-tabs
        self.current_tab = QWidget()
        self.history_tab = QWidget()
        self.utilization_tab = QWidget()

        # Add the sub-tabs into main Tab widget
        self.main_tab.addTab(self.current_tab, 'CURRENT')
        self.main_tab.addTab(self.history_tab, 'HISTORY')
        self.main_tab.addTab(self.utilization_tab, 'UTILIZATION')

        # Generate the sub-tabs
        self.gen_current_tab()
        self.gen_history_tab()
        self.gen_utilization_tab()

        # Show main window
        self.setWindowTitle('zebuMonitor')
        self.resize(1100, 700)
        common_pyqt5.center_window(self)

    def gen_menubar(self):
        """
        Generate menubar.
        """
        menubar = self.menuBar()

        # File
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(qApp.quit)

        file_menu = menubar.addMenu('File')
        file_menu.addAction(exit_action)

        # Help
        version_action = QAction('Version', self)
        version_action.triggered.connect(self.show_version)

        about_action = QAction('About ZebuMonitor', self)
        about_action.triggered.connect(self.show_about)

        help_menu = menubar.addMenu('Help')
        help_menu.addAction(version_action)
        help_menu.addAction(about_action)

    def show_version(self):
        """
        Show zebuMonitor version information.
        """
        version = 'V1.0'
        QMessageBox.about(self, 'zebuMonitor', 'Version: ' + str(version) + '        ')

    def show_about(self):
        """
        Show zebuMonitor about information.
        """
        about_message = """
Thanks for downloading zebuMonitor.

zebuMonitor is an open source software for zebu information data-collection, data-analysis and data-display."""

        QMessageBox.about(self, 'zebuMonitor', about_message)

    # For current TAB (start) #
    def gen_current_tab(self):
        """
        Generate the CURRENT tab on zebuMonitor GUI, show current zebu usage informations.
        """
        # self.current_tab
        self.current_tab_frame = QFrame(self.current_tab)
        self.current_tab_frame.setFrameShadow(QFrame.Raised)
        self.current_tab_frame.setFrameShape(QFrame.Box)

        self.current_tab_table = QTableWidget(self.current_tab)

        # self.current_tab - Grid
        current_tab_grid = QGridLayout()

        current_tab_grid.addWidget(self.current_tab_frame, 0, 0)
        current_tab_grid.addWidget(self.current_tab_table, 1, 0)

        current_tab_grid.setRowStretch(0, 1)
        current_tab_grid.setRowStretch(1, 20)

        self.current_tab.setLayout(current_tab_grid)

        # Generate sub-frame
        self.gen_current_tab_frame()
        self.gen_current_tab_table()

    def gen_current_tab_frame(self):
        """
        Generate self.current_tab_frame.
        """
        # self.current_tab_frame
        current_tab_unit_label = QLabel('Unit', self.current_tab_frame)
        current_tab_unit_label.setStyleSheet("font-weight: bold;")
        current_tab_unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_unit_combo = QComboBox(self.current_tab_frame)
        self.current_tab_unit_combo.activated.connect(self.filter_current_tab_table)

        current_tab_module_label = QLabel('Module', self.current_tab_frame)
        current_tab_module_label.setStyleSheet("font-weight: bold;")
        current_tab_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_module_combo = QComboBox(self.current_tab_frame)
        self.current_tab_module_combo.activated.connect(self.filter_current_tab_table)

        current_tab_sub_module_label = QLabel('Sub Module', self.current_tab_frame)
        current_tab_sub_module_label.setStyleSheet("font-weight: bold;")
        current_tab_sub_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_sub_module_combo = QComboBox(self.current_tab_frame)
        self.current_tab_sub_module_combo.activated.connect(self.filter_current_tab_table)

        current_tab_status_label = QLabel('Status', self.current_tab_frame)
        current_tab_status_label.setStyleSheet("font-weight: bold;")
        current_tab_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_status_combo = QComboBox(self.current_tab_frame)
        self.current_tab_status_combo.activated.connect(self.filter_current_tab_table)

        current_tab_user_label = QLabel('User', self.current_tab_frame)
        current_tab_user_label.setStyleSheet("font-weight: bold;")
        current_tab_user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_user_combo = QComboBox(self.current_tab_frame)
        self.current_tab_user_combo.activated.connect(self.filter_current_tab_table)

        current_tab_host_label = QLabel('Host', self.current_tab_frame)
        current_tab_host_label.setStyleSheet("font-weight: bold;")
        current_tab_host_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_host_combo = QComboBox(self.current_tab_frame)
        self.current_tab_host_combo.activated.connect(self.filter_current_tab_table)

        current_tab_pid_label = QLabel('Pid', self.current_tab_frame)
        current_tab_pid_label.setStyleSheet("font-weight: bold;")
        current_tab_pid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_pid_combo = QComboBox(self.current_tab_frame)
        self.current_tab_pid_combo.activated.connect(self.filter_current_tab_table)

        current_tab_suspend_label = QLabel('Suspend', self.current_tab_frame)
        current_tab_suspend_label.setStyleSheet("font-weight: bold;")
        current_tab_suspend_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_suspend_combo = QComboBox(self.current_tab_frame)
        self.current_tab_suspend_combo.activated.connect(self.filter_current_tab_table)

        current_tab_refresh_button = QPushButton('Refresh', self.current_tab_frame)
        current_tab_refresh_button.setStyleSheet("font-weight: bold;")
        current_tab_refresh_button.clicked.connect(self.gen_current_tab_table)
        current_tab_refresh_button.setFixedSize(2*current_tab_refresh_button.sizeHint().width(), 2*current_tab_refresh_button.sizeHint().height())

        # self.current_tab_frame - Grid
        current_tab_frame_grid = QGridLayout()

        current_tab_frame_grid.addWidget(current_tab_unit_label, 0, 0)
        current_tab_frame_grid.addWidget(self.current_tab_unit_combo, 0, 1)
        current_tab_frame_grid.addWidget(current_tab_module_label, 0, 2)
        current_tab_frame_grid.addWidget(self.current_tab_module_combo, 0, 3)
        current_tab_frame_grid.addWidget(current_tab_sub_module_label, 0, 4)
        current_tab_frame_grid.addWidget(self.current_tab_sub_module_combo, 0, 5)
        current_tab_frame_grid.addWidget(current_tab_status_label, 0, 6)
        current_tab_frame_grid.addWidget(self.current_tab_status_combo, 0, 7)
        current_tab_frame_grid.addWidget(current_tab_refresh_button, 0, 9, 2, 2)

        current_tab_frame_grid.addWidget(current_tab_user_label, 1, 0)
        current_tab_frame_grid.addWidget(self.current_tab_user_combo, 1, 1)
        current_tab_frame_grid.addWidget(current_tab_host_label, 1, 2)
        current_tab_frame_grid.addWidget(self.current_tab_host_combo, 1, 3)
        current_tab_frame_grid.addWidget(current_tab_pid_label, 1, 4)
        current_tab_frame_grid.addWidget(self.current_tab_pid_combo, 1, 5)
        current_tab_frame_grid.addWidget(current_tab_suspend_label, 1, 6)
        current_tab_frame_grid.addWidget(self.current_tab_suspend_combo, 1, 7)

        current_tab_frame_grid.setColumnStretch(0, 3)
        current_tab_frame_grid.setColumnStretch(1, 3)
        current_tab_frame_grid.setColumnStretch(2, 3)
        current_tab_frame_grid.setColumnStretch(3, 3)
        current_tab_frame_grid.setColumnStretch(4, 3)
        current_tab_frame_grid.setColumnStretch(5, 3)
        current_tab_frame_grid.setColumnStretch(6, 3)
        current_tab_frame_grid.setColumnStretch(7, 3)
        current_tab_frame_grid.setColumnStretch(8, 1)
        current_tab_frame_grid.setColumnStretch(9, 3)

        self.current_tab_frame.setLayout(current_tab_frame_grid)

    def update_current_tab_combo(self):
        """
        Update self.current_tab with new optional setting.
        """
        # Clear all combo
        self.current_tab_unit_combo.clear()
        self.current_tab_module_combo.clear()
        self.current_tab_sub_module_combo.clear()
        self.current_tab_status_combo.clear()
        self.current_tab_user_combo.clear()
        self.current_tab_host_combo.clear()
        self.current_tab_pid_combo.clear()
        self.current_tab_suspend_combo.clear()

        # Set combo Items
        self.current_tab_unit_combo.addItems(['ALL'] + self.current_zebu_dic['unit_list'])
        self.current_tab_module_combo.addItems(['ALL'] + self.current_zebu_dic['module_list'])
        self.current_tab_sub_module_combo.addItems(['ALL'] + self.current_zebu_dic['sub_module_list'])
        self.current_tab_status_combo.addItems(['ALL'] + self.current_zebu_dic['status_list'])
        self.current_tab_user_combo.addItems(['ALL'] + self.current_zebu_dic['user_list'])
        self.current_tab_host_combo.addItems(['ALL'] + self.current_zebu_dic['host_list'])
        self.current_tab_pid_combo.addItems(['ALL'] + self.current_zebu_dic['pid_list'])
        self.current_tab_suspend_combo.addItems(['ALL'] + self.current_zebu_dic['suspend_list'])

    def gen_current_tab_table(self):
        """
        Generate self.current_tab_table.
        """
        # Get information
        self.check_current_zebu_info()
        self.update_current_tab_combo()

        # current tab table appearance
        self.current_tab_table.setShowGrid(True)
        self.current_tab_table.setSortingEnabled(True)
        self.current_tab_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.current_tab_table.setColumnCount(8)
        self.current_tab_table.setHorizontalHeaderLabels(['Unit', 'Module', 'Sub Module', 'Status', 'User', 'Host', 'PID', 'Suspend'])
        self.current_tab_table.setColumnWidth(0, 100)
        self.current_tab_table.setColumnWidth(1, 100)
        self.current_tab_table.setColumnWidth(2, 100)
        self.current_tab_table.setColumnWidth(3, 120)
        self.current_tab_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.current_tab_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.current_tab_table.setColumnWidth(6, 120)
        self.current_tab_table.setColumnWidth(7, 120)

        # Init current tab table
        self.update_current_tab_table(self.current_zebu_dic)

    def filter_current_tab_table(self):
        """
        Filter self.current_tab_table with unit/module/sub_module/status/user/host/pid/suspend.
        """
        # Read combobox to get specified filter criteria
        unit = self.current_tab_unit_combo.currentText().strip()
        module = self.current_tab_module_combo.currentText().strip()
        sub_module = self.current_tab_sub_module_combo.currentText().strip()
        status = self.current_tab_status_combo.currentText().strip()
        user = self.current_tab_user_combo.currentText().strip()
        host = self.current_tab_host_combo.currentText().strip()
        pid = self.current_tab_pid_combo.currentText().strip()
        suspend = self.current_tab_suspend_combo.currentText().strip()

        # Get filtered information
        filtered_zebu_dic = common_zebu.filter_zebu_dic(self.current_zebu_dic, specified_unit=unit, specified_module=module, specified_sub_module=sub_module, specified_status=status, specified_user=user, specified_host=host, specified_pid=pid, specified_suspend=suspend)

        # Update current tab table
        self.update_current_tab_table(filtered_zebu_dic)

    def update_current_tab_table(self, zebu_dic):
        """
        Update self.current_tab_table with specified zebu_dic information.
        """
        self.current_tab_table.setRowCount(0)

        # Fill current tab table
        self.current_tab_table.setRowCount(zebu_dic['row'])

        row = 0

        for unit in zebu_dic['info']:
            for module in zebu_dic['info'][unit]:
                for sub_module in zebu_dic['info'][unit][module]:
                    self.current_tab_table.setItem(row, 0, QTableWidgetItem(unit))
                    self.current_tab_table.setItem(row, 1, QTableWidgetItem(module))
                    self.current_tab_table.setItem(row, 2, QTableWidgetItem(sub_module))
                    self.current_tab_table.setItem(row, 3, QTableWidgetItem(zebu_dic['info'][unit][module][sub_module]['status']))
                    self.current_tab_table.setItem(row, 4, QTableWidgetItem(zebu_dic['info'][unit][module][sub_module]['user']))
                    self.current_tab_table.setItem(row, 5, QTableWidgetItem(zebu_dic['info'][unit][module][sub_module]['host']))
                    self.current_tab_table.setItem(row, 6, QTableWidgetItem(zebu_dic['info'][unit][module][sub_module]['pid']))
                    self.current_tab_table.setItem(row, 7, QTableWidgetItem(zebu_dic['info'][unit][module][sub_module]['suspend']))
                    row += 1

    def check_current_zebu_info(self):
        """
        Generate self.current_zebu_dic
        """
        current_zebu_info = []

        if os.path.exists(config.zRscManager) and os.path.exists(config.ZEBU_SYSTEM_DIR):
            stdout = os.popen(config.check_status_command).read()

            for line in stdout.split('\n'):
                current_zebu_info.append(line.strip())

            self.current_zebu_dic = common_zebu.parse_current_zebu_info(current_zebu_info)

    def gen_history_tab(self):
        """
        Generate the HISTORY tab on zebuMonitor GUI, show zebu history usage.
        """
        self.history_tab_frame = QFrame(self.history_tab)
        self.history_tab_frame.setFrameShadow(QFrame.Raised)
        self.history_tab_frame.setFrameShape(QFrame.Box)

        self.history_tab_table = QTableWidget(self.history_tab)

        # self.history_tab - Grid
        history_tab_grid = QGridLayout()

        history_tab_grid.addWidget(self.history_tab_frame, 0, 0)
        history_tab_grid.addWidget(self.history_tab_table, 1, 0)

        history_tab_grid.setRowStretch(0, 1)
        history_tab_grid.setRowStretch(1, 20)

        self.history_tab.setLayout(history_tab_grid)

        # Generate sub-frame
        self.gen_history_tab_frame()
        self.gen_history_tab_table()

    def gen_history_tab_frame(self):
        """
        Generate self.history_tab_frame
        """
        history_tab_unit_label = QLabel('Unit', self.history_tab_frame)
        history_tab_unit_label.setStyleSheet("font-weight: bold;")
        history_tab_unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_unit_combo = QComboBox(self.history_tab_frame)
        self.history_tab_unit_combo.activated.connect(self.update_history_tab_table)

        history_tab_module_label = QLabel('Module', self.history_tab_frame)
        history_tab_module_label.setStyleSheet("font-weight: bold;")
        history_tab_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_module_combo = QComboBox(self.history_tab_frame)
        self.history_tab_module_combo.activated.connect(self.update_history_tab_table)

        history_tab_sub_module_label = QLabel('Sub Module', self.history_tab_frame)
        history_tab_sub_module_label.setStyleSheet("font-weight: bold;")
        history_tab_sub_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_sub_module_combo = QComboBox(self.history_tab_frame)
        self.history_tab_sub_module_combo.activated.connect(self.update_history_tab_table)

        history_tab_start_date_label = QLabel('Start Date', self.history_tab_frame)
        history_tab_start_date_label.setStyleSheet("font-weight: bold;")
        history_tab_start_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_start_date_edit = QDateEdit(self.history_tab_frame)
        self.history_tab_start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.history_tab_start_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.history_tab_start_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.history_tab_start_date_edit.setCalendarPopup(True)
        self.history_tab_start_date_edit.setDate(QDate.currentDate().addDays(-1))
        self.history_tab_start_date_edit.dateChanged.connect(self.update_history_tab_table)

        history_tab_end_date_label = QLabel('End Date', self.history_tab_frame)
        history_tab_end_date_label.setStyleSheet("font-weight: bold;")
        history_tab_end_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_end_date_edit = QDateEdit(self.history_tab_frame)
        self.history_tab_end_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.history_tab_end_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.history_tab_end_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.history_tab_end_date_edit.setCalendarPopup(True)
        self.history_tab_end_date_edit.setDate(QDate.currentDate())
        self.history_tab_end_date_edit.dateChanged.connect(self.update_history_tab_table)

        history_tab_user_label = QLabel('User', self.history_tab_frame)
        history_tab_user_label.setStyleSheet("font-weight: bold;")
        history_tab_user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_user_combo = QComboBox(self.history_tab_frame)
        self.history_tab_user_combo.activated.connect(self.update_history_tab_table)

        history_tab_host_label = QLabel('Host', self.history_tab_frame)
        history_tab_host_label.setStyleSheet("font-weight: bold;")
        history_tab_host_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_host_combo = QComboBox(self.history_tab_frame)
        self.history_tab_host_combo.activated.connect(self.update_history_tab_table)

        history_tab_pid_label = QLabel('Pid', self.history_tab_frame)
        history_tab_pid_label.setStyleSheet("font-weight: bold;")
        history_tab_pid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_pid_combo = QComboBox(self.history_tab_frame)
        self.history_tab_pid_combo.activated.connect(self.update_history_tab_table)

        history_tab_refresh_button = QPushButton('Refresh', self.history_tab_frame)
        history_tab_refresh_button.setStyleSheet("font-weight: bold;")
        history_tab_refresh_button.clicked.connect(self.refresh_history_tab_combo)
        history_tab_refresh_button.setFixedSize(2*history_tab_refresh_button.sizeHint().width(), 2*history_tab_refresh_button.sizeHint().height())

        # self.history_tab_frame - Grid
        history_tab_frame_grid = QGridLayout()

        history_tab_frame_grid.addWidget(history_tab_unit_label, 0, 0)
        history_tab_frame_grid.addWidget(self.history_tab_unit_combo, 0, 1)
        history_tab_frame_grid.addWidget(history_tab_module_label, 0, 2)
        history_tab_frame_grid.addWidget(self.history_tab_module_combo, 0, 3)
        history_tab_frame_grid.addWidget(history_tab_sub_module_label, 0, 4)
        history_tab_frame_grid.addWidget(self.history_tab_sub_module_combo, 0, 5)
        history_tab_frame_grid.addWidget(history_tab_start_date_label, 0, 6)
        history_tab_frame_grid.addWidget(self.history_tab_start_date_edit, 0, 7)
        history_tab_frame_grid.addWidget(history_tab_refresh_button, 0, 9, 2, 1)
        history_tab_frame_grid.addWidget(history_tab_user_label, 1, 0)
        history_tab_frame_grid.addWidget(self.history_tab_user_combo, 1, 1)
        history_tab_frame_grid.addWidget(history_tab_host_label, 1, 2)
        history_tab_frame_grid.addWidget(self.history_tab_host_combo, 1, 3)
        history_tab_frame_grid.addWidget(history_tab_pid_label, 1, 4)
        history_tab_frame_grid.addWidget(self.history_tab_pid_combo, 1, 5)
        history_tab_frame_grid.addWidget(history_tab_end_date_label, 1, 6)
        history_tab_frame_grid.addWidget(self.history_tab_end_date_edit, 1, 7)

        history_tab_frame_grid.setColumnStretch(0, 3)
        history_tab_frame_grid.setColumnStretch(1, 3)
        history_tab_frame_grid.setColumnStretch(2, 3)
        history_tab_frame_grid.setColumnStretch(3, 3)
        history_tab_frame_grid.setColumnStretch(4, 3)
        history_tab_frame_grid.setColumnStretch(5, 3)
        history_tab_frame_grid.setColumnStretch(6, 3)
        history_tab_frame_grid.setColumnStretch(7, 3)
        history_tab_frame_grid.setColumnStretch(8, 1)
        history_tab_frame_grid.setColumnStretch(9, 3)

        self.history_tab_frame.setLayout(history_tab_frame_grid)
        self.init_history_tab_combo()

    def init_history_tab_combo(self):
        """
        Initialization self.history_tab.
        """
        # Set history tab combobox value
        self.history_tab_unit_combo.addItems(['ALL'] + self.current_zebu_dic['unit_list'])
        self.history_tab_module_combo.addItems(['ALL'] + self.current_zebu_dic['module_list'])
        self.history_tab_sub_module_combo.addItems(['ALL'] + self.current_zebu_dic['sub_module_list'])

        self.history_tab_user_combo.addItems(['ALL'])
        self.history_tab_host_combo.addItems(['ALL'])
        self.history_tab_pid_combo.addItems(['ALL'])

    def gen_history_tab_table(self):
        """
        Generate self.history_tab_table.
        """
        # History tab table appearance
        self.history_tab_table.setShowGrid(True)
        self.history_tab_table.setSortingEnabled(True)
        self.history_tab_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_tab_table.setColumnCount(8)
        self.history_tab_table.setHorizontalHeaderLabels(['Unit', 'Module', 'Sub Module', 'User', 'Host', 'PID', 'Start Time', 'End Time'])
        self.history_tab_table.setColumnWidth(0, 100)
        self.history_tab_table.setColumnWidth(1, 100)
        self.history_tab_table.setColumnWidth(2, 100)
        self.history_tab_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.history_tab_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.history_tab_table.setColumnWidth(5, 100)
        self.history_tab_table.setColumnWidth(6, 180)
        self.history_tab_table.setColumnWidth(7, 180)

        # Init current tab table
        self.update_history_tab_table()

    def update_history_tab_table(self):
        """
        Update self.history_tab_table.
        """
        # Read History combobox
        unit = self.history_tab_unit_combo.currentText().strip()
        module = self.history_tab_module_combo.currentText().strip()
        sub_module = self.history_tab_sub_module_combo.currentText().strip()
        start_date = self.history_tab_start_date_edit.date().toString(Qt.ISODate)
        end_date = self.history_tab_end_date_edit.date().toString(Qt.ISODate)
        user = self.history_tab_user_combo.currentText().strip()
        host = self.history_tab_host_combo.currentText().strip()
        pid = self.history_tab_pid_combo.currentText().strip()

        if datetime.strptime(end_date, "%Y-%m-%d") >= datetime.strptime(start_date, "%Y-%m-%d"):
            check_report_command = re.sub('FROMDATE', start_date, config.check_report_command)
            check_report_command = re.sub('TODATE', end_date, check_report_command)
            sys_report_lines = os.popen(check_report_command).read().split('\n')
            history_zebu_dic = common_zebu.parse_history_zebu_info(sys_report_lines, specified_unit=unit, specified_module=module, specified_sub_module=sub_module, specified_user=user, specified_host=host, specified_pid=pid)

            # Update history combobox according to search result
            self.update_history_tab_combo(history_zebu_dic, user, host, pid)
            self.history_tab_table.setRowCount(history_zebu_dic['rows'])

            row = 0

            for pid in history_zebu_dic['info']:
                for modules in history_zebu_dic['info'][pid]['modules']:
                    unit, module, sub_module = modules.split('.')
                    self.history_tab_table.setItem(row, 0, QTableWidgetItem(unit))
                    self.history_tab_table.setItem(row, 1, QTableWidgetItem(module))
                    self.history_tab_table.setItem(row, 2, QTableWidgetItem(sub_module))
                    self.history_tab_table.setItem(row, 3, QTableWidgetItem(history_zebu_dic['info'][pid]['user']))
                    self.history_tab_table.setItem(row, 4, QTableWidgetItem(history_zebu_dic['info'][pid]['host']))
                    self.history_tab_table.setItem(row, 5, QTableWidgetItem(pid))
                    self.history_tab_table.setItem(row, 6, QTableWidgetItem(history_zebu_dic['info'][pid]['start_time']))
                    self.history_tab_table.setItem(row, 7, QTableWidgetItem(history_zebu_dic['info'][pid]['end_time']))

                    row += 1

    def update_history_tab_combo(self, zebu_dic, user, host, pid):
        """
        Update user/host/pid information on self.history_tab with specified information.
        """
        # Update combobox value according to zebu_dic
        self.history_tab_user_combo.clear()
        self.history_tab_host_combo.clear()
        self.history_tab_pid_combo.clear()

        if user not in zebu_dic['user_list'] and user != 'ALL':
            zebu_dic['user_list'].append(user)

        if host not in zebu_dic['host_list'] and host != 'ALL':
            zebu_dic['host_list'].append(host)

        if pid not in zebu_dic['pid_list'] and pid != 'ALL':
            zebu_dic['pid_list'].append(pid)

        self.history_tab_user_combo.addItems(['ALL'] + zebu_dic['user_list'])
        self.history_tab_host_combo.addItems(['ALL'] + zebu_dic['host_list'])
        self.history_tab_pid_combo.addItems(['ALL'] + zebu_dic['pid_list'])

        self.history_tab_user_combo.setCurrentText(user)
        self.history_tab_host_combo.setCurrentText(host)
        self.history_tab_pid_combo.setCurrentText(pid)

    def refresh_history_tab_combo(self):
        """
        Revert combo currentText to "ALL" on self.history_tab.
        """
        # Reset history_tab_combo
        self.history_tab_unit_combo.setCurrentText('ALL')
        self.history_tab_module_combo.setCurrentText('ALL')
        self.history_tab_sub_module_combo.setCurrentText('ALL')

        self.history_tab_user_combo.setCurrentText('ALL')
        self.history_tab_host_combo.setCurrentText('ALL')
        self.history_tab_pid_combo.setCurrentText('ALL')

        self.update_history_tab_table()

    def gen_utilization_tab(self):
        """
        Generate the UTILIZATION tab on zebuMonitor GUI, show zebu utilization informations.
        """
        # self.utilization_tab
        self.utilization_tab_frame0 = QFrame(self.utilization_tab)
        self.utilization_tab_frame0.setFrameShadow(QFrame.Raised)
        self.utilization_tab_frame0.setFrameShape(QFrame.Box)

        self.utilization_tab_frame1 = QFrame(self.utilization_tab)
        self.utilization_tab_frame1.setFrameShadow(QFrame.Raised)
        self.utilization_tab_frame1.setFrameShape(QFrame.Box)

        # self.utilization_tab - Grid
        utilization_tab_grid = QGridLayout()

        utilization_tab_grid.addWidget(self.utilization_tab_frame0, 0, 0)
        utilization_tab_grid.addWidget(self.utilization_tab_frame1, 1, 0)

        utilization_tab_grid.setRowStretch(0, 1)
        utilization_tab_grid.setRowStretch(1, 20)

        self.utilization_tab.setLayout(utilization_tab_grid)

        # Generate sub-frame
        self.gen_utilization_tab_frame0()
        self.gen_utilization_tab_frame1()

    def gen_utilization_tab_frame0(self):
        """
        Generate self.utilization_tab_frame0, which contains filter items.
        """
        utilization_tab_unit_label = QLabel('Unit', self.utilization_tab_frame0)
        utilization_tab_unit_label.setStyleSheet("font-weight: bold;")
        utilization_tab_unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_unit_combo = QComboBox(self.utilization_tab_frame0)
        self.utilization_tab_unit_combo.activated.connect(self.utilization_tab_unit_combo_activated)
        self.utilization_tab_unit_combo.activated.connect(self.update_utilization_tab_frame1)

        utilization_tab_module_label = QLabel('Module', self.utilization_tab_frame0)
        utilization_tab_module_label.setStyleSheet("font-weight: bold;")
        utilization_tab_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_module_combo = QComboBox(self.utilization_tab_frame0)
        self.utilization_tab_module_combo.activated.connect(self.utilization_tab_module_combo_activated)
        self.utilization_tab_module_combo.activated.connect(self.update_utilization_tab_frame1)

        utilization_tab_sub_module_label = QLabel('Sub Module', self.utilization_tab_frame0)
        utilization_tab_sub_module_label.setStyleSheet("font-weight: bold;")
        utilization_tab_sub_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_sub_module_combo = QComboBox(self.utilization_tab_frame0)
        self.utilization_tab_sub_module_combo.activated.connect(self.utilization_tab_sub_module_combo_activated)
        self.utilization_tab_sub_module_combo.activated.connect(self.update_utilization_tab_frame1)

        utilization_tab_start_date_label = QLabel('Start Date', self.utilization_tab_frame0)
        utilization_tab_start_date_label.setStyleSheet("font-weight: bold;")
        utilization_tab_start_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_start_date_edit = QDateEdit(self.utilization_tab_frame0)
        self.utilization_tab_start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.utilization_tab_start_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.utilization_tab_start_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.utilization_tab_start_date_edit.setCalendarPopup(True)
        self.utilization_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.utilization_tab_start_date_edit.dateChanged.connect(self.update_utilization_tab_frame1)

        utilization_tab_end_date_label = QLabel('End Date', self.utilization_tab_frame0)
        utilization_tab_end_date_label.setStyleSheet("font-weight: bold;")
        utilization_tab_end_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_end_date_edit = QDateEdit(self.utilization_tab_frame0)
        self.utilization_tab_end_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.utilization_tab_end_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.utilization_tab_end_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.utilization_tab_end_date_edit.setCalendarPopup(True)
        self.utilization_tab_end_date_edit.setDate(QDate.currentDate())
        self.utilization_tab_end_date_edit.dateChanged.connect(self.update_utilization_tab_frame1)

        # self.utilization_tab_frame0 - Grid
        utilization_tab_frame0_grid = QGridLayout()

        utilization_tab_frame0_grid.addWidget(utilization_tab_unit_label, 0, 0)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_unit_combo, 0, 1)
        utilization_tab_frame0_grid.addWidget(utilization_tab_module_label, 0, 2)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_module_combo, 0, 3)
        utilization_tab_frame0_grid.addWidget(utilization_tab_sub_module_label, 0, 4)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_sub_module_combo, 0, 5)

        utilization_tab_frame0_grid.addWidget(utilization_tab_start_date_label, 0, 6)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_start_date_edit, 0, 7)
        utilization_tab_frame0_grid.addWidget(utilization_tab_end_date_label, 0, 8)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_end_date_edit, 0, 9)

        utilization_tab_frame0_grid.setColumnStretch(0, 1)
        utilization_tab_frame0_grid.setColumnStretch(1, 1)
        utilization_tab_frame0_grid.setColumnStretch(2, 1)
        utilization_tab_frame0_grid.setColumnStretch(3, 1)
        utilization_tab_frame0_grid.setColumnStretch(4, 1)
        utilization_tab_frame0_grid.setColumnStretch(5, 1)
        utilization_tab_frame0_grid.setColumnStretch(6, 1)
        utilization_tab_frame0_grid.setColumnStretch(7, 1)
        utilization_tab_frame0_grid.setColumnStretch(8, 1)
        utilization_tab_frame0_grid.setColumnStretch(9, 1)

        self.utilization_tab_frame0.setLayout(utilization_tab_frame0_grid)
        self.init_utilization_tab_combo()

    def init_utilization_tab_combo(self):
        """
        Initialization self.utilization_tab combo settings.
        """
        self.utilization_tab_unit_combo.addItems(['ALL'] + self.current_zebu_dic['unit_list'])
        self.utilization_tab_module_combo.addItems(['ALL'] + self.current_zebu_dic['module_list'])
        self.utilization_tab_sub_module_combo.addItems(['ALL'] + self.current_zebu_dic['sub_module_list'])

    def utilization_tab_unit_combo_activated(self):
        """
        If self.utilization_tab_unit_combo current value is "ALL", set self.utilization_tab_module_combo and self.utilization_tab_sub_module_combo to "ALL".
        """
        if self.utilization_tab_unit_combo.currentText() == 'ALL':
            self.utilization_tab_module_combo.setCurrentText('ALL')
            self.utilization_tab_sub_module_combo.setCurrentText('ALL')

    def utilization_tab_module_combo_activated(self):
        if self.utilization_tab_module_combo.currentText() != 'ALL':
            if self.utilization_tab_unit_combo.currentText() == 'ALL':
                self.utilization_tab_unit_combo.setCurrentIndex(1)
        else:
            self.utilization_tab_sub_module_combo.setCurrentText('ALL')

    def utilization_tab_sub_module_combo_activated(self):
        if self.utilization_tab_sub_module_combo.currentText() != 'ALL':
            if self.utilization_tab_unit_combo.currentText() == 'ALL' or self.utilization_tab_module_combo.currentText() == 'ALL':
                self.utilization_tab_unit_combo.setCurrentIndex(1)
                self.utilization_tab_module_combo.setCurrentIndex(1)

    def gen_utilization_tab_frame1(self):
        """
        Generate empty self.utilization_tab_frame1.
        """
        # self.utilization_tab_frame1
        self.utilization_figure_canvas = FigureCanvas()
        self.utilization_navigation_toolbar = NavigationToolbar2QT(self.utilization_figure_canvas, self)

        # self.utilization_tab_frame1 - Grid
        utilization_tab_frame1_grid = QGridLayout()
        utilization_tab_frame1_grid.addWidget(self.utilization_navigation_toolbar, 0, 0)
        utilization_tab_frame1_grid.addWidget(self.utilization_figure_canvas, 1, 0)
        self.utilization_tab_frame1.setLayout(utilization_tab_frame1_grid)

        self.update_utilization_tab_frame1()

    def update_utilization_tab_frame1(self):
        # Read combo to get module information
        unit = self.utilization_tab_unit_combo.currentText()
        module = self.utilization_tab_module_combo.currentText()
        sub_module = self.utilization_tab_sub_module_combo.currentText()

        # Get start/end date
        start_date = self.utilization_tab_start_date_edit.date().toString(Qt.ISODate)
        end_date = self.utilization_tab_end_date_edit.date().toString(Qt.ISODate)

        if unit and module and sub_module and start_date and end_date and start_date <= end_date:
            # Get utilization dic
            utilization_dic = self.get_utilization_info(unit, module, sub_module, start_date, end_date)
            date_list = []
            utilization_list = []

            # Get date_list and utilization_list
            for (date, utilization) in utilization_dic.items():
                date_list.append(date)
                utilization_list.append(utilization * 100)

            # Draw utilization curve
            if date_list and utilization_list:
                fig = self.utilization_figure_canvas.figure
                fig.clear()
                self.utilization_figure_canvas.draw()

                for i in range(len(date_list)):
                    date_list[i] = datetime.strptime(date_list[i], "%Y-%m-%d")

                av_utilization = int(sum(utilization_list) / len(utilization_list))

                self.draw_utilization_curve(fig, av_utilization, date_list, utilization_list)

    def get_utilization_info(self, unit, module, sub_module, start_date, end_date):
        utilization_info_dic = {}
        filtered_zebu_dic = common_zebu.filter_zebu_dic(self.current_zebu_dic, specified_unit=unit, specified_module=module, specified_sub_module=sub_module)
        module_count = int(filtered_zebu_dic['row'])
        check_report_command = re.sub('FROMDATE', start_date, config.check_report_command)
        check_report_command = re.sub('TODATE', end_date, check_report_command)

        # Run zRscManager to get utilization information
        sys_report_lines = os.popen(check_report_command).read().split('\n')

        start_date_utc = datetime.strptime(start_date + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_date_utc = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

        # Generate utilization_info_dic
        for day in range((end_date_utc.date() - start_date_utc.date()).days + 1):
            key_date = (start_date_utc + timedelta(days=day)).strftime("%Y-%m-%d")
            utilization_info_dic.setdefault(key_date, 0)

        # Read sys_report lines
        for line in sys_report_lines:
            if line:
                # Split line in to useful information
                start_time, end_time, modules, user, pid, pc = line.split(',')
                modules_list = modules.strip('()').split(' ')

                for modules in modules_list:
                    # If this line has specified module
                    if modules.strip() in filtered_zebu_dic['module_name']:
                        # If job begins before user specified start_date
                        if start_time == '' or datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S") < datetime.strptime(start_date, "%Y-%m-%d"):
                            start_time = start_date + ' 00:00:00'

                        # If job still running and doesn't have end time
                        if end_time == '':
                            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # If job ends after user specified end_date
                        if datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S") > end_date_utc:
                            end_time = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")

                        # Transfer time into utc format
                        start_time_utc = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                        end_time_utc = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

                        # If job begins and ends in the same day
                        if start_time_utc.date() == end_time_utc.date():
                            time_delta = (end_time_utc - start_time_utc).total_seconds() / 86400
                            module_count = self.get_module_count(start_time_utc.date().strftime("%Y-%m-%d"), unit, module, sub_module)
                            utilization_info_dic[start_time_utc.date().strftime("%Y-%m-%d")] += time_delta / module_count
                        # If job begins and ends in different day
                        else:
                            start_run_date = datetime.strftime(start_time_utc.date(), "%Y-%m-%d")
                            end_run_date = datetime.strftime(end_time_utc.date(), "%Y-%m-%d")

                            for day in range((end_time_utc.date() - start_time_utc.date()).days + 1):
                                run_date = start_time_utc.date() + timedelta(days=day)

                                if run_date == start_time_utc.date():
                                    time_delta = ((datetime.strptime(start_run_date + " 23:59:59", "%Y-%m-%d %H:%M:%S") - start_time_utc).total_seconds() + 1) / 86400
                                elif run_date == end_time_utc.date():
                                    time_delta = (end_time_utc - datetime.strptime(end_run_date + " 00:00:00", "%Y-%m-%d %H:%M:%S")).total_seconds() / 86400
                                else:
                                    time_delta = 1.0

                                module_count = self.get_module_count(datetime.strftime(run_date, "%Y-%m-%d"), unit, module, sub_module)
                                utilization_info_dic[datetime.strftime(run_date, "%Y-%m-%d")] += time_delta / module_count

        return utilization_info_dic

    def get_module_count(self, date, unit, module, sub_module):
        """
        Read and get module count
        """
        module_count = 0

        for modules in self.current_zebu_dic['module_info_list']:
            if re.search(unit, modules) or unit == 'ALL':
                if re.search(module, modules) or module == 'ALL':
                    if re.search(sub_module, modules) or sub_module == 'ALL':
                        module_count += 1

        return module_count

    def draw_utilization_curve(self, fig, av_utilization, date_list, utilization_list):
        """
        Draw "date - utilization" curve on self.utilization_tab_frame1.
        """
        fig.subplots_adjust(bottom=0.25)
        axes = fig.add_subplot(111)
        axes.set_title('Average Utilization : ' + str(av_utilization) + '%')
        axes.set_xlabel('Sample Date')
        axes.set_ylabel('Utilization (%)')
        axes.plot(date_list, utilization_list, 'go-')
        axes.tick_params(axis='x', rotation=15)
        axes.grid()
        self.utilization_figure_canvas.draw()


#################
# Main Function #
#################
def main():
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
