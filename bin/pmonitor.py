# -*- coding: utf-8 -*-

import os
import re
import sys
import stat
import yaml
import getpass
import datetime
import argparse
import logging

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, qApp, QTabWidget, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QMessageBox, QLineEdit, QComboBox, QHeaderView, QDateEdit, QFileDialog
from PyQt5.QtCore import Qt, QThread, QDate

from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/common')
import common
import common_pyqt5
import common_palladium

# Import local config file if exists.
local_config_dir = str(os.environ['HOME']) + '/.palladiumMonitor/config'
local_config = str(local_config_dir) + '/config.py'

if os.path.exists(local_config):
    sys.path.append(local_config_dir)
    import config
else:
    sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config')
    import config

os.environ['PYTHONUNBUFFERED'] = '1'
logger = common.get_logger(level=logging.WARNING)

# Solve some unexpected warning message.
if 'XDG_RUNTIME_DIR' not in os.environ:
    user = getpass.getuser()
    os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-' + str(user)

    if not os.path.exists(os.environ['XDG_RUNTIME_DIR']):
        os.makedirs(os.environ['XDG_RUNTIME_DIR'])

    os.chmod(os.environ['XDG_RUNTIME_DIR'], stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)


def read_args():
    """
    Read arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        default=False,
                        help='Enable debug mode.')

    args = parser.parse_args()

    if args.debug:
        logger = common.get_logger(level=logging.DEBUG)
    else:
        logger = common.get_logger(level=logging.WARNING)


class FigureCanvas(FigureCanvasQTAgg):
    """
    Generate a new figure canvas.
    """
    def __init__(self):
        self.figure = Figure()
        super().__init__(self.figure)


class MainWindow(QMainWindow):
    """
    Main window of palladiumMonitor.
    """
    def __init__(self):
        super().__init__()
        self.current_palladium_dic = {}
        self.hostiry_palladium_dic = {}
        self.history_palladium_path_dic = self.parse_db_path()

        if hasattr(config, 'palladium_enable_cost_others_project'):
            self.enable_cost_others_project = config.palladium_enable_cost_others_project
        else:
            logger.error("Could not find the definition of zebu_enable_cost_others_project in config!")

        if hasattr(config, 'palladium_enable_use_default_cost_rate'):
            self.enable_use_default_cost_rate = config.palladium_enable_use_default_cost_rate
        else:
            logger.error("Could not find the definition of zebu_enable_use_default_cost_rate in config!")

        # Get project related information.
        Z1_project_list_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/palladium/Z1/project_list'
        self.Z1_project_list, self.Z1_default_project_cost_dic = common.parse_project_list_file(Z1_project_list_file)

        Z2_project_list_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/palladium/Z2/project_list'
        self.Z2_project_list, self.Z2_default_project_cost_dic = common.parse_project_list_file(Z2_project_list_file)

        self.total_project_list = list(set(self.Z1_project_list).union(self.Z2_project_list))

        self.Z1_default_project_cost_dic['others'] = 0
        self.Z2_default_project_cost_dic['others'] = 0

        if self.enable_cost_others_project:
            self.Z1_project_list.append('others')
            self.Z2_project_list.append('others')
            self.total_project_list.append('others')

        self.init_ui()

    def parse_db_path(self):
        """
        Parse config.db_path, get history_palladium_path_dic with history palladium info (yaml file).
        """
        history_palladium_path_dic = {}

        if os.path.exists(config.db_path) and os.path.isdir(config.db_path):
            # Check db path. (get hardware)
            for hardware in os.listdir(config.db_path):
                hardware_path = str(config.db_path) + '/' + str(hardware)

                if os.path.isdir(hardware_path):
                    history_palladium_path_dic.setdefault(hardware, {})

                    # Check hardware path. (get emulator)
                    for emulator in os.listdir(hardware_path):
                        emulator_path = str(hardware_path) + '/' + str(emulator)

                        if os.path.isdir(emulator_path):
                            history_palladium_path_dic[hardware].setdefault(emulator, {})

                            # Check emulator path. (get year)
                            for year in os.listdir(emulator_path):
                                year_path = str(emulator_path) + '/' + str(year)

                                if os.path.isdir(year_path):
                                    history_palladium_path_dic[hardware][emulator].setdefault(year, {})

                                    # Check year path. (get month)
                                    for month in os.listdir(year_path):
                                        month_path = str(year_path) + '/' + str(month)

                                        if os.path.isdir(month_path):
                                            history_palladium_path_dic[hardware][emulator][year].setdefault(month, {})

                                            # Check month path. (get day)
                                            for day in os.listdir(month_path):
                                                day_path = str(month_path) + '/' + str(day)

                                                if os.path.isdir(day_path):
                                                    history_palladium_path_dic[hardware][emulator][year][month].setdefault(day, {})

                                                    # Check day path. (get time)
                                                    for time in os.listdir(day_path):
                                                        time_path = str(day_path) + '/' + str(time)

                                                        if os.path.isfile(time_path):
                                                            history_palladium_path_dic[hardware][emulator][year][month][day].setdefault(time, time_path)

        return history_palladium_path_dic

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
        self.setWindowTitle('palladiumMonitor')
        self.resize(1111, 620)
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
        version_action.triggered.connect(self.show_version)

        about_action = QAction('About palladiumMonitor', self)
        about_action.triggered.connect(self.show_about)

        help_menu = menubar.addMenu('Help')
        help_menu.addAction(version_action)
        help_menu.addAction(about_action)

    def show_version(self):
        """
        Show palladiumMonitor version information.
        """
        version = 'V1.0'
        QMessageBox.about(self, 'palladiumMonitor', 'Version: ' + str(version) + '        ')

    def show_about(self):
        """
        Show palladiumMonitor about information.
        """
        about_message = """
Thanks for downloading palladiumMonitor.

