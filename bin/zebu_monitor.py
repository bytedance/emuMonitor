# -*- coding: utf-8 -*-

import os
import re
import sys
import yaml
import stat
import getpass
import logging
from datetime import datetime, timedelta

# Import PyQt
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, qApp, QTabWidget, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QMessageBox, QComboBox, QHeaderView, QDateEdit, QAbstractItemView, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QDate

# Import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# Import common file
sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']))
from common import common_pyqt5, common_zebu, common
from config import config

os.environ['PYTHONUNBUFFERED'] = '1'
logger = common.get_logger(level=logging.WARNING)

# ZMONITOR VERSION
VERSION = "v1.1"


# Solve some unexpected warning message.
if 'XDG_RUNTIME_DIR' not in os.environ:
    user = getpass.getuser()
    os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-' + str(user)

    if not os.path.exists(os.environ['XDG_RUNTIME_DIR']):
        os.makedirs(os.environ['XDG_RUNTIME_DIR'])

    os.chmod(os.environ['XDG_RUNTIME_DIR'], stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)


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

        if hasattr(config, 'zebu_enable_cost_others_project'):
            self.enable_cost_others_project = config.zebu_enable_cost_others_project
        else:
            logger.error("Could not find the definition of zebu_enable_cost_others_project in config!")

        if hasattr(config, 'zebu_enable_use_default_cost_rate'):
            self.enable_use_default_cost_rate = config.zebu_enable_use_default_cost_rate
        else:
            logger.error("Could not find the definition of zebu_enable_use_default_cost_rate in config!")

        self.zebu_system_dir_dic = None

        if hasattr(config, 'zebu_system_dir_record'):
            if os.path.exists(config.zebu_system_dir_record):
                with open(config.zebu_system_dir_record, 'r') as zf:
                    self.zebu_system_dir_dic = yaml.load(zf, Loader=yaml.CLoader)

        if self.zebu_system_dir_dic is None:
            logger.error('Find zebu system directory failed. Please Check!')
            sys.exit(1)

        project_list_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/zebu/project_list'
        project_execute_host_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/zebu/project_execute_host'
        project_user_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/zebu/project_user_file'

        self.project_list, self.default_project_cost_dic = common.parse_project_list_file(project_list_file)

        if self.enable_cost_others_project:
            self.project_list.append('others')
            self.default_project_cost_dic['others'] = 0

        self.project_execute_host_dic = common.parse_project_proportion_file(project_execute_host_file)
        self.project_user_dic = common.parse_project_proportion_file(project_user_file)

        self.project_proportion_dic = {'execute_host': self.project_execute_host_dic, 'user': self.project_user_dic}

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
        self.cost_tab = QWidget()

        # Add the sub-tabs into main Tab widget
        self.main_tab.addTab(self.current_tab, 'CURRENT')
        self.main_tab.addTab(self.history_tab, 'HISTORY')
        self.main_tab.addTab(self.utilization_tab, 'UTILIZATION')
        self.main_tab.addTab(self.cost_tab, 'COST')

        # Generate the sub-tabs
        self.gen_current_tab()
        self.gen_history_tab()
        self.gen_utilization_tab()
        self.gen_cost_tab()

        # Show main window
        self.setWindowTitle('emuMonitor - Zebu')
        self.resize(1111, 620)
        self.setWindowIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/monitor.ico'))
        common_pyqt5.center_window(self)

    def gen_menubar(self):
        """
        Generate menubar.
        """
        menubar = self.menuBar()

        # File
        exit_action = QAction('Exit', self)
        exit_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/exit.png'))
        exit_action.triggered.connect(qApp.quit)

        export_current_table_action = QAction('Export current table', self)
        export_current_table_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/save.png'))
        export_current_table_action.triggered.connect(self.export_current_table)

        export_history_table_action = QAction('Export history table', self)
        export_history_table_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/save.png'))
        export_history_table_action.triggered.connect(self.export_history_table)

        export_cost_table_action = QAction('Export cost table', self)
        export_cost_table_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/save.png'))
        export_cost_table_action.triggered.connect(self.export_cost_table)

        file_menu = menubar.addMenu('File')
        file_menu.addAction(export_current_table_action)
        file_menu.addAction(export_history_table_action)
        file_menu.addAction(export_cost_table_action)
        file_menu.addAction(exit_action)

        # Setup
        enable_use_default_cost_rate_action = QAction('Enable Use Default Cost Rate', self, checkable=True)
        enable_use_default_cost_rate_action.setChecked(self.enable_use_default_cost_rate)
        enable_use_default_cost_rate_action.triggered.connect(self.func_enable_use_default_cost_rate)

        enable_cost_others_project_action = QAction('Enable Cost Others Project', self, checkable=True)
        enable_cost_others_project_action.setChecked(self.enable_cost_others_project)
        enable_cost_others_project_action.triggered.connect(self.func_enable_cost_others_project)

        setup_menu = menubar.addMenu('Setup')
        setup_menu.addAction(enable_use_default_cost_rate_action)
        setup_menu.addAction(enable_cost_others_project_action)

        # Help
        version_action = QAction('Version', self)
        version_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/version.png'))
        version_action.triggered.connect(self.show_version)

        about_action = QAction('About ZebuMonitor', self)
        about_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/about.png'))
        about_action.triggered.connect(self.show_about)

        help_menu = menubar.addMenu('Help')
        help_menu.addAction(version_action)
        help_menu.addAction(about_action)

    def show_version(self):
        """
        Show zebuMonitor version information.
        """
        version = 'V1.2'
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
        current_tab_refresh_button.setFixedSize(2 * current_tab_refresh_button.sizeHint().width(), 2 * current_tab_refresh_button.sizeHint().height())

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
        self.current_tab_table_title_list = ['Unit', 'Module', 'Sub Module', 'Status', 'User', 'Host', 'PID', 'Suspend']
        self.current_tab_table.setHorizontalHeaderLabels(self.current_tab_table_title_list)
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
        today = datetime.now()
        zebu_system_dir = ''

        for record_day in self.zebu_system_dir_dic:
            try:
                record_day_time = datetime.strptime(record_day, '%Y-%m-%d')
            except Exception as error:
                logger.error('Find Error {} in zebu_system_dir date setting, please check!'.format(str(error)))
                sys.exit(1)

            if today > record_day_time:
                zebu_system_dir = self.zebu_system_dir_dic[record_day]

        if not zebu_system_dir:
            zebu_system_dir = self.zebu_system_dir_dic[self.zebu_system_dir_dic.keys()[0]]

        var_dic = {'ZEBU_SYSTEM_DIR': zebu_system_dir}

        if os.path.exists(config.zRscManager) and os.path.exists(zebu_system_dir):
            check_status_command = config.check_status_command.format_map(var_dic)
            stdout = os.popen(check_status_command).read()

            for line in stdout.split('\n'):
                current_zebu_info.append(line.strip())

            self.current_zebu_dic, self.zebu_module_dic = common_zebu.parse_current_zebu_info(current_zebu_info)

        if os.path.isfile('ZEBU_GLOBAL_SYSTEM_DIR_global_mngt.db'):
            os.system('rm ZEBU_GLOBAL_SYSTEM_DIR_global_mngt.db')

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
        history_tab_refresh_button.setFixedSize(2 * history_tab_refresh_button.sizeHint().width(), 2 * history_tab_refresh_button.sizeHint().height())

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
        self.history_tab_table_title_list = ['Unit', 'Module', 'Sub Module', 'User', 'Host', 'PID', 'Start Time', 'End Time']
        self.history_tab_table.setHorizontalHeaderLabels(self.history_tab_table_title_list)
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

        end_date_time = datetime.strptime(end_date, "%Y-%m-%d")
        start_date_time = datetime.strptime(start_date, "%Y-%m-%d")
        zebu_system_dir_list = []

        if end_date_time >= start_date_time:
            for record_day in sorted(self.zebu_system_dir_dic.keys()):
                try:
                    record_day_time = datetime.strptime(record_day, '%Y-%m-%d')
                except Exception as error:
                    logger.error('Find Error {} in zebu_system_dir date setting, please check!'.format(str(error)))
                    sys.exit(1)

                if record_day_time < end_date_time:
                    zebu_system_dir_list.append(self.zebu_system_dir_dic[record_day])

        var_dic = {'FROMDATE': start_date_time.strftime('%Y/%m/%d'), 'TODATE': end_date_time.strftime('%Y/%m/%d')}

        for zebu_system_dir in zebu_system_dir_list:
            var_dic['ZEBU_SYSTEM_DIR'] = zebu_system_dir
            check_report_command = config.check_report_command.format_map(var_dic)
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
        self.utilization_navigation_toolbar = common_pyqt5.NavigationToolbar2QT(self.utilization_figure_canvas, self, x_is_date=True)

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

        start_date_time = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_time = datetime.strptime(end_date, '%Y-%m-%d')
        start_date_utc = datetime.strptime(start_date + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_date_utc = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

        # Generate utilization_info_dic
        for day in range((end_date_utc.date() - start_date_utc.date()).days + 1):
            key_date = (start_date_utc + timedelta(days=day)).strftime("%Y-%m-%d")
            utilization_info_dic.setdefault(key_date, 0)

        zebu_system_dir_list = []

        if end_date_time >= start_date_time:
            for record_day in sorted(self.zebu_system_dir_dic.keys()):
                try:
                    record_day_time = datetime.strptime(record_day, '%Y-%m-%d')
                except Exception as error:
                    logger.error('Find Error {} in zebu_system_dir date setting, please check!'.format(str(error)))
                    sys.exit(1)

                if record_day_time < end_date_time:
                    zebu_system_dir_list.append(self.zebu_system_dir_dic[record_day])

        var_dic = {'FROMDATE': (start_date_time - timedelta(days=90)).strftime('%Y/%m/%d'), 'TODATE': end_date_time.strftime('%Y/%m/%d')}

        for zebu_system_dir in zebu_system_dir_list:
            var_dic['ZEBU_SYSTEM_DIR'] = zebu_system_dir
            check_report_command = config.check_report_command.format_map(var_dic)

            # Run zRscManager to get utilization information
            sys_report_lines = os.popen(check_report_command).read().split('\n')

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

        utilization_info_dic = {udate: utilization if utilization <= 1 else 1 for udate, utilization in utilization_info_dic.items()}

        return utilization_info_dic

    def get_module_count(self, date, unit, module, sub_module):
        """
        Read self.zebu_module_dic and get module count
        """
        date_list = list(self.zebu_module_dic.keys())
        first_dila_date = date_list[0]
        last_dila_date = date_list[-1]
        first_dila_date_utc = datetime.strptime(first_dila_date, '%Y-%m-%d').date()
        last_dila_date_utc = datetime.strptime(last_dila_date, '%Y-%m-%d').date()
        check_date_utc = datetime.strptime(date, '%Y-%m-%d').date()
        module_list = []

        if check_date_utc < first_dila_date_utc:
            module_list = self.zebu_module_dic[first_dila_date]
        elif check_date_utc >= last_dila_date_utc:
            module_list = self.zebu_module_dic[last_dila_date]
        else:
            for i in range(len(date_list) - 1):
                start_date = date_list[i]
                end_date = date_list[i + 1]
                start_date_utc = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_utc = datetime.strptime(end_date, '%Y-%m-%d').date()
                if start_date_utc <= check_date_utc <= end_date_utc:
                    module_list = self.zebu_module_dic[start_date]

        module_count = 0

        for modules in module_list:
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
        axes.plot(date_list, utilization_list, 'go-', label='Utilization (%)', linewidth=0.1, markersize=0.1)
        axes.fill_between(date_list, utilization_list, color='green', alpha=0.5)
        axes.tick_params(axis='x', rotation=15)
        axes.grid()
        self.utilization_figure_canvas.draw()

    def gen_cost_tab(self):
        """
        Generate the COST tab on zebuMonitor GUI, show zebu cost informations.
        """
        # self.cost_tab
        self.cost_tab_frame = QFrame(self.cost_tab)
        self.cost_tab_frame.setFrameShadow(QFrame.Raised)
        self.cost_tab_frame.setFrameShape(QFrame.Box)

        self.cost_tab_table = QTableWidget(self.cost_tab)

        # self.utilization_tab - Grid
        cost_tab_grid = QGridLayout()

        cost_tab_grid.addWidget(self.cost_tab_frame, 0, 0)
        cost_tab_grid.addWidget(self.cost_tab_table, 1, 0)

        cost_tab_grid.setRowStretch(0, 1)
        cost_tab_grid.setRowStretch(1, 20)

        self.cost_tab.setLayout(cost_tab_grid)

        # Generate sub-frame
        self.gen_cost_tab_frame()
        self.gen_cost_tab_table()

    def gen_cost_tab_frame(self):
        """
        Generate self.cost_tab_frame, which contains filter items.
        """
        cost_tab_unit_label = QLabel('Unit', self.cost_tab_frame)
        cost_tab_unit_label.setStyleSheet("font-weight: bold;")
        cost_tab_unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_unit_combo = QComboBox(self.cost_tab_frame)
        self.cost_tab_unit_combo.activated.connect(self.cost_tab_unit_combo_activated)
        self.cost_tab_unit_combo.activated.connect(self.gen_cost_tab_table)

        cost_tab_module_label = QLabel('Module', self.cost_tab_frame)
        cost_tab_module_label.setStyleSheet("font-weight: bold;")
        cost_tab_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_module_combo = QComboBox(self.cost_tab_frame)
        self.cost_tab_module_combo.activated.connect(self.cost_tab_module_combo_activated)
        self.cost_tab_module_combo.activated.connect(self.gen_cost_tab_table)

        cost_tab_sub_module_label = QLabel('Sub Module', self.cost_tab_frame)
        cost_tab_sub_module_label.setStyleSheet("font-weight: bold;")
        cost_tab_sub_module_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_sub_module_combo = QComboBox(self.cost_tab_frame)
        self.cost_tab_sub_module_combo.activated.connect(self.cost_tab_sub_module_combo_activated)
        self.cost_tab_sub_module_combo.activated.connect(self.gen_cost_tab_table)

        cost_tab_start_date_label = QLabel('Start Date', self.cost_tab_frame)
        cost_tab_start_date_label.setStyleSheet("font-weight: bold;")
        cost_tab_start_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_start_date_edit = QDateEdit(self.cost_tab_frame)
        self.cost_tab_start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.cost_tab_start_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.cost_tab_start_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.cost_tab_start_date_edit.setCalendarPopup(True)
        self.cost_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.cost_tab_start_date_edit.dateChanged.connect(self.gen_cost_tab_table)

        cost_tab_end_date_label = QLabel('End Date', self.cost_tab_frame)
        cost_tab_end_date_label.setStyleSheet("font-weight: bold;")
        cost_tab_end_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_end_date_edit = QDateEdit(self.cost_tab_frame)
        self.cost_tab_end_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.cost_tab_end_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.cost_tab_end_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.cost_tab_end_date_edit.setCalendarPopup(True)
        self.cost_tab_end_date_edit.setDate(QDate.currentDate())
        self.utilization_tab_end_date_edit.dateChanged.connect(self.gen_cost_tab_table)

        cost_tab_export_button = QPushButton('Export', self.cost_tab_frame)
        cost_tab_export_button.setStyleSheet('''QPushButton:hover{background:rgb(170, 255, 127);}''')
        cost_tab_export_button.clicked.connect(self.export_cost_table)

        # self.cost_tab_frame0 - Grid
        cost_tab_frame_grid = QGridLayout()

        cost_tab_frame_grid.addWidget(cost_tab_unit_label, 0, 0)
        cost_tab_frame_grid.addWidget(self.cost_tab_unit_combo, 0, 1)
        cost_tab_frame_grid.addWidget(cost_tab_module_label, 0, 2)
        cost_tab_frame_grid.addWidget(self.cost_tab_module_combo, 0, 3)
        cost_tab_frame_grid.addWidget(cost_tab_sub_module_label, 0, 4)
        cost_tab_frame_grid.addWidget(self.cost_tab_sub_module_combo, 0, 5)
        cost_tab_frame_grid.addWidget(cost_tab_start_date_label, 0, 6)
        cost_tab_frame_grid.addWidget(self.cost_tab_start_date_edit, 0, 7)
        cost_tab_frame_grid.addWidget(cost_tab_end_date_label, 0, 8)
        cost_tab_frame_grid.addWidget(self.cost_tab_end_date_edit, 0, 9)
        cost_tab_frame_grid.addWidget(cost_tab_export_button, 0, 10)

        cost_tab_frame_grid.setColumnStretch(0, 1)
        cost_tab_frame_grid.setColumnStretch(1, 1)
        cost_tab_frame_grid.setColumnStretch(2, 1)
        cost_tab_frame_grid.setColumnStretch(3, 1)
        cost_tab_frame_grid.setColumnStretch(4, 1)
        cost_tab_frame_grid.setColumnStretch(5, 1)
        cost_tab_frame_grid.setColumnStretch(6, 1)
        cost_tab_frame_grid.setColumnStretch(7, 1)
        cost_tab_frame_grid.setColumnStretch(8, 1)
        cost_tab_frame_grid.setColumnStretch(9, 1)

        self.cost_tab_frame.setLayout(cost_tab_frame_grid)
        self.init_cost_tab_combo()

    def init_cost_tab_combo(self):
        """
        Initialization self.cost_tab combo settings.
        """
        self.cost_tab_unit_combo.addItems(['ALL'] + self.current_zebu_dic['unit_list'])
        self.cost_tab_module_combo.addItems(['ALL'] + self.current_zebu_dic['module_list'])
        self.cost_tab_sub_module_combo.addItems(['ALL'] + self.current_zebu_dic['sub_module_list'])

    def cost_tab_unit_combo_activated(self):
        """
        If self.cost_tab_unit_combo current value is "ALL", set self.cost_tab_module_combo and self.cost_tab_sub_module_combo to "ALL".
        """
        if self.cost_tab_unit_combo.currentText() == 'ALL':
            self.cost_tab_module_combo.setCurrentText('ALL')
            self.cost_tab_sub_module_combo.setCurrentText('ALL')

    def cost_tab_module_combo_activated(self):
        if self.cost_tab_module_combo.currentText() != 'ALL':
            if self.cost_tab_unit_combo.currentText() == 'ALL':
                self.cost_tab_unit_combo.setCurrentIndex(1)
        else:
            self.cost_tab_sub_module_combo.setCurrentText('ALL')

    def cost_tab_sub_module_combo_activated(self):
        if self.cost_tab_sub_module_combo.currentText() != 'ALL':
            if self.cost_tab_unit_combo.currentText() == 'ALL' or self.cost_tab_module_combo.currentText() == 'ALL':
                self.cost_tab_unit_combo.setCurrentIndex(1)
                self.cost_tab_module_combo.setCurrentIndex(1)

    def get_cost_info(self, unit, module, sub_module, start_date, end_date):
        # Print loading cost informaiton message.
        logger.critical('Loading cost information, please wait a moment ...')
        cost_info_dic = {}

        start_date_time = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_time = datetime.strptime(end_date, '%Y-%m-%d')

        zebu_system_dir_list = []

        if end_date_time >= start_date_time:
            for record_day in sorted(self.zebu_system_dir_dic.keys()):
                try:
                    record_day_time = datetime.strptime(record_day, '%Y-%m-%d')
                except Exception as error:
                    logger.error('Find Error {} in zebu_system_dir date setting, please check!'.format(str(error)))
                    sys.exit(1)

                if record_day_time < end_date_time:
                    zebu_system_dir_list.append(self.zebu_system_dir_dic[record_day])

        var_dic = {'FROMDATE': start_date_time.strftime('%Y/%m/%d'), 'TODATE': end_date_time.strftime('%Y/%m/%d')}

        for zebu_system_dir in zebu_system_dir_list:
            var_dic['ZEBU_SYSTEM_DIR'] = zebu_system_dir
            check_report_command = config.check_report_command.format_map(var_dic)

            # Run zRscManager to get utilization information
            sys_report_lines = os.popen(check_report_command).read().split('\n')

            end_date_utc = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

            # Read sys_report lines
            for line in sys_report_lines:
                if line:
                    # Split line in to useful information
                    start_time, end_time, modules, user, pid, host = line.split(',')

                    if host.strip() == 'None':
                        continue

                    modules_list = modules.strip('()').split(' ')

                    for module_name in modules_list:
                        if my_match := re.match(r'(\S+)\.(\S+)\.(\S+)', module_name):
                            record_unit = my_match.group(1)
                            record_module = my_match.group(2)
                            record_sub_module = my_match.group(3)

                            if (unit != 'ALL' and record_unit != unit) or (module != 'ALL' and record_module != module) or (sub_module != 'ALL' and sub_module != record_sub_module):
                                continue

                            cost_info_dic.setdefault(record_unit, {})
                            cost_info_dic[record_unit].setdefault(record_module, {})
                            cost_info_dic[record_unit][record_module].setdefault(record_sub_module, {})

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

                            total_seconds = (end_time_utc - start_time_utc).total_seconds()

                            if hasattr(config, 'zebu_project_primary_factors'):
                                project_dic = common.get_project_info(config.zebu_project_primary_factors, self.project_proportion_dic, execute_host=host, user=user)
                            else:
                                project_dic = {}
                                logger.error("zebu_project_primary_factors doesn't has dinifition, please check!")

                            if not project_dic:
                                if 'UNKOWN' not in cost_info_dic[record_unit][record_module][record_sub_module]:
                                    cost_info_dic[record_unit][record_module][record_sub_module].setdefault('UNKOWN', total_seconds)
                                else:
                                    cost_info_dic[record_unit][record_module][record_sub_module]['UNKOWN'] += total_seconds
                            else:
                                for project in project_dic.keys():
                                    if project not in cost_info_dic[record_unit][record_module][record_sub_module]:
                                        cost_info_dic[record_unit][record_module][record_sub_module].setdefault(project, project_dic[project] * total_seconds)
                                    else:
                                        cost_info_dic[record_unit][record_module][record_sub_module][project] += project_dic[project] * total_seconds

                                    if project not in self.project_list:
                                        self.project_list.append(project)

        return cost_info_dic

    def gen_cost_tab_table(self):
        start_date = self.cost_tab_start_date_edit.date().toString(Qt.ISODate)
        end_date = self.cost_tab_end_date_edit.date().toString(Qt.ISODate)

        unit = self.cost_tab_unit_combo.currentText().strip()
        module = self.cost_tab_module_combo.currentText().strip()
        sub_module = self.cost_tab_sub_module_combo.currentText().strip()

        if unit and module and sub_module and start_date and end_date and start_date <= end_date:
            cost_dic = self.get_cost_info(unit, module, sub_module, start_date, end_date)

            self.cost_tab_table_title_list = ['Unit', 'Module', 'Sub Module', 'TotalHours']
            self.cost_tab_table_title_list.extend(self.project_list)

            self.cost_tab_table.setShowGrid(True)
            self.cost_tab_table.setSortingEnabled(True)
            self.cost_tab_table.setColumnCount(0)
            self.cost_tab_table.setColumnCount(len(self.cost_tab_table_title_list))
            self.cost_tab_table.setHorizontalHeaderLabels(self.cost_tab_table_title_list)
            self.cost_tab_table.setColumnWidth(0, 120)
            self.cost_tab_table.setColumnWidth(1, 120)
            self.cost_tab_table.setColumnWidth(2, 120)
            self.cost_tab_table.setColumnWidth(3, 120)

            for column in range(4, len(self.cost_tab_table_title_list)):
                self.cost_tab_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Stretch)

                # Set self.cost_tab_table row length.
                row_length = 0

                for unit in cost_dic.keys():
                    for module in cost_dic[unit].keys():
                        for sub_module in cost_dic[unit][module].keys():
                            row_length += 1

                self.cost_tab_table.setRowCount(0)
                self.cost_tab_table.setRowCount(row_length)

                # Fill self.cost_tab_table items.
                i = -1

                for unit in cost_dic.keys():
                    for module in cost_dic[unit].keys():
                        for sub_module in cost_dic[unit][module].keys():
                            i += 1

                            # Get total_runtime information.
                            total_sampling = 0
                            others_sampling = 0

                            for project in cost_dic[unit][module][sub_module].keys():
                                project_sampling = cost_dic[unit][module][sub_module][project]
                                total_sampling += project_sampling

                                if project not in self.project_list:
                                    others_sampling += cost_dic[unit][module][sub_module][project]

                            # Fill "Unit" item.
                            item = QTableWidgetItem(unit)
                            self.cost_tab_table.setItem(i, 0, item)

                            # Fill "Module" item
                            item = QTableWidgetItem(module)
                            self.cost_tab_table.setItem(i, 1, item)

                            # Fill "Sub Module" item
                            item = QTableWidgetItem(sub_module)
                            self.cost_tab_table.setItem(i, 2, item)

                            # Fill "TotalHours" item
                            total_sampling = total_sampling if self.enable_cost_others_project else (total_sampling - others_sampling)

                            item = QTableWidgetItem(str(round(total_sampling / 3600, 2)))
                            self.cost_tab_table.setItem(i, 3, item)

                            # Fill "project*" item.
                            j = 3
                            for project in self.project_list:
                                if project in cost_dic[unit][module][sub_module]:
                                    project_sampling = cost_dic[unit][module][sub_module][project]
                                else:
                                    project_sampling = 0

                                if project == 'others':
                                    project_sampling += others_sampling

                                if total_sampling == 0:
                                    if self.enable_use_default_cost_rate:
                                        project_rate = self.default_project_cost_dic[project]
                                    else:
                                        project_rate = 0
                                else:
                                    project_rate = round(100 * (project_sampling / total_sampling), 2)

                                if re.match(r'^(\d+)\.0+$', str(project_rate)):
                                    my_match = re.match(r'^(\d+)\.0+$', str(project_rate))
                                    project_rate = int(my_match.group(1))

                                item = QTableWidgetItem()
                                item.setData(Qt.DisplayRole, str(project_rate) + '%')

                                if total_sampling == 0:
                                    item.setForeground(Qt.gray)
                                elif (project == 'others') and (project_rate != 0):
                                    item.setForeground(Qt.red)

                                j += 1
                                self.cost_tab_table.setItem(i, j, item)

    def func_enable_cost_others_project(self, state):
        """
        Class no-project license usage to "others" project with self.enable_cost_others_project.
        """
        if state:
            self.enable_cost_others_project = True

            if 'others' not in self.project_list:
                self.project_list.append('others')
        else:
            self.enable_cost_others_project = False

            if 'others' in self.project_list:
                self.project_list.remove('others')

        self.gen_cost_tab_table()

    def func_enable_use_default_cost_rate(self, state):
        if state:
            self.enable_use_default_cost_rate = True
        else:
            self.enable_use_default_cost_rate = False

        self.gen_cost_tab_table()

    def export_current_table(self):
        self.export_table('current', self.current_tab_table, self.current_tab_table_title_list)

    def export_history_table(self):
        self.export_table('history', self.history_tab_table, self.history_tab_table_title_list)

    def export_cost_table(self):
        self.export_table('cost', self.cost_tab_table, self.cost_tab_table_title_list)

    def export_table(self, table_type, table_item, title_list):
        """
        Export specified table info into an Excel.
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_time_string = re.sub('-', '', current_time)
        current_time_string = re.sub(':', '', current_time_string)
        current_time_string = re.sub(' ', '_', current_time_string)
        default_output_file = './zebuMonitor_' + str(table_type) + '_' + str(current_time_string) + '.xlsx'
        (output_file, output_file_type) = QFileDialog.getSaveFileName(self, 'Export ' + str(table_type) + ' table', default_output_file, 'Excel (*.xlsx)')

        if output_file:
            # Get table content.
            table_info_list = []
            table_info_list.append(title_list)

            for row in range(table_item.rowCount()):
                row_list = []

                for column in range(table_item.columnCount()):
                    if table_item.item(row, column):
                        row_list.append(table_item.item(row, column).text())
                    else:
                        row_list.append('')

                table_info_list.append(row_list)

            # Write excel
            print('* [' + str(current_time) + '] Writing ' + str(table_type) + ' table into "' + str(output_file) + '" ...')

            common.write_excel(excel_file=output_file, contents_list=table_info_list, specified_sheet_name=table_type)


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