palladiumMonitor is an open source software for palladium information data-collection, data-analysis and data-display."""

        QMessageBox.about(self, 'palladiumMonitor', about_message)

# Common sub-functions (begin) #
    def gui_warning(self, warning_message):
        """
        Show the specified warning message on both of command line and GUI window.
        """
        logger.warning(warning_message)
        QMessageBox.warning(self, 'palladiumMonitor Warning', warning_message)
# Common sub-functions (end) #

# For current TAB (start) #
    def gen_current_tab(self):
        """
        Generate the CURRENT tab on palladiumMonitor GUI, show current palladium usage informations.
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
        current_tab_hardware_label = QLabel('Hardware', self.current_tab_frame)
        current_tab_hardware_label.setStyleSheet("font-weight: bold;")
        current_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_hardware_combo = QComboBox(self.current_tab_frame)
        self.set_current_tab_hardware_combo(['Z1', 'Z2'])
        self.current_tab_hardware_combo.activated.connect(self.set_current_tab_host_line)

        current_tab_host_label = QLabel('Host', self.current_tab_frame)
        current_tab_host_label.setStyleSheet("font-weight: bold;")
        current_tab_host_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_host_line = QLineEdit()
        self.set_current_tab_host_line()

        current_tab_empty_label = QLabel('', self.current_tab_frame)

        current_tab_check_button = QPushButton('Check', self.current_tab_frame)
        current_tab_check_button.setStyleSheet("font-weight: bold;")
        current_tab_check_button.clicked.connect(self.check_current_palladium_info)

        current_tab_rack_label = QLabel('Rack', self.current_tab_frame)
        current_tab_rack_label.setStyleSheet("font-weight: bold;")
        current_tab_rack_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_rack_combo = QComboBox(self.current_tab_frame)
        self.current_tab_rack_combo.activated.connect(self.update_current_tab_table)

        current_tab_cluster_label = QLabel('Cluster', self.current_tab_frame)
        current_tab_cluster_label.setStyleSheet("font-weight: bold;")
        current_tab_cluster_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_cluster_combo = QComboBox(self.current_tab_frame)
        self.current_tab_cluster_combo.activated.connect(self.update_current_tab_table)

        current_tab_logic_drawer_label = QLabel('Logic_Drawer', self.current_tab_frame)
        current_tab_logic_drawer_label.setStyleSheet("font-weight: bold;")
        current_tab_logic_drawer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_logic_drawer_combo = QComboBox(self.current_tab_frame)
        self.current_tab_logic_drawer_combo.activated.connect(self.update_current_tab_table)

        current_tab_domain_label = QLabel('Domain', self.current_tab_frame)
        current_tab_domain_label.setStyleSheet("font-weight: bold;")
        current_tab_domain_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_domain_combo = QComboBox(self.current_tab_frame)
        self.current_tab_domain_combo.activated.connect(self.update_current_tab_table)

        current_tab_owner_label = QLabel('Owner', self.current_tab_frame)
        current_tab_owner_label.setStyleSheet("font-weight: bold;")
        current_tab_owner_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_owner_combo = QComboBox(self.current_tab_frame)
        self.current_tab_owner_combo.activated.connect(self.update_current_tab_table)

        current_tab_pid_label = QLabel('PID', self.current_tab_frame)
        current_tab_pid_label.setStyleSheet("font-weight: bold;")
        current_tab_pid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_pid_combo = QComboBox(self.current_tab_frame)
        self.current_tab_pid_combo.activated.connect(self.update_current_tab_table)

        current_tab_tpod_label = QLabel('T-Pod', self.current_tab_frame)
        current_tab_tpod_label.setStyleSheet("font-weight: bold;")
        current_tab_tpod_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_tpod_combo = QComboBox(self.current_tab_frame)
        self.current_tab_tpod_combo.activated.connect(self.update_current_tab_table)

        current_tab_design_label = QLabel('Design', self.current_tab_frame)
        current_tab_design_label.setStyleSheet("font-weight: bold;")
        current_tab_design_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_design_combo = QComboBox(self.current_tab_frame)
        self.current_tab_design_combo.activated.connect(self.update_current_tab_table)

        # self.current_tab_frame - Grid
        current_tab_frame_grid = QGridLayout()

        current_tab_frame_grid.addWidget(current_tab_hardware_label, 0, 0)
        current_tab_frame_grid.addWidget(self.current_tab_hardware_combo, 0, 1)
        current_tab_frame_grid.addWidget(current_tab_host_label, 0, 2)
        current_tab_frame_grid.addWidget(self.current_tab_host_line, 0, 3)
        current_tab_frame_grid.addWidget(current_tab_empty_label, 0, 4, 1, 3)
        current_tab_frame_grid.addWidget(current_tab_check_button, 0, 7)
        current_tab_frame_grid.addWidget(current_tab_rack_label, 1, 0)
        current_tab_frame_grid.addWidget(self.current_tab_rack_combo, 1, 1)
        current_tab_frame_grid.addWidget(current_tab_cluster_label, 1, 2)
        current_tab_frame_grid.addWidget(self.current_tab_cluster_combo, 1, 3)
        current_tab_frame_grid.addWidget(current_tab_logic_drawer_label, 1, 4)
        current_tab_frame_grid.addWidget(self.current_tab_logic_drawer_combo, 1, 5)
        current_tab_frame_grid.addWidget(current_tab_domain_label, 1, 6)
        current_tab_frame_grid.addWidget(self.current_tab_domain_combo, 1, 7)
        current_tab_frame_grid.addWidget(current_tab_owner_label, 2, 0)
        current_tab_frame_grid.addWidget(self.current_tab_owner_combo, 2, 1)
        current_tab_frame_grid.addWidget(current_tab_pid_label, 2, 2)
        current_tab_frame_grid.addWidget(self.current_tab_pid_combo, 2, 3)
        current_tab_frame_grid.addWidget(current_tab_tpod_label, 2, 4)
        current_tab_frame_grid.addWidget(self.current_tab_tpod_combo, 2, 5)
        current_tab_frame_grid.addWidget(current_tab_design_label, 2, 6)
        current_tab_frame_grid.addWidget(self.current_tab_design_combo, 2, 7)

        current_tab_frame_grid.setColumnStretch(0, 1)
        current_tab_frame_grid.setColumnStretch(1, 1)
        current_tab_frame_grid.setColumnStretch(2, 1)
        current_tab_frame_grid.setColumnStretch(3, 1)
        current_tab_frame_grid.setColumnStretch(4, 1)
        current_tab_frame_grid.setColumnStretch(5, 1)
        current_tab_frame_grid.setColumnStretch(6, 1)
        current_tab_frame_grid.setColumnStretch(7, 1)

        self.current_tab_frame.setLayout(current_tab_frame_grid)

    def set_current_tab_hardware_combo(self, hardware_list):
        """
        Set (initialize) self.current_tab_hardware_combo.
        """
        self.current_tab_hardware_combo.clear()

        for hardware in hardware_list:
            self.current_tab_hardware_combo.addItem(hardware)

    def set_current_tab_host_line(self, item=''):
        """
        Set (initialize) self.current_tab_host_line..
        """
        if ((not item) or (item == 0)) and config.Z1_test_server_host:
            host = config.Z1_test_server_host
        elif (item == 1) and config.Z2_test_server_host:
            host = config.Z2_test_server_host

        if host:
            self.current_tab_host_line.setText(host)

    def check_current_palladium_info(self):
        """
        Generate self.current_tab_table with hardware&host information.
        """
        hardware = self.current_tab_hardware_combo.currentText().strip()

        if not hardware:
            my_show_message = ShowMessage('Warning', '"Hardware" is not specified.')
            my_show_message.start()
        else:
            host = self.current_tab_host_line.text().strip()

            if not host:
                my_show_message = ShowMessage('Warning', '"Host" is not specified.')
                my_show_message.start()
            else:
                my_show_message = ShowMessage('Info', 'Loading palladium information, please wait a moment ...')
                my_show_message.start()

                # Get self.current_palladium_dic.
                test_server_info = common_palladium.get_test_server_info(hardware, host)
                self.current_palladium_dic = common_palladium.parse_test_server_info(test_server_info)

                my_show_message.terminate()

                if self.current_palladium_dic:
                    # Update QComboBox items.
                    self.update_current_tab_frame()

                    # Update self.current_tab_table.
                    self.gen_current_tab_table()
                else:
                    logger.warning('Not find any valid palladium information.')

    def update_current_tab_frame(self):
        """
        Update *_combo items on self.current_tab_frame..
        """
        # Update self.current_tab_rack_combo
        self.current_tab_rack_combo.clear()
        self.current_tab_rack_combo.addItem('ALL')

        for rack in self.current_palladium_dic['rack_list']:
            self.current_tab_rack_combo.addItem(rack)

        # Update self.current_tab_cluster_combo
        self.current_tab_cluster_combo.clear()
        self.current_tab_cluster_combo.addItem('ALL')

        for cluster in self.current_palladium_dic['cluster_list']:
            self.current_tab_cluster_combo.addItem(cluster)

        # Update self.current_tab_logic_drawer_combo
        self.current_tab_logic_drawer_combo.clear()
        self.current_tab_logic_drawer_combo.addItem('ALL')

        for logic_drawer in self.current_palladium_dic['logic_drawer_list']:
            self.current_tab_logic_drawer_combo.addItem(logic_drawer)

        # Update self.current_tab_domain_combo
        self.current_tab_domain_combo.clear()
        self.current_tab_domain_combo.addItem('ALL')

        for domain in self.current_palladium_dic['domain_list']:
            self.current_tab_domain_combo.addItem(domain)

        # Update self.current_tab_owner_combo
        self.current_tab_owner_combo.clear()
        self.current_tab_owner_combo.addItem('ALL')

        for owner in self.current_palladium_dic['owner_list']:
            self.current_tab_owner_combo.addItem(owner)

        # Update self.current_tab_pid_combo
        self.current_tab_pid_combo.clear()
        self.current_tab_pid_combo.addItem('ALL')

        for pid in self.current_palladium_dic['pid_list']:
            self.current_tab_pid_combo.addItem(pid)

        # Update self.current_tab_tpod_combo
        self.current_tab_tpod_combo.clear()
        self.current_tab_tpod_combo.addItem('ALL')

        for tpod in self.current_palladium_dic['tpod_list']:
            self.current_tab_tpod_combo.addItem(tpod)

        # Update self.current_tab_design_combo
        self.current_tab_design_combo.clear()
        self.current_tab_design_combo.addItem('ALL')

        for design in self.current_palladium_dic['design_list']:
            self.current_tab_design_combo.addItem(design)

    def gen_palladium_info_table(self, palladium_info_table, palladium_dic):
        """
        Common function, generate specified table with specified palladium info (palladium_dic).
        """
        # palladium_info_table
        palladium_info_table.setShowGrid(True)
        palladium_info_table.setSortingEnabled(True)
        palladium_info_table.setColumnCount(0)
        palladium_info_table.setColumnCount(10)
        palladium_info_table.setHorizontalHeaderLabels(['Rack', 'Cluster', 'Logic drawer', 'Domain', 'Owner', 'PID', 'T-Pod', 'Design', 'ElapTime', 'ReservedKey'])

        palladium_info_table.setColumnWidth(0, 60)
        palladium_info_table.setColumnWidth(1, 70)
        palladium_info_table.setColumnWidth(2, 100)
        palladium_info_table.setColumnWidth(3, 70)
        palladium_info_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        palladium_info_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        palladium_info_table.setColumnWidth(6, 80)
        palladium_info_table.setColumnWidth(7, 90)
        palladium_info_table.setColumnWidth(8, 90)
        palladium_info_table.setColumnWidth(9, 100)

        row = -1

        # Fill palladium_info_table.
        palladium_info_table.setRowCount(0)

        if palladium_dic:
            domain_line_num = palladium_dic['domain_line_num']
            palladium_info_table.setRowCount(domain_line_num)

            for rack in palladium_dic['rack'].keys():
                for cluster in palladium_dic['rack'][rack]['cluster'].keys():
                    for logic_drawer in palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'].keys():
                        for domain in palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'].keys():
                            owner = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['owner']
                            pid = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['pid']
                            tpod = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['tpod']
                            design = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['design']
                            elaptime = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['elaptime']
                            reservedkey = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['reservedkey']
                            row += 1

                            # Fill "Rack"
                            item = QTableWidgetItem(rack)
                            palladium_info_table.setItem(row, 0, item)

                            # Fill "Cluster"
                            item = QTableWidgetItem(cluster)
                            palladium_info_table.setItem(row, 1, item)

                            # Fill "Logic drawer"
                            item = QTableWidgetItem(logic_drawer)
                            palladium_info_table.setItem(row, 2, item)

                            # Fill "Domain"
                            item = QTableWidgetItem(domain)
                            palladium_info_table.setItem(row, 3, item)

                            # Fill "Owner"
                            item = QTableWidgetItem(owner)
                            palladium_info_table.setItem(row, 4, item)

                            # Fill "PID"
                            item = QTableWidgetItem(pid)
                            palladium_info_table.setItem(row, 5, item)

                            # Fill "T-Pod"
                            item = QTableWidgetItem(tpod)
                            palladium_info_table.setItem(row, 6, item)

                            # Fill "Design"
                            item = QTableWidgetItem(design)
                            palladium_info_table.setItem(row, 7, item)

                            # Fill "Elaptime"
                            item = QTableWidgetItem(elaptime)
                            palladium_info_table.setItem(row, 8, item)

                            # Fill "ReservedKey"
                            item = QTableWidgetItem(reservedkey)
                            palladium_info_table.setItem(row, 9, item)

    def gen_current_tab_table(self):
        self.gen_palladium_info_table(self.current_tab_table, self.current_palladium_dic)

    def update_current_tab_table(self):
        """
        Filter self.current_palladium_dic with self.current_tab_frame items.
        Re-generate self.current_table_table with filtered palladium dic.
        """
        rack = self.current_tab_rack_combo.currentText().strip()
        cluster = self.current_tab_cluster_combo.currentText().strip()
        logic_drawer = self.current_tab_logic_drawer_combo.currentText().strip()
        domain = self.current_tab_domain_combo.currentText().strip()
        owner = self.current_tab_owner_combo.currentText().strip()
        pid = self.current_tab_pid_combo.currentText().strip()
        tpod = self.current_tab_tpod_combo.currentText().strip()
        design = self.current_tab_design_combo.currentText().strip()

        filtered_palladium_dic = common_palladium.filter_palladium_dic(self.current_palladium_dic, specified_rack=rack, specified_cluster=cluster, specified_logic_drawer=logic_drawer, specified_domain=domain, specified_owner=owner, specified_pid=pid, specified_tpod=tpod, specified_design=design)

        self.gen_palladium_info_table(self.current_tab_table, filtered_palladium_dic)
# For current TAB (end) #

# For history TAB (start) #
    def gen_history_tab(self):
        """
        Generate the HISTORY tab on palladiumMonitor GUI, show history palladium usage informations.
        """
        # self.history_tab
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
        Generate self.history_tab_frame.
        """
        # self.history_tab_frame
        history_tab_hardware_label = QLabel('Hardware', self.history_tab_frame)
        history_tab_hardware_label.setStyleSheet("font-weight: bold;")
        history_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_hardware_combo = QComboBox(self.history_tab_frame)
        self.history_tab_hardware_combo.activated.connect(self.set_history_tab_emulator_combo)

        history_tab_emulator_label = QLabel('Emulator', self.history_tab_frame)
        history_tab_emulator_label.setStyleSheet("font-weight: bold;")
        history_tab_emulator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_emulator_combo = QComboBox(self.history_tab_frame)
        self.history_tab_emulator_combo.activated.connect(self.set_history_tab_year_combo)

        history_tab_year_label = QLabel('Year', self.history_tab_frame)
        history_tab_year_label.setStyleSheet("font-weight: bold;")
        history_tab_year_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_year_combo = QComboBox(self.history_tab_frame)
        self.history_tab_year_combo.activated.connect(self.set_history_tab_month_combo)

        history_tab_month_label = QLabel('Month', self.history_tab_frame)
        history_tab_month_label.setStyleSheet("font-weight: bold;")
        history_tab_month_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_month_combo = QComboBox(self.history_tab_frame)
        self.history_tab_month_combo.activated.connect(self.set_history_tab_day_combo)

        history_tab_day_label = QLabel('Day', self.history_tab_frame)
        history_tab_day_label.setStyleSheet("font-weight: bold;")
        history_tab_day_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_day_combo = QComboBox(self.history_tab_frame)
        self.history_tab_day_combo.activated.connect(self.set_history_tab_time_combo)

        history_tab_time_label = QLabel('Time', self.history_tab_frame)
        history_tab_time_label.setStyleSheet("font-weight: bold;")
        history_tab_time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_time_combo = QComboBox(self.history_tab_frame)
        self.history_tab_time_combo.activated.connect(self.gen_history_tab_table)

        # self.history_tab_frame - Grid
        history_tab_frame_grid = QGridLayout()

        history_tab_frame_grid.addWidget(history_tab_hardware_label, 0, 0)
        history_tab_frame_grid.addWidget(self.history_tab_hardware_combo, 0, 1)
        history_tab_frame_grid.addWidget(history_tab_emulator_label, 0, 2)
        history_tab_frame_grid.addWidget(self.history_tab_emulator_combo, 0, 3)
        history_tab_frame_grid.addWidget(history_tab_year_label, 1, 0)
        history_tab_frame_grid.addWidget(self.history_tab_year_combo, 1, 1)
        history_tab_frame_grid.addWidget(history_tab_month_label, 1, 2)
        history_tab_frame_grid.addWidget(self.history_tab_month_combo, 1, 3)
        history_tab_frame_grid.addWidget(history_tab_day_label, 1, 4)
        history_tab_frame_grid.addWidget(self.history_tab_day_combo, 1, 5)
        history_tab_frame_grid.addWidget(history_tab_time_label, 1, 6)
        history_tab_frame_grid.addWidget(self.history_tab_time_combo, 1, 7)

        history_tab_frame_grid.setColumnStretch(0, 1)
        history_tab_frame_grid.setColumnStretch(1, 1)
        history_tab_frame_grid.setColumnStretch(2, 1)
        history_tab_frame_grid.setColumnStretch(3, 1)
        history_tab_frame_grid.setColumnStretch(4, 1)
        history_tab_frame_grid.setColumnStretch(5, 1)
        history_tab_frame_grid.setColumnStretch(6, 1)
        history_tab_frame_grid.setColumnStretch(7, 1)

        self.history_tab_frame.setLayout(history_tab_frame_grid)

        # Init self.history_tab_frame.
        self.set_history_tab_hardware_combo()

    def set_history_tab_hardware_combo(self):
        """
        Set (initialize) self.history_tab_hardware_combo.
        """
        self.history_tab_hardware_combo.clear()
        self.history_tab_hardware_combo.addItem('')

        for hardware in self.history_palladium_path_dic.keys():
            self.history_tab_hardware_combo.addItem(hardware)

        self.set_history_tab_emulator_combo()

    def set_history_tab_emulator_combo(self):
        """
        Set (initialize) self.history_tab_emulator_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()

        if hardware and (hardware in self.history_palladium_path_dic.keys()):
            self.history_tab_emulator_combo.clear()

            for emulator in self.history_palladium_path_dic[hardware].keys():
                self.history_tab_emulator_combo.addItem(emulator)

        self.set_history_tab_year_combo()

    def set_history_tab_year_combo(self):
        """
        Set (initialize) self.history_tab_year_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()

        if hardware and (hardware in self.history_palladium_path_dic.keys()):
            emulator = self.history_tab_emulator_combo.currentText().strip()

            if emulator and (emulator in self.history_palladium_path_dic[hardware].keys()):
                self.history_tab_year_combo.clear()

                for year in self.history_palladium_path_dic[hardware][emulator].keys():
                    self.history_tab_year_combo.addItem(year)

        self.set_history_tab_month_combo()

    def set_history_tab_month_combo(self):
        """
        Set (initialize) self.history_tab_month_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()

        if hardware and (hardware in self.history_palladium_path_dic.keys()):
            emulator = self.history_tab_emulator_combo.currentText().strip()

            if emulator and (emulator in self.history_palladium_path_dic[hardware].keys()):
                year = self.history_tab_year_combo.currentText().strip()

                if year and (year in self.history_palladium_path_dic[hardware][emulator].keys()):
                    self.history_tab_month_combo.clear()

                    for month in self.history_palladium_path_dic[hardware][emulator][year].keys():
                        self.history_tab_month_combo.addItem(month)

        self.set_history_tab_day_combo()

    def set_history_tab_day_combo(self):
        """
        Set (initialize) self.history_tab_day_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()

        if hardware and (hardware in self.history_palladium_path_dic.keys()):
            emulator = self.history_tab_emulator_combo.currentText().strip()

            if emulator and (emulator in self.history_palladium_path_dic[hardware].keys()):
                year = self.history_tab_year_combo.currentText().strip()

                if year and (year in self.history_palladium_path_dic[hardware][emulator].keys()):
                    month = self.history_tab_month_combo.currentText().strip()

                    if month and (month in self.history_palladium_path_dic[hardware][emulator][year].keys()):
                        self.history_tab_day_combo.clear()

                        for day in self.history_palladium_path_dic[hardware][emulator][year][month].keys():
                            self.history_tab_day_combo.addItem(day)

        self.set_history_tab_time_combo()

    def set_history_tab_time_combo(self):
        """
        Set (initialize) self.history_tab_time_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()

        if hardware and (hardware in self.history_palladium_path_dic.keys()):
            emulator = self.history_tab_emulator_combo.currentText().strip()

            if emulator and (emulator in self.history_palladium_path_dic[hardware].keys()):
                year = self.history_tab_year_combo.currentText().strip()

                if year and (year in self.history_palladium_path_dic[hardware][emulator].keys()):
                    month = self.history_tab_month_combo.currentText().strip()

                    if month and (month in self.history_palladium_path_dic[hardware][emulator][year].keys()):
                        day = self.history_tab_day_combo.currentText().strip()

                        if day and (day in self.history_palladium_path_dic[hardware][emulator][year][month].keys()):
                            self.history_tab_time_combo.clear()

                            for time in self.history_palladium_path_dic[hardware][emulator][year][month][day].keys():
                                self.history_tab_time_combo.addItem(time)

        self.gen_history_tab_table()

    def gen_history_tab_table(self):
        """
        Generate self.history_tab_table with filter information from self.history_tab_frame.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()
        emulator = self.history_tab_emulator_combo.currentText().strip()
        year = self.history_tab_year_combo.currentText().strip()
        month = self.history_tab_month_combo.currentText().strip()
        day = self.history_tab_day_combo.currentText().strip()
        time = self.history_tab_time_combo.currentText().strip()

        if hardware and emulator and year and month and day and time:
            time_file = self.history_palladium_path_dic[hardware][emulator][year][month][day][time]

            with open(time_file, 'rb') as TF:
                history_palladium_dic = yaml.load(TF, Loader=yaml.FullLoader)

            self.gen_palladium_info_table(self.history_tab_table, history_palladium_dic)
# For history TAB (end) #

# For utilization TAB (start) #
    def gen_utilization_tab(self):
        """
        Generate the UTILIZATION tab on palladiumMonitor GUI, show palladium utilization informations.
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
        # self.utilization_tab_frame0
        utilization_tab_hardware_label = QLabel('Hardware', self.utilization_tab_frame0)
        utilization_tab_hardware_label.setStyleSheet("font-weight: bold;")
        utilization_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_hardware_combo = QComboBox(self.utilization_tab_frame0)
        self.utilization_tab_hardware_combo.activated.connect(self.set_utilization_tab_emulator_combo)

        utilization_tab_emulator_label = QLabel('Emulator', self.utilization_tab_frame0)
        utilization_tab_emulator_label.setStyleSheet("font-weight: bold;")
        utilization_tab_emulator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_emulator_combo = QComboBox(self.utilization_tab_frame0)
        self.utilization_tab_emulator_combo.activated.connect(self.update_utilization_tab_frame1)

        utilization_tab_start_date_label = QLabel('Start_Date', self.utilization_tab_frame0)
        utilization_tab_start_date_label.setStyleSheet("font-weight: bold;")
        utilization_tab_start_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_start_date_edit = QDateEdit(self.utilization_tab_frame0)
        self.utilization_tab_start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.utilization_tab_start_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.utilization_tab_start_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.utilization_tab_start_date_edit.setCalendarPopup(True)
        self.utilization_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.utilization_tab_start_date_edit.dateChanged.connect(self.update_utilization_tab_frame1)

        utilization_tab_end_date_label = QLabel('End_Date', self.utilization_tab_frame0)
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

        utilization_tab_frame0_grid.addWidget(utilization_tab_hardware_label, 0, 0)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_hardware_combo, 0, 1)
        utilization_tab_frame0_grid.addWidget(utilization_tab_emulator_label, 0, 2)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_emulator_combo, 0, 3)
        utilization_tab_frame0_grid.addWidget(utilization_tab_start_date_label, 0, 4)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_start_date_edit, 0, 5)
        utilization_tab_frame0_grid.addWidget(utilization_tab_end_date_label, 0, 6)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_end_date_edit, 0, 7)

        utilization_tab_frame0_grid.setColumnStretch(0, 1)
        utilization_tab_frame0_grid.setColumnStretch(1, 1)
        utilization_tab_frame0_grid.setColumnStretch(2, 1)
        utilization_tab_frame0_grid.setColumnStretch(3, 1)
        utilization_tab_frame0_grid.setColumnStretch(4, 1)
        utilization_tab_frame0_grid.setColumnStretch(5, 1)
        utilization_tab_frame0_grid.setColumnStretch(6, 1)
        utilization_tab_frame0_grid.setColumnStretch(7, 1)

        self.utilization_tab_frame0.setLayout(utilization_tab_frame0_grid)

        # Init self.utilization_tab_frame0.
        self.set_utilization_tab_hardware_combo()

    def set_utilization_tab_hardware_combo(self):
        """
        Set (initialize) self.utilization_tab_hardware_combo.
        """
        self.utilization_tab_hardware_combo.clear()
        self.utilization_tab_hardware_combo.addItem('')

        for hardware in self.history_palladium_path_dic.keys():
            self.utilization_tab_hardware_combo.addItem(hardware)

        self.set_utilization_tab_emulator_combo()

    def set_utilization_tab_emulator_combo(self):
        """
        Set (initialize) self.utilization_tab_emulator_combo.
        """
        hardware = self.utilization_tab_hardware_combo.currentText().strip()

        if hardware and (hardware in self.history_palladium_path_dic.keys()):
            self.utilization_tab_emulator_combo.clear()

            for emulator in self.history_palladium_path_dic[hardware].keys():
                self.utilization_tab_emulator_combo.addItem(emulator)

        self.update_utilization_tab_frame1()

    def get_utilization_dic(self, hardware, emulator, start_date, end_date):
        """
        Get utilization_dic, with "date - utilization" information.
        """
        utilization_dic = {}
        utilization_file = str(config.db_path) + '/' + str(hardware) + '/' + str(emulator) + '/utilization'

        if os.path.exists(utilization_file):
            full_utilization_dic = {}
            start_date = re.sub(r'-', '', start_date)
            end_date = re.sub(r'-', '', end_date)

            with open(utilization_file, 'r') as UF:
                for line in UF.readlines():
                    if re.match(r'^(\d+)\s+(\d+)\s+:\s+(\S+)\s*$', line.strip()):
                        my_match = re.match(r'^(\d+)\s+(\d+)\s+:\s+(\S+)\s*$', line.strip())
                        date = my_match.group(1)

                        if int(start_date) <= int(date) <= int(end_date):
                            time = my_match.group(2)
                            utilization = my_match.group(3)
                            full_utilization_dic.setdefault(date, {})
                            full_utilization_dic[date].setdefault(time, float(utilization))

            for date in full_utilization_dic.keys():
                utilization = int(sum(full_utilization_dic[date].values()) * 100 / len(full_utilization_dic[date]))
                utilization_dic.setdefault(date, utilization)

        return utilization_dic

    def gen_utilization_tab_frame1(self):
        """
        Generate empty self.utilization_tab_frame1.
        """
        # self.utilization_tab_frame1.
        self.utilization_figure_canvas = FigureCanvas()
        self.utilization_navigation_toolbar = NavigationToolbar2QT(self.utilization_figure_canvas, self)

        # self.utilization_tab_frame1 - Grid
        utilization_tab_frame1_grid = QGridLayout()
        utilization_tab_frame1_grid.addWidget(self.utilization_navigation_toolbar, 0, 0)
        utilization_tab_frame1_grid.addWidget(self.utilization_figure_canvas, 1, 0)
        self.utilization_tab_frame1.setLayout(utilization_tab_frame1_grid)

    def update_utilization_tab_frame1(self):
        """
        Update self.utilization_tab_frame1 with "date - utilization" draw.
        """
        hardware = self.utilization_tab_hardware_combo.currentText().strip()
        emulator = self.utilization_tab_emulator_combo.currentText().strip()
        start_date = self.utilization_tab_start_date_edit.date().toString(Qt.ISODate)
        end_date = self.utilization_tab_end_date_edit.date().toString(Qt.ISODate)

        if hardware and emulator and start_date and end_date:
            utilization_dic = self.get_utilization_dic(hardware, emulator, start_date, end_date)
            date_list = []
            utilization_list = []

            for (date, utilization) in utilization_dic.items():
                date_list.append(date)
                utilization_list.append(utilization)

            if date_list and utilization_list:
                fig = self.utilization_figure_canvas.figure
                fig.clear()
                self.utilization_figure_canvas.draw()

                for i in range(len(date_list)):
                    date_list[i] = datetime.datetime.strptime(date_list[i], '%Y%m%d')

                av_utilization = int(sum(utilization_list) / len(utilization_list))

                self.draw_utilization_curve(fig, av_utilization, date_list, utilization_list)

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
        axes.legend(loc='upper right')
        axes.tick_params(axis='x', rotation=15)
        axes.grid()
        self.utilization_figure_canvas.draw()
# For utilization TAB (end) #

# For cost TAB (start) #
    def gen_cost_tab(self):
        """
        Generate the COST tab on palladiumMonitor GUI, show palladium cost informations.
        """
        # self.utilization_tab
        self.cost_tab_frame0 = QFrame(self.cost_tab)
        self.cost_tab_frame0.setFrameShadow(QFrame.Raised)
        self.cost_tab_frame0.setFrameShape(QFrame.Box)

        self.cost_tab_table = QTableWidget(self.cost_tab)

        # self.utilization_tab - Grid
        cost_tab_grid = QGridLayout()

        cost_tab_grid.addWidget(self.cost_tab_frame0, 0, 0)
        cost_tab_grid.addWidget(self.cost_tab_table, 1, 0)

        cost_tab_grid.setRowStretch(0, 1)
        cost_tab_grid.setRowStretch(1, 20)

        self.cost_tab.setLayout(cost_tab_grid)

        # Generate sub-frame
        self.gen_cost_tab_frame0()
        self.gen_cost_tab_table()

    def gen_cost_tab_frame0(self):
        """
        Generate self.cost_tab_frame0, which contains filter items.
        """
        # self.utilization_tab_frame0
        cost_tab_hardware_label = QLabel('Hardware', self.cost_tab_frame0)
        cost_tab_hardware_label.setStyleSheet("font-weight: bold;")
        cost_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_hardware_combo = QComboBox(self.cost_tab_frame0)
        self.cost_tab_hardware_combo.activated.connect(self.set_cost_tab_emulator_combo)

        cost_tab_emulator_label = QLabel('Emulator', self.cost_tab_frame0)
        cost_tab_emulator_label.setStyleSheet("font-weight: bold;")
        cost_tab_emulator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_emulator_combo = QComboBox(self.cost_tab_frame0)
        self.cost_tab_emulator_combo.activated.connect(self.gen_cost_tab_table)

        cost_tab_start_date_label = QLabel('Start_Date', self.cost_tab_frame0)
        cost_tab_start_date_label.setStyleSheet("font-weight: bold;")
        cost_tab_start_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_start_date_edit = QDateEdit(self.cost_tab_frame0)
        self.cost_tab_start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.cost_tab_start_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.cost_tab_start_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.cost_tab_start_date_edit.setCalendarPopup(True)
        self.cost_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.cost_tab_start_date_edit.dateChanged.connect(self.gen_cost_tab_table)

        cost_tab_end_date_label = QLabel('End_Date', self.cost_tab_frame0)
        cost_tab_end_date_label.setStyleSheet("font-weight: bold;")
        cost_tab_end_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_end_date_edit = QDateEdit(self.cost_tab_frame0)
        self.cost_tab_end_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.cost_tab_end_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.cost_tab_end_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.cost_tab_end_date_edit.setCalendarPopup(True)
        self.cost_tab_end_date_edit.setDate(QDate.currentDate())
        self.cost_tab_end_date_edit.dateChanged.connect(self.gen_cost_tab_table)

        cost_tab_export_button = QPushButton('Export', self.cost_tab_frame0)
        cost_tab_export_button.setStyleSheet('''QPushButton:hover{background:rgb(170, 255, 127);}''')
        cost_tab_export_button.clicked.connect(self.export_cost_info)

        # self.utilization_tab_frame0 - Grid
        cost_tab_frame0_grid = QGridLayout()

        cost_tab_frame0_grid.addWidget(cost_tab_hardware_label, 0, 0)
        cost_tab_frame0_grid.addWidget(self.cost_tab_hardware_combo, 0, 1)
        cost_tab_frame0_grid.addWidget(cost_tab_emulator_label, 0, 2)
        cost_tab_frame0_grid.addWidget(self.cost_tab_emulator_combo, 0, 3)
        cost_tab_frame0_grid.addWidget(cost_tab_start_date_label, 0, 4)
        cost_tab_frame0_grid.addWidget(self.cost_tab_start_date_edit, 0, 5)
        cost_tab_frame0_grid.addWidget(cost_tab_end_date_label, 0, 6)
        cost_tab_frame0_grid.addWidget(self.cost_tab_end_date_edit, 0, 7)
        cost_tab_frame0_grid.addWidget(cost_tab_export_button, 0, 8)

        cost_tab_frame0_grid.setColumnStretch(0, 1)
        cost_tab_frame0_grid.setColumnStretch(1, 1)
        cost_tab_frame0_grid.setColumnStretch(2, 1)
        cost_tab_frame0_grid.setColumnStretch(3, 1)
        cost_tab_frame0_grid.setColumnStretch(4, 1)
        cost_tab_frame0_grid.setColumnStretch(5, 1)
        cost_tab_frame0_grid.setColumnStretch(6, 1)
        cost_tab_frame0_grid.setColumnStretch(7, 1)
        cost_tab_frame0_grid.setColumnStretch(8, 1)

        self.cost_tab_frame0.setLayout(cost_tab_frame0_grid)

        # Init self.utilization_tab_frame0.
        self.set_cost_tab_hardware_combo()

    def get_cost_info(self):
        """
        Get emulator sampling counts information from config.db_path cost file
        cost_dic = {<hardware>: {<emulator>: {<project>: <project_sampling>}}}
        """
        # Print loading cost informaiton message.
        logger.critical('Loading cost information, please wait a moment ...')

        begin_date = self.cost_tab_start_date_edit.date().toPyDate()
        end_date = self.cost_tab_end_date_edit.date().toPyDate()
        day_inteval = (end_date - begin_date).days

        selected_hardware = self.cost_tab_hardware_combo.currentText().strip()
        selected_emulator = self.cost_tab_emulator_combo.currentText().strip()

        cost_dic = {}

        # Filter with hardware/emulator
        for hardware in self.history_palladium_path_dic.keys():
            if (selected_hardware == 'ALL') or (selected_hardware == hardware):
                for emulator in self.history_palladium_path_dic[hardware].keys():
                    if (selected_emulator == 'ALL') or (selected_emulator == emulator):
                        # Get palladium sampling counts infomation in datebase
                        if hardware not in cost_dic:
                            cost_dic.setdefault(hardware, {})

                        if emulator not in cost_dic[hardware]:
                            cost_dic[hardware].setdefault(emulator, {})

                        cost_file = str(config.db_path) + '/' + str(hardware) + '/' + str(emulator) + '/cost'

                        if os.path.exists(cost_file):
                            total_cost_dic = {}

                            with open(cost_file, 'r') as cf:
                                for line in cf:
                                    line_s = line.replace('\n', '').split()

                                    if re.match(r'^\s*$', line):
                                        continue

                                    # Get date & project:cost infomation
                                    if re.match(r'^\S+\s*(\S+:\S+\s*)+$', line):
                                        date = line_s[0].strip()
                                        history_project_cost_dic = {cost_info.split(':')[0].strip(): int(cost_info.split(':')[1].strip()) for cost_info in line_s[1:]}
                                    else:
                                        logger.warning('Could not find valid infomation in cost file line: ' + line + '!')
                                        continue

                                    total_cost_dic[date] = history_project_cost_dic

                            for day in range(0, day_inteval + 1):
                                cost_date = (begin_date + datetime.timedelta(days=day)).strftime('%Y-%m-%d')

                                if cost_date in total_cost_dic:
                                    for project in total_cost_dic[cost_date]:
                                        if project in cost_dic[hardware][emulator]:
                                            cost_dic[hardware][emulator][project] += total_cost_dic[cost_date][project]
                                        else:
                                            cost_dic[hardware][emulator].setdefault(project, total_cost_dic[cost_date][project])

        return cost_dic

    def gen_cost_tab_table(self):
        """
        Generate self.cost_tab_table.
        """
        cost_dic = self.get_cost_info()
        self.cost_tab_table_title_list = ['Hardware', 'Emulator', 'TotalSamping']
        self.cost_tab_table_title_list.extend(self.total_project_list)

        self.cost_tab_table.setShowGrid(True)
        self.cost_tab_table.setSortingEnabled(True)
        self.cost_tab_table.setColumnCount(0)
        self.cost_tab_table.setColumnCount(len(self.cost_tab_table_title_list))
        self.cost_tab_table.setHorizontalHeaderLabels(self.cost_tab_table_title_list)
        self.cost_tab_table.setColumnWidth(0, 100)
        self.cost_tab_table.setColumnWidth(1, 120)
        self.cost_tab_table.setColumnWidth(2, 120)

        for column in range(3, len(self.cost_tab_table_title_list)):
            self.cost_tab_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Stretch)

        # Set self.cost_tab_table row length.
        row_length = 0

        for hardware in cost_dic.keys():
            for emulator in cost_dic[hardware].keys():
                row_length += 1

        self.cost_tab_table.setRowCount(0)
        self.cost_tab_table.setRowCount(row_length)

        # Fill self.cost_tab_table items.
        i = -1

        for hardware in cost_dic.keys():
            if hardware == 'Z1':
                project_list = self.Z1_project_list
                default_project_cost_dic = self.Z1_default_project_cost_dic
            elif hardware == 'Z2':
                project_list = self.Z2_project_list
                default_project_cost_dic = self.Z2_default_project_cost_dic

            for emulator in cost_dic[hardware].keys():
                i += 1

                # Get total_runtime information.
                total_sampling = 0
                others_sampling = 0

                for project in cost_dic[hardware][emulator].keys():
                    project_sampling = cost_dic[hardware][emulator][project]
                    total_sampling += project_sampling

                    if project not in project_list:
                        others_sampling += cost_dic[hardware][emulator][project]

                # Fill "Hardware" item.
                item = QTableWidgetItem(hardware)
                self.cost_tab_table.setItem(i, 0, item)

                # Fill "Emulator" item
                item = QTableWidgetItem(emulator)
                self.cost_tab_table.setItem(i, 1, item)

                # Fill "total_samping" item
                total_sampling = total_sampling if self.enable_cost_others_project else (total_sampling - others_sampling)

                item = QTableWidgetItem(str(total_sampling))
                self.cost_tab_table.setItem(i, 2, item)

                # Fill "project*" item.
                j = 2

                for project in self.total_project_list:
                    if project in cost_dic[hardware][emulator]:
                        project_sampling = cost_dic[hardware][emulator][project]
                    else:
                        project_sampling = 0

                    if project == 'others':
                        project_sampling += others_sampling

                    if total_sampling == 0:
                        if (project in default_project_cost_dic) and self.enable_use_default_cost_rate:
                            project_rate = default_project_cost_dic[project]
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

    def set_cost_tab_hardware_combo(self):
        """
        Set (initialize) self.cost_tab_hardware_combo.
        """
        self.cost_tab_hardware_combo.clear()

        hardware_list = ['ALL', ]

        for hardware in self.history_palladium_path_dic.keys():
            hardware_list.append(hardware)

        for hardware in hardware_list:
            self.cost_tab_hardware_combo.addItem(hardware)

        self.set_cost_tab_emulator_combo()

    def set_cost_tab_emulator_combo(self):
        """
        Set (initialize) self.cost_tab_emulator_combo.
        """
        hardware = self.cost_tab_hardware_combo.currentText().strip()

        emulator_list = ['ALL', ]

        if hardware and (hardware in self.history_palladium_path_dic.keys()):
            for emulator in self.history_palladium_path_dic[hardware].keys():
                emulator_list.append(emulator)
        else:
            for hardware in self.history_palladium_path_dic.keys():
                for emulator in self.history_palladium_path_dic[hardware].keys():
                    emulator_list.append(emulator)

        self.cost_tab_emulator_combo.clear()

        for emulator in emulator_list:
            self.cost_tab_emulator_combo.addItem(emulator)

        self.gen_cost_tab_table()

    def export_cost_info(self):
        """
        Export self.cost_tab_table into an Excel.
        """
        (cost_info_file, file_type) = QFileDialog.getSaveFileName(self, 'Export cost info', './palladium_cost.xlsx', 'Excel (*.xlsx)')

        if cost_info_file:
            # Get self.cost_tab_label content.
            cost_tab_table_list = []
            cost_tab_table_list.append(self.cost_tab_table_title_list)

            for row in range(self.cost_tab_table.rowCount()):
                row_list = []

                for column in range(self.cost_tab_table.columnCount()):
                    row_list.append(self.cost_tab_table.item(row, column).text())

                cost_tab_table_list.append(row_list)

            # Write excel
            logger.critical('Writing cost info file "' + str(cost_info_file) + '" ...')

            common.write_excel(excel_file=cost_info_file, contents_list=cost_tab_table_list, specified_sheet_name='cost_info')

    def func_enable_cost_others_project(self, state):
        """
        Class no-project license usage to "others" project with self.enable_cost_others_project.
        """
        if state:
            self.enable_cost_others_project = True

            if 'others' not in self.total_project_list:
                self.total_project_list.append('others')

            if 'others' not in self.Z1_project_list:
                self.Z1_project_list.append('others')

            if 'others' not in self.Z2_project_list:
                self.Z2_project_list.append('others')

        else:
            self.enable_cost_others_project = False

            if 'others' in self.total_project_list:
                self.total_project_list.remove('others')

            if 'others' in self.Z1_project_list:
                self.Z1_project_list.remove('others')

            if 'others' in self.Z2_project_list:
                self.Z2_project_list.remove('others')

        self.gen_cost_tab_table()

    def func_enable_use_default_cost_rate(self, state):
        if state:
            self.enable_use_default_cost_rate = True
        else:
            self.enable_use_default_cost_rate = False

        self.gen_cost_tab_table()
# For cost TAB (end) #

    def close_event(self, QCloseEvent):
        """
        When window close, post-process.
        """
        logger.critical('Bye')


class ShowMessage(QThread):
    """
    Show message with tool message.
    """
    def __init__(self, title, message):
        super(ShowMessage, self).__init__()
        self.title = title
        self.message = message

    def run(self):
        command = 'python3 ' + str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/tools/message.py --title "' + str(self.title) + '" --message "' + str(self.message) + '"'
        os.system(command)


#################
# Main Function #
#################
def main():
    read_args()
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
