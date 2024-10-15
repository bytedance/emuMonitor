# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import stat
import yaml
import copy
import getpass
import datetime
import logging

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, qApp, QTabWidget, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QMessageBox, QLineEdit, QComboBox, QHeaderView, QDateEdit, QFileDialog, QFormLayout, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QDate, pyqtSignal

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']))
from common import common, common_pyqt5, common_palladium
from config import config

os.environ['PYTHONUNBUFFERED'] = '1'
logger = common.get_logger(level=logging.WARNING)

# Solve some unexpected warning message.
if 'XDG_RUNTIME_DIR' not in os.environ:
    user = getpass.getuser()
    os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-' + str(user)

    if not os.path.exists(os.environ['XDG_RUNTIME_DIR']):
        os.makedirs(os.environ['XDG_RUNTIME_DIR'])

    os.chmod(os.environ['XDG_RUNTIME_DIR'], stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)


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
        self.first_open_flag = True
        self.current_palladium_dic = {}
        self.history_palladium_dic = {}
        self.history_palladium_path_dic = self.parse_db_path()

        # get default test server and test server host
        self.total_hardware_dic = common_palladium.get_palladium_host_info()
        self.hardware_dic = copy.deepcopy(self.total_hardware_dic)
        self.hardware_list = list(self.hardware_dic.keys())

        if hasattr(config, 'palladium_enable_cost_others_project'):
            self.enable_cost_others_project = config.palladium_enable_cost_others_project
        else:
            logger.error("Could not find the definition of zebu_enable_cost_others_project in config!")

        if hasattr(config, 'palladium_enable_use_default_cost_rate'):
            self.enable_use_default_cost_rate = config.palladium_enable_use_default_cost_rate
        else:
            logger.error("Could not find the definition of zebu_enable_use_default_cost_rate in config!")

        self.enable_utilization_detail = False
        self.total_project_list = []

        for hardware in self.hardware_dic:
            for project in self.hardware_dic[hardware]['project_list']:
                if project not in self.total_project_list:
                    self.total_project_list.append(project)

        if self.enable_cost_others_project:
            for hardware in self.hardware_dic:
                self.hardware_dic[hardware]['project_list'].append('others')
            self.total_project_list.append('others')

        self.label_dic = self.get_label_dic()
        self.selected_label = ''

        self.current_rack_list = ['ALL', ]
        self.current_cluster_list = ['ALL', ]
        self.current_logic_drawer_list = ['ALL', ]
        self.current_domain_list = ['ALL', ]

        self.history_rack_list = ['ALL', ]
        self.history_cluster_list = ['ALL', ]
        self.history_logic_drawer_list = ['ALL', ]
        self.history_domain_list = ['ALL', ]

        self.utilization_rack_list = ['ALL', ]
        self.utilization_logic_drawer_list = ['ALL', ]
        self.utilization_logic_drawer_list = ['ALL', ]
        self.utilization_domain_list = ['ALL', ]

        self.cost_rack_list = ['ALL', ]
        self.cost_cluster_list = ['ALL', ]
        self.cost_logic_drawer_list = ['ALL', ]
        self.cost_domain_list = ['ALL', ]

        self.init_ui()

        self.first_open_flag = False

    @staticmethod
    def get_label_dic():
        """
        get label information from local home path -> install path
        label_dic = {'hardware': <hardware>, 'test_server': <test_server>, 'test_server_host': <test_server_host>, 'domain_dic': <domain_dic>}
        """
        label_dic = {}

        # search install path
        install_label_path = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']), 'config/palladium/label/')

        if os.path.exists(install_label_path):
            for file in os.listdir(install_label_path):
                if my_match := re.match(r'^(\S+).config.yaml$', file):
                    label = my_match.group(1)
                    label_config_file = os.path.join(install_label_path, file)

                    with open(label_config_file, 'r') as cf:
                        info_dic = yaml.load(cf, Loader=yaml.FullLoader)
                        hardware = info_dic['hardware']
                        label_dic.setdefault(hardware, {})
                        label_dic[hardware][label] = info_dic

        # search usr home path
        usr_home_path = os.path.expanduser('~')
        label_config_path = os.path.join(usr_home_path, '.config/emuMonitor/label/')

        if os.path.exists(label_config_path):
            for file in os.listdir(label_config_path):
                if my_match := re.match(r'^(\S+).config.yaml$', file):
                    label = my_match.group(1)
                    label_config_file = os.path.join(label_config_path, file)

                    with open(label_config_file, 'r') as cf:
                        info_dic = yaml.load(cf, Loader=yaml.FullLoader)
                        hardware = info_dic['hardware']
                        label_dic.setdefault(hardware, {})
                        label_dic[hardware][label] = info_dic

        return label_dic

    @staticmethod
    def parse_db_path():
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
                                                    for day_time in os.listdir(day_path):
                                                        time_path = str(day_path) + '/' + str(day_time)

                                                        if os.path.isfile(time_path):
                                                            history_palladium_path_dic[hardware][emulator][year][month][day].setdefault(day_time, time_path)

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
        self.setWindowTitle('emuMonitor - Palladium')
        self.setWindowIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/monitor.ico'))
        self.resize(1111, 620)
        common_pyqt5.center_window(self)

    def gen_menubar(self):
        """
        Generate menubar.
        """
        self.menubar = self.menuBar()
        self.menubar.clear()

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

        file_menu = self.menubar.addMenu('File')
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

        enable_utilization_detail_action = QAction('Enable Utilization Detail', self, checkable=True)
        enable_utilization_detail_action.setChecked(self.enable_utilization_detail)
        enable_utilization_detail_action.triggered.connect(self.func_enable_utilization_detail)

        save_selected_as_label_action = QAction('Save Selected as Label', self)
        save_selected_as_label_action.triggered.connect(self.gen_save_label_window)

        setup_menu = self.menubar.addMenu('Setup')
        setup_menu.addAction(enable_use_default_cost_rate_action)
        setup_menu.addAction(enable_cost_others_project_action)
        setup_menu.addAction(enable_utilization_detail_action)
        setup_menu.addSeparator()
        setup_menu.addAction(save_selected_as_label_action)

        # Help
        version_action = QAction('Version', self)
        version_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/version.png'))
        version_action.triggered.connect(self.show_version)

        about_action = QAction('About palladiumMonitor', self)
        about_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/about.png'))
        about_action.triggered.connect(self.show_about)

        help_menu = self.menubar.addMenu('Help')
        help_menu.addAction(version_action)
        help_menu.addAction(about_action)

    def gen_save_label_window(self):
        """
        selected_info_dic = {'hardware':<hardware>, 'ip': <ip>,  'test_server': <test_server_path>, 'domain_dic': <domain_dic>
                             'domain': {'rack_list': <rack_list>, 'cluster_list': <cluster_list>,
                                        'logic_drawer_list': <logic_drawer_list>, 'domain_list': <domain_list>}}
        """
        tab_index = self.main_tab.currentIndex()
        label_info_dic = {}
        rack_list, cluster_list, logic_drawer_list, domain_list, hardware, domain_dic = [], [], [], [], '', {}

        if tab_index == 0:
            if self.current_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.current_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            rack_list = self.current_rack_list
            cluster_list = self.current_cluster_list
            logic_drawer_list = self.current_logic_drawer_list
            domain_list = self.current_domain_list
        elif tab_index == 1:
            if self.history_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.history_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            rack_list = self.history_rack_list
            cluster_list = self.history_cluster_list
            logic_drawer_list = self.history_logic_drawer_list
            domain_list = self.history_domain_list
        elif tab_index == 2:
            if self.utilization_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.utilization_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            rack_list = self.utilization_rack_list
            cluster_list = self.utilization_cluster_list
            logic_drawer_list = self.utilization_logic_drawer_list
            domain_list = self.utilization_domain_list
        elif tab_index == 3:
            if self.cost_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.cost_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            rack_list = self.cost_rack_list
            cluster_list = self.cost_cluster_list
            logic_drawer_list = self.cost_logic_drawer_list
            domain_list = self.cost_domain_list

        if hardware not in self.hardware_dic:
            logger.warning("Please select valid hardware first!")
            return

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.warning("Please check palladium information first!")
            return

        domain_dic = self.hardware_dic[hardware]['domain_dic']

        label_info_dic['domain_dic'] = domain_dic
        label_info_dic['hardware'] = hardware
        label_info_dic['rack_list'] = rack_list
        label_info_dic['cluster_list'] = cluster_list
        label_info_dic['logic_drawer_list'] = logic_drawer_list
        label_info_dic['domain_list'] = domain_list

        self.label_window = WindowForLabel(label_info_dic)
        self.label_window.save_signal.connect(self.save_label)
        self.label_window.show()

    def save_label(self):
        self.label_dic = self.get_label_dic()
        self.set_current_tab_tag_combo()
        self.set_history_tab_tag_combo()
        self.set_utilization_tab_tag_combo()
        self.set_cost_tab_tag_combo()

    def show_version(self):
        """
        Show palladiumMonitor version information.
        """
        version = 'V1.2'
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
        self.set_current_tab_hardware_combo(self.hardware_list)
        self.current_tab_hardware_combo.activated.connect(self.set_current_tab_host_line)
        self.current_tab_hardware_combo.activated.connect(self.set_current_tab_tag_combo)

        current_tab_host_label = QLabel('Host', self.current_tab_frame)
        current_tab_host_label.setStyleSheet("font-weight: bold;")
        current_tab_host_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_host_line = QLineEdit()
        self.set_current_tab_host_line()

        current_tab_tag_label = QLabel('Label', self.current_tab_frame)
        current_tab_tag_label.setStyleSheet("font-weight: bold;")
        current_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_tag_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_check_button = QPushButton('Check', self.current_tab_frame)
        current_tab_check_button.setStyleSheet("font-weight: bold;")
        current_tab_check_button.clicked.connect(self.check_current_palladium_info)

        current_tab_rack_label = QLabel('Rack', self.current_tab_frame)
        current_tab_rack_label.setStyleSheet("font-weight: bold;")
        current_tab_rack_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_rack_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_cluster_label = QLabel('Cluster', self.current_tab_frame)
        current_tab_cluster_label.setStyleSheet("font-weight: bold;")
        current_tab_cluster_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_cluster_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_logic_drawer_label = QLabel('Board', self.current_tab_frame)
        current_tab_logic_drawer_label.setStyleSheet("font-weight: bold;")
        current_tab_logic_drawer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_logic_drawer_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_domain_label = QLabel('Domain', self.current_tab_frame)
        current_tab_domain_label.setStyleSheet("font-weight: bold;")
        current_tab_domain_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_domain_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_owner_label = QLabel('Owner', self.current_tab_frame)
        current_tab_owner_label.setStyleSheet("font-weight: bold;")
        current_tab_owner_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_owner_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_pid_label = QLabel('PID', self.current_tab_frame)
        current_tab_pid_label.setStyleSheet("font-weight: bold;")
        current_tab_pid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_pid_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_tpod_label = QLabel('T-Pod', self.current_tab_frame)
        current_tab_tpod_label.setStyleSheet("font-weight: bold;")
        current_tab_tpod_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_tpod_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_design_label = QLabel('Design', self.current_tab_frame)
        current_tab_design_label.setStyleSheet("font-weight: bold;")
        current_tab_design_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_design_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        # self.current_tab_frame - Grid
        current_tab_frame_grid = QGridLayout()

        current_tab_frame_grid.addWidget(current_tab_hardware_label, 0, 0)
        current_tab_frame_grid.addWidget(self.current_tab_hardware_combo, 0, 1)
        current_tab_frame_grid.addWidget(current_tab_host_label, 0, 2)
        current_tab_frame_grid.addWidget(self.current_tab_host_line, 0, 3)
        current_tab_frame_grid.addWidget(current_tab_tag_label, 0, 4)
        current_tab_frame_grid.addWidget(self.current_tab_tag_combo, 0, 5)
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
        self.set_current_tab_tag_combo()

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
        hardware = self.current_tab_hardware_combo.currentText().strip()
        host = ''

        if hardware in self.hardware_dic:
            host = self.hardware_dic[hardware]['test_server_host']

        if host:
            self.current_tab_host_line.setText(host)

    def set_current_tab_tag_combo(self):
        """
        Set (initialize) self.current_tab_tag_combo..
        """
        hardware = self.current_tab_hardware_combo.currentText().strip()
        self.current_tab_tag_combo.clear()
        self.current_tab_tag_combo.addCheckBoxItem('None')

        if hardware in self.label_dic:
            for label in self.label_dic[hardware]:
                self.current_tab_tag_combo.addCheckBoxItem(label)

        self.current_tab_tag_combo.stateChangedconnect(self.set_current_tab_tag_list)
        self.current_tab_tag_combo.unselectAllItems()
        self.current_tab_tag_combo.selectItems(['None'])

        self.update_current_tab_frame(reset=True)

    def set_current_tab_tag_list(self):
        """
        Select tag selected list
        """
        hardware = self.current_tab_hardware_combo.currentText().strip()
        label_list = self.current_tab_tag_combo.qLineEdit.text().strip().split()

        if hardware not in self.label_dic:
            return

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s domain information, please check!" % hardware)
            return

        if not label_list:
            return

        rack_list, cluster_list, logic_drawer_list, domain_list = self.get_label_selected_list(hardware, label_list)

        self.current_tab_rack_combo.unselectAllItems()
        self.current_tab_cluster_combo.unselectAllItems()
        self.current_tab_logic_drawer_combo.unselectAllItems()
        self.current_tab_domain_combo.unselectAllItems()

        self.current_tab_rack_combo.selectItems(rack_list)
        self.current_tab_cluster_combo.selectItems(cluster_list)
        self.current_tab_logic_drawer_combo.selectItems(logic_drawer_list)
        self.current_tab_domain_combo.selectItems(domain_list)

    def get_label_selected_list(self, hardware, label_list):
        if hardware not in self.label_dic:
            return ['ALL', ], ['ALL', ], ['ALL', ], ['ALL', ]

        rack_set = set()
        cluster_set = set()
        logic_drawer_set = set()
        domain_set = set()

        for label in label_list:
            if label not in self.label_dic[hardware]:
                continue

            if label in self.label_dic[hardware]:
                if 'rack_list' in self.label_dic[hardware][label]:
                    rack_set.update(set(self.label_dic[hardware][label]['rack_list']))

                if 'cluster_list' in self.label_dic[hardware][label]:
                    cluster_set.update(set(self.label_dic[hardware][label]['cluster_list']))

                if 'logic_drawer_list' in self.label_dic[hardware][label]:
                    logic_drawer_set.update(self.label_dic[hardware][label]['logic_drawer_list'])

                if 'domain_list' in self.label_dic[hardware][label]:
                    domain_set.update(self.label_dic[hardware][label]['domain_list'])

        rack_list = list(rack_set) if rack_set else ['ALL', ]
        cluster_list = list(cluster_set) if cluster_set else ['ALL', ]
        logic_drawer_list = list(logic_drawer_set) if logic_drawer_set else ['ALL']
        domain_list = list(domain_set) if domain_set else ['ALL', ]

        rack_list, cluster_list, logic_drawer_list, domain_list = self.check_selected_list(hardware=hardware,
                                                                                           rack_list=rack_list,
                                                                                           cluster_list=cluster_list,
                                                                                           logic_drawer_list=logic_drawer_list,
                                                                                           domain_list=domain_list)

        return rack_list, cluster_list, logic_drawer_list, domain_list

    def check_selected_list(self, hardware: str = '', rack_list: list = [], cluster_list: list = [], logic_drawer_list: list = [], domain_list: list = []):
        new_rack_list, new_cluster_list, new_logic_drawer_list, new_domain_list = [], [], [], []
        error_info = 'Following selected is failed, please check!'
        error_flag = False

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.error("Could not find domain information is %s, please check!" % hardware)
            return

        if rack_list:
            error_info += '\nRack:'

            for rack in rack_list:
                if rack != 'ALL' and rack not in self.hardware_dic[hardware]['domain_dic']['rack_list']:
                    error_info += '%s ' % str(rack)
                    error_flag = True
                    continue

                new_rack_list.append(rack)

        if cluster_list:
            error_info += '\nCluster:'

            for cluster in cluster_list:
                if cluster != 'ALL' and cluster not in self.hardware_dic[hardware]['domain_dic']['cluster_list']:
                    error_info += '%s ' % str(cluster)
                    error_flag = True
                    continue

                new_cluster_list.append(cluster)

        if logic_drawer_list:
            error_info += '\nBoard:'

            for logic_drawer in logic_drawer_list:
                if logic_drawer != 'ALL' and logic_drawer not in self.hardware_dic[hardware]['domain_dic']['logic_drawer_list']:
                    error_info += '%s ' % str(logic_drawer)
                    error_flag = True
                    continue

                new_logic_drawer_list.append(logic_drawer)

        if domain_list:
            error_info += '\nDomain:'

            for domain in domain_list:
                if domain != 'ALL' and domain not in self.hardware_dic[hardware]['domain_dic']['domain_list']:
                    error_info += '%s ' % str(domain)
                    error_flag = True
                    continue

                new_domain_list.append(domain)

        if error_flag:
            common_pyqt5.Dialog(title='Selected Error',
                                info=error_info,
                                icon=QMessageBox.Warning)

        return new_rack_list, new_cluster_list, new_logic_drawer_list, new_domain_list

    def check_current_palladium_info(self):
        """
        Generate self.current_tab_table with hardware&host information.
        """
        hardware = self.current_tab_hardware_combo.currentText().strip()
        test_server = self.hardware_dic[hardware]['test_server']
        label_list = self.current_tab_tag_combo.qLineEdit.text().split()

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s domain information, please psample -H %s" % (hardware, hardware))
            return

        if label_list != ['None']:
            self.current_rack_list, self.current_cluster_list, self.current_logic_drawer_list, self.current_domain_list = self.get_label_selected_list(hardware, label_list)
        else:
            self.current_rack_list = ['ALL', ] if not self.current_tab_rack_combo.qLineEdit.text().strip().split() else self.current_tab_rack_combo.qLineEdit.text().strip().split()
            self.current_cluster_list = ['ALL', ] if not self.current_tab_cluster_combo.qLineEdit.text().strip().split() else self.current_tab_cluster_combo.qLineEdit.text().strip().split()
            self.current_logic_drawer_list = ['ALL', ] if not self.current_tab_logic_drawer_combo.qLineEdit.text().strip().split() else self.current_tab_logic_drawer_combo.qLineEdit.text().strip().split()
            self.current_domain_list = ['ALL', ] if not self.current_tab_domain_combo.qLineEdit.text().strip().split() else self.current_tab_domain_combo.qLineEdit.text().strip().split()

        self.current_owner_list = ['ALL', ] if not self.current_tab_owner_combo.qLineEdit.text().strip().split() else self.current_tab_owner_combo.qLineEdit.text().strip().split()
        self.current_pid_list = ['ALL', ] if not self.current_tab_pid_combo.qLineEdit.text().strip().split() else self.current_tab_pid_combo.qLineEdit.text().strip().split()
        self.current_tpod_list = ['ALL', ] if not self.current_tab_tpod_combo.qLineEdit.text().strip().split() else self.current_tab_tpod_combo.qLineEdit.text().strip().split()
        self.current_design_list = ['ALL', ] if not self.current_tab_design_combo.qLineEdit.text().strip().split() else self.current_tab_design_combo.qLineEdit.text().strip().split()

        if not hardware:
            my_show_message = common_pyqt5.ShowMessage('Warning', '"Hardware" is not specified.')
            my_show_message.start()
        else:
            host = self.total_hardware_dic[hardware]['test_server_host'] if not self.current_tab_host_line.text().strip() else self.current_tab_host_line.text().strip()

            if host:
                logger.critical("Loading current information, please wait ...")

                my_show_message = common_pyqt5.ShowMessage('Info', 'Loading palladium information, please wait a moment ...')
                my_show_message.start()

                # Get self.current_palladium_dic.
                test_server_info = common_palladium.get_test_server_info(hardware, test_server, host)
                self.current_palladium_dic = common_palladium.parse_test_server_info(test_server_info)

                my_show_message.terminate()

                if self.current_palladium_dic:
                    # Update QComboBox items.
                    self.current_palladium_dic = common_palladium.multifilter_palladium_dic(
                        self.current_palladium_dic,
                        specified_rack_list=self.current_rack_list,
                        specified_cluster_list=self.current_cluster_list,
                        specified_logic_drawer_list=self.current_logic_drawer_list,
                        specified_domain_list=self.current_domain_list,
                        specified_owner_list=self.current_owner_list,
                        specified_pid_list=self.current_pid_list,
                        specified_tpod_list=self.current_tpod_list,
                        specified_design_list=self.current_design_list,
                    )

                    self.update_current_tab_frame()

                else:
                    title = 'No valid information!'
                    info = 'Not find any valid palladium information. \n Please confirm that your current machine can access palladium emulator.\n'

                    if 'test_server_host' in self.hardware_dic[hardware] and self.hardware_dic[hardware]['test_server']:
                        info += 'You can try to login this machine %s to get palladium current information.\n' % str(self.hardware_dic[hardware]['test_server_host'])

                    common_pyqt5.Dialog(title=title, info=info)
                    logger.warning('Not find any valid palladium information.')

                # Update self.current_tab_table.
                self.gen_current_tab_table()

    def update_current_tab_frame(self, reset=False):
        """
        Update *_combo items on self.current_tab_frame..
        """
        hardware = self.current_tab_hardware_combo.currentText().strip()

        if hardware not in self.hardware_dic:
            return

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s domain information, please check!" % hardware)
            return

        if not self.current_palladium_dic:
            return

        if reset:
            self.current_rack_list = ['ALL', ]
            self.current_cluster_list = ['ALL', ]
            self.current_logic_drawer_list = ['ALL', ]
            self.current_domain_list = ['ALL', ]
            self.current_owner_list = ['ALL', ]
            self.current_pid_list = ['ALL', ]
            self.current_tpod_list = ['ALL', ]
            self.current_design_list = ['ALL', ]

        rack_list = self.hardware_dic[hardware]['domain_dic']['rack_list']

        # Update self.current_tab_rack_combo
        self.current_tab_rack_combo.clear()
        self.current_tab_rack_combo.addCheckBoxItem('ALL')
        self.current_tab_rack_combo.addCheckBoxItems(rack_list)
        self.current_tab_rack_combo.stateChangedconnect(self.current_rack_combo_change)

        self.current_tab_rack_combo.selectItems(self.current_rack_list)

        # Update self.current_tab_owner_combo
        self.current_tab_owner_combo.clear()
        self.current_tab_owner_combo.addCheckBoxItem('ALL')
        self.current_tab_owner_combo.addCheckBoxItems(self.current_palladium_dic['owner_list'])
        self.current_tab_owner_combo.selectItems(self.current_owner_list)

        # Update self.current_tab_pid_combo
        self.current_tab_pid_combo.clear()
        self.current_tab_pid_combo.addCheckBoxItem('ALL')
        self.current_tab_pid_combo.addCheckBoxItems(self.current_palladium_dic['pid_list'])
        self.current_tab_pid_combo.selectItems(self.current_pid_list)

        # Update self.current_tab_tpod_combo
        self.current_tab_tpod_combo.clear()
        self.current_tab_tpod_combo.addCheckBoxItem('ALL')
        self.current_tab_tpod_combo.addCheckBoxItems(self.current_palladium_dic['tpod_list'])
        self.current_tab_tpod_combo.selectItems(self.current_tpod_list)

        # Update self.current_tab_design_combo
        self.current_tab_design_combo.clear()
        self.current_tab_design_combo.addCheckBoxItem('ALL')
        self.current_tab_design_combo.addCheckBoxItems(self.current_palladium_dic['design_list'])
        self.current_tab_design_combo.selectItems(self.current_design_list)

    def current_rack_combo_change(self):
        hardware = self.current_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.current_tab_rack_combo.selectedItems().items()]
        self.current_rack_list = rack_list

        if 'ALL' in rack_list:
            cluster_list = self.total_hardware_dic[hardware]['domain_dic']['cluster_list']
        else:
            cluster_list = []

            for rack in rack_list:
                cluster_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack].keys())

        self.current_tab_cluster_combo.clear()
        self.current_tab_cluster_combo.addCheckBoxItem('ALL')
        self.current_tab_cluster_combo.addCheckBoxItems(sorted(cluster_list, key=lambda k: int(k)))
        self.current_tab_cluster_combo.stateChangedconnect(self.current_tab_cluster_combo_change)
        self.current_tab_cluster_combo.selectItems(self.current_cluster_list)

        if not self.current_tab_cluster_combo.selectedItems():
            self.current_cluster_list = ['ALL']
            self.current_tab_cluster_combo.selectItems(self.current_cluster_list)

    def current_tab_cluster_combo_change(self):
        hardware = self.current_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.current_tab_rack_combo.selectedItems().items()]
        cluster_list = [rack for _, rack in self.current_tab_cluster_combo.selectedItems().items()]
        self.current_cluster_list = cluster_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        board_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' in cluster_list or cluster in cluster_list:
                    board_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster])

        self.current_tab_logic_drawer_combo.clear()
        self.current_tab_logic_drawer_combo.addCheckBoxItem('ALL')
        self.current_tab_logic_drawer_combo.addCheckBoxItems(sorted(board_list, key=lambda k: int(k)))
        self.current_tab_logic_drawer_combo.stateChangedconnect(self.current_tab_board_combo_change)
        self.current_tab_logic_drawer_combo.selectItems(self.current_logic_drawer_list)

        if not self.current_tab_logic_drawer_combo.selectedItems():
            self.current_logic_drawer_list = ['ALL']
            self.current_tab_cluster_combo.selectItems(self.current_logic_drawer_list)

    def current_tab_board_combo_change(self):
        hardware = self.current_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.current_tab_rack_combo.selectedItems().items()]
        cluster_list = [cluster for _, cluster in self.current_tab_cluster_combo.selectedItems().items()]
        board_list = [board for _, board in self.current_tab_logic_drawer_combo.selectedItems().items()]
        self.current_logic_drawer_list = board_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        domain_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' not in cluster_list and cluster not in cluster_list:
                    continue

                for board in self.total_hardware_dic[hardware]['domain_dic'][rack][cluster]:
                    if 'ALL' in board_list or board in board_list:
                        domain_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster][board])

        self.current_tab_domain_combo.clear()
        self.current_tab_domain_combo.addCheckBoxItem('ALL')
        self.current_tab_domain_combo.addCheckBoxItems(sorted(domain_list, key=lambda k: float(k)))
        self.current_tab_domain_combo.stateChangedconnect(self.current_tab_domain_combo_change)
        self.current_tab_domain_combo.selectItems(self.current_domain_list)

        if not self.current_tab_domain_combo.selectedItems():
            self.current_domain_list = ['ALL']
            self.current_tab_domain_combo.selectItems(self.current_domain_list)

    def current_tab_domain_combo_change(self):
        domain_list = [domain for _, domain in self.current_tab_domain_combo.selectedItems().items()]
        self.current_tab_domain_list = domain_list

    def gen_palladium_info_table(self, palladium_info_table, palladium_dic):
        """
        Common function, generate specified table with specified palladium info (palladium_dic).
        """
        # palladium_info_table
        palladium_info_table.setShowGrid(True)
        palladium_info_table.setSortingEnabled(True)
        palladium_info_table.setColumnCount(0)
        palladium_info_table.setColumnCount(10)
        self.palladium_record_table_title_list = ['Rack', 'Cluster', 'Board', 'Domain', 'Owner', 'PID', 'T-Pod', 'Design', 'ElapTime', 'ReservedKey']
        palladium_info_table.setHorizontalHeaderLabels(self.palladium_record_table_title_list)

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
        self.history_tab_hardware_combo.activated.connect(self.set_history_tab_tag_combo)

        history_tab_emulator_label = QLabel('Emulator', self.history_tab_frame)
        history_tab_emulator_label.setStyleSheet("font-weight: bold;")
        history_tab_emulator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_emulator_combo = QComboBox(self.history_tab_frame)
        self.history_tab_emulator_combo.activated.connect(self.set_history_tab_year_combo)

        history_tab_tag_label = QLabel('Label', self.history_tab_frame)
        history_tab_tag_label.setStyleSheet("font-weight: bold;")
        history_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_tag_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        history_tab_check_button = QPushButton('Check', self.history_tab_frame)
        history_tab_check_button.setStyleSheet("font-weight: bold;")
        history_tab_check_button.clicked.connect(self.gen_history_tab_table)

        history_tab_rack_label = QLabel('Rack', self.history_tab_frame)
        history_tab_rack_label.setStyleSheet("font-weight: bold;")
        history_tab_rack_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_rack_combo = common_pyqt5.QComboCheckBox(self.history_tab_frame)

        history_tab_cluster_label = QLabel('Cluster', self.history_tab_frame)
        history_tab_cluster_label.setStyleSheet("font-weight: bold;")
        history_tab_cluster_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_cluster_combo = common_pyqt5.QComboCheckBox(self.history_tab_frame)

        history_tab_logic_drawer_label = QLabel('Board', self.history_tab_frame)
        history_tab_logic_drawer_label.setStyleSheet("font-weight: bold;")
        history_tab_logic_drawer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_logic_drawer_combo = common_pyqt5.QComboCheckBox(self.history_tab_frame)

        history_tab_domain_label = QLabel('Domain', self.history_tab_frame)
        history_tab_domain_label.setStyleSheet("font-weight: bold;")
        history_tab_domain_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_domain_combo = common_pyqt5.QComboCheckBox(self.history_tab_frame)

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
        history_tab_frame_grid.addWidget(history_tab_tag_label, 0, 4)
        history_tab_frame_grid.addWidget(self.history_tab_tag_combo, 0, 5)
        history_tab_frame_grid.addWidget(history_tab_check_button, 0, 7)
        history_tab_frame_grid.addWidget(history_tab_rack_label, 1, 0)
        history_tab_frame_grid.addWidget(self.history_tab_rack_combo, 1, 1)
        history_tab_frame_grid.addWidget(history_tab_cluster_label, 1, 2)
        history_tab_frame_grid.addWidget(self.history_tab_cluster_combo, 1, 3)
        history_tab_frame_grid.addWidget(history_tab_logic_drawer_label, 1, 4)
        history_tab_frame_grid.addWidget(self.history_tab_logic_drawer_combo, 1, 5)
        history_tab_frame_grid.addWidget(history_tab_domain_label, 1, 6)
        history_tab_frame_grid.addWidget(self.history_tab_domain_combo, 1, 7)
        history_tab_frame_grid.addWidget(history_tab_year_label, 2, 0)
        history_tab_frame_grid.addWidget(self.history_tab_year_combo, 2, 1)
        history_tab_frame_grid.addWidget(history_tab_month_label, 2, 2)
        history_tab_frame_grid.addWidget(self.history_tab_month_combo, 2, 3)
        history_tab_frame_grid.addWidget(history_tab_day_label, 2, 4)
        history_tab_frame_grid.addWidget(self.history_tab_day_combo, 2, 5)
        history_tab_frame_grid.addWidget(history_tab_time_label, 2, 6)
        history_tab_frame_grid.addWidget(self.history_tab_time_combo, 2, 7)

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

        for hardware in self.hardware_list:
            if hardware in self.history_palladium_path_dic.keys():
                self.history_tab_hardware_combo.addItem(hardware)

        self.set_history_tab_emulator_combo()

    def set_history_tab_tag_combo(self):
        """
        Set (initialize) self.history_tab_tag_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()
        self.history_tab_tag_combo.clear()
        self.history_tab_tag_combo.addCheckBoxItem('None')

        if hardware in self.label_dic:
            for label in self.label_dic[hardware]:
                self.history_tab_tag_combo.addCheckBoxItem(label)

        self.history_tab_tag_combo.stateChangedconnect(self.set_history_tab_tag_list)
        self.history_tab_tag_combo.selectItems(['None'])

        self.update_history_tab_frame(hardware, reset=True)

    def set_history_tab_tag_list(self):
        """
        Select tag selected list
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()
        label_list = self.history_tab_tag_combo.qLineEdit.text().strip().split()

        if hardware not in self.label_dic:
            return

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s domain information, please check!" % hardware)
            return

        if not label_list:
            return

        rack_list, cluster_list, logic_drawer_list, domain_list = self.get_label_selected_list(hardware, label_list)

        self.history_tab_rack_combo.unselectAllItems()
        self.history_tab_cluster_combo.unselectAllItems()
        self.history_tab_logic_drawer_combo.unselectAllItems()
        self.history_tab_domain_combo.unselectAllItems()

        self.history_tab_rack_combo.selectItems(rack_list)
        self.history_tab_cluster_combo.selectItems(cluster_list)
        self.history_tab_logic_drawer_combo.selectItems(logic_drawer_list)
        self.history_tab_domain_combo.selectItems(domain_list)

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
                    if year.isdigit():
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

                            for day_time in self.history_palladium_path_dic[hardware][emulator][year][month][day].keys():
                                self.history_tab_time_combo.addItem(day_time)

    def gen_history_tab_table(self):
        """
        Generate self.history_tab_table with filter information from self.history_tab_frame.
        """
        logger.critical("Loading history information, please wait...")

        hardware = self.history_tab_hardware_combo.currentText().strip()
        emulator = self.history_tab_emulator_combo.currentText().strip()
        year = self.history_tab_year_combo.currentText().strip()
        month = self.history_tab_month_combo.currentText().strip()
        day = self.history_tab_day_combo.currentText().strip()
        time = self.history_tab_time_combo.currentText().strip()

        self.history_rack_list = ['ALL', ] if not self.history_tab_rack_combo.qLineEdit.text().strip().split() else self.history_tab_rack_combo.qLineEdit.text().strip().split()
        self.history_cluster_list = ['ALL', ] if not self.history_tab_cluster_combo.qLineEdit.text().strip().split() else self.history_tab_cluster_combo.qLineEdit.text().strip().split()
        self.history_logic_drawer_list = ['ALL', ] if not self.history_tab_logic_drawer_combo.qLineEdit.text().strip().split() else self.history_tab_logic_drawer_combo.qLineEdit.text().strip().split()
        self.history_domain_list = ['ALL', ] if not self.history_tab_domain_combo.qLineEdit.text().strip().split() else self.history_tab_domain_combo.qLineEdit.text().strip().split()

        if hardware and emulator and year and month and day and time:
            time_file = self.history_palladium_path_dic[hardware][emulator][year][month][day][time]

            with open(time_file, 'rb') as TF:
                self.history_palladium_dic = yaml.load(TF, Loader=yaml.FullLoader)

            self.history_palladium_dic = common_palladium.multifilter_palladium_dic(
                self.history_palladium_dic,
                specified_rack_list=self.history_rack_list,
                specified_cluster_list=self.history_cluster_list,
                specified_logic_drawer_list=self.history_logic_drawer_list,
                specified_domain_list=self.history_domain_list,
                specified_owner_list=['ALL', ],
                specified_pid_list=['ALL', ],
                specified_tpod_list=['ALL', ],
                specified_design_list=['ALL', ],
            )

            self.update_history_tab_frame(hardware)

            self.gen_palladium_info_table(self.history_tab_table, self.history_palladium_dic)

    def update_history_tab_frame(self, hardware, reset=False):
        if hardware not in self.hardware_dic or 'domain_dic' not in self.hardware_dic[hardware]:
            return

        rack_list = self.hardware_dic[hardware]['domain_dic']['rack_list']

        # Update self.current_tab_rack_combo
        self.history_tab_rack_combo.clear()
        self.history_tab_rack_combo.addCheckBoxItem('ALL')
        self.history_tab_rack_combo.addCheckBoxItems(rack_list)
        self.history_tab_rack_combo.stateChangedconnect(self.history_rack_combo_change)

        if reset:
            self.history_rack_list = ['ALL']
            self.history_cluster_list = ['ALL']
            self.history_logic_drawer_list = ['ALL']
            self.history_domain_list = ['ALL']

        self.history_tab_rack_combo.selectItems(self.history_rack_list)

    def history_rack_combo_change(self):
        hardware = self.history_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.history_tab_rack_combo.selectedItems().items()]
        self.history_rack_list = rack_list

        if 'ALL' in rack_list:
            cluster_list = self.total_hardware_dic[hardware]['domain_dic']['cluster_list']
        else:
            cluster_list = []

            for rack in rack_list:
                cluster_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack].keys())

        self.history_tab_cluster_combo.clear()
        self.history_tab_cluster_combo.addCheckBoxItem('ALL')
        self.history_tab_cluster_combo.addCheckBoxItems(sorted(cluster_list, key=lambda k: int(k)))
        self.history_tab_cluster_combo.stateChangedconnect(self.history_tab_cluster_combo_change)
        self.history_tab_cluster_combo.selectItems(self.history_cluster_list)

        if not self.history_tab_cluster_combo.selectedItems():
            self.history_cluster_list = ['ALL']
            self.history_tab_cluster_combo.selectItems(self.history_cluster_list)

    def history_tab_cluster_combo_change(self):
        hardware = self.history_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.history_tab_rack_combo.selectedItems().items()]
        cluster_list = [rack for _, rack in self.history_tab_cluster_combo.selectedItems().items()]
        self.history_cluster_list = cluster_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        board_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' in cluster_list or cluster in cluster_list:
                    board_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster])

        self.history_tab_logic_drawer_combo.clear()
        self.history_tab_logic_drawer_combo.addCheckBoxItem('ALL')
        self.history_tab_logic_drawer_combo.addCheckBoxItems(sorted(board_list, key=lambda k: int(k)))
        self.history_tab_logic_drawer_combo.stateChangedconnect(self.history_tab_board_combo_change)
        self.history_tab_logic_drawer_combo.selectItems(self.history_logic_drawer_list)

        if not self.history_tab_logic_drawer_combo.selectedItems():
            self.history_logic_drawer_list = ['ALL']
            self.history_tab_logic_drawer_combo.selectItems(self.history_logic_drawer_list)

    def history_tab_board_combo_change(self):
        hardware = self.history_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.history_tab_rack_combo.selectedItems().items()]
        cluster_list = [cluster for _, cluster in self.history_tab_cluster_combo.selectedItems().items()]
        board_list = [board for _, board in self.history_tab_logic_drawer_combo.selectedItems().items()]
        self.history_logic_drawer_list = board_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        domain_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' not in cluster_list and cluster not in cluster_list:
                    continue

                for board in self.total_hardware_dic[hardware]['domain_dic'][rack][cluster]:
                    if 'ALL' in board_list or board in board_list:
                        domain_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster][board])

        self.history_tab_domain_combo.clear()
        self.history_tab_domain_combo.addCheckBoxItem('ALL')
        self.history_tab_domain_combo.addCheckBoxItems(sorted(domain_list, key=lambda k: float(k)))
        self.history_tab_domain_combo.stateChangedconnect(self.history_tab_domain_combo_change)
        self.history_tab_domain_combo.selectItems(self.history_domain_list)

        if not self.history_tab_domain_combo.selectedItems():
            self.history_domain_list = ['ALL']
            self.history_tab_domain_combo.selectItems(self.history_domain_list)

    def history_tab_domain_combo_change(self):
        domain_list = [domain for _, domain in self.history_tab_domain_combo.selectedItems().items()]
        self.history_tab_domain_list = domain_list

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
        self.utilization_tab_hardware_combo.activated.connect(self.set_utilization_tab_tag_combo)

        utilization_tab_emulator_label = QLabel('Emulator', self.utilization_tab_frame0)
        utilization_tab_emulator_label.setStyleSheet("font-weight: bold;")
        utilization_tab_emulator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_emulator_combo = QComboBox(self.utilization_tab_frame0)

        utilization_tab_start_date_label = QLabel('Start_Date', self.utilization_tab_frame0)
        utilization_tab_start_date_label.setStyleSheet("font-weight: bold;")
        utilization_tab_start_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_start_date_edit = QDateEdit(self.utilization_tab_frame0)
        self.utilization_tab_start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.utilization_tab_start_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.utilization_tab_start_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.utilization_tab_start_date_edit.setCalendarPopup(True)
        self.utilization_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))

        utilization_tab_end_date_label = QLabel('End_Date', self.utilization_tab_frame0)
        utilization_tab_end_date_label.setStyleSheet("font-weight: bold;")
        utilization_tab_end_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_end_date_edit = QDateEdit(self.utilization_tab_frame0)
        self.utilization_tab_end_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.utilization_tab_end_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.utilization_tab_end_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.utilization_tab_end_date_edit.setCalendarPopup(True)
        self.utilization_tab_end_date_edit.setDate(QDate.currentDate())

        utilization_tab_tag_label = QLabel('Label', self.utilization_tab_frame0)
        utilization_tab_tag_label.setStyleSheet("font-weight: bold;")
        utilization_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_tag_combo = common_pyqt5.QComboCheckBox(self.utilization_tab_frame0)
        self.set_utilization_tab_tag_combo()

        utilization_tab_rack_label = QLabel('Rack', self.utilization_tab_frame0)
        utilization_tab_rack_label.setStyleSheet("font-weight: bold;")
        utilization_tab_rack_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_rack_combo = common_pyqt5.QComboCheckBox(self.utilization_tab_frame0)

        utilization_tab_cluster_label = QLabel('Cluster', self.utilization_tab_frame0)
        utilization_tab_cluster_label.setStyleSheet("font-weight: bold;")
        utilization_tab_cluster_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_cluster_combo = common_pyqt5.QComboCheckBox(self.utilization_tab_frame0)

        utilization_tab_logic_drawer_label = QLabel('Board', self.utilization_tab_frame0)
        utilization_tab_logic_drawer_label.setStyleSheet("font-weight: bold;")
        utilization_tab_logic_drawer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_logic_drawer_combo = common_pyqt5.QComboCheckBox(self.utilization_tab_frame0)

        utilization_tab_domain_label = QLabel('Domain', self.utilization_tab_frame0)
        utilization_tab_domain_label.setStyleSheet("font-weight: bold;")
        utilization_tab_domain_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_domain_combo = common_pyqt5.QComboCheckBox(self.utilization_tab_frame0)

        utilization_tab_check_label = QLabel('', self.utilization_tab_frame0)
        utilization_tab_check_button = QPushButton('Check', self.utilization_tab_frame0)
        utilization_tab_check_button.setStyleSheet("font-weight: bold;")
        utilization_tab_check_button.clicked.connect(self.update_utilization_tab_frame1)

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
        utilization_tab_frame0_grid.addWidget(utilization_tab_check_label, 0, 8)
        utilization_tab_frame0_grid.addWidget(utilization_tab_check_button, 0, 9)
        utilization_tab_frame0_grid.addWidget(utilization_tab_rack_label, 1, 0)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_rack_combo, 1, 1)
        utilization_tab_frame0_grid.addWidget(utilization_tab_cluster_label, 1, 2)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_cluster_combo, 1, 3)
        utilization_tab_frame0_grid.addWidget(utilization_tab_logic_drawer_label, 1, 4)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_logic_drawer_combo, 1, 5)
        utilization_tab_frame0_grid.addWidget(utilization_tab_domain_label, 1, 6)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_domain_combo, 1, 7)
        utilization_tab_frame0_grid.addWidget(utilization_tab_tag_label, 1, 8)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_tag_combo, 1, 9)

        utilization_tab_frame0_grid.setColumnStretch(0, 1)
        utilization_tab_frame0_grid.setColumnStretch(1, 1)
        utilization_tab_frame0_grid.setColumnStretch(2, 1)
        utilization_tab_frame0_grid.setColumnStretch(3, 1)
        utilization_tab_frame0_grid.setColumnStretch(4, 1)
        utilization_tab_frame0_grid.setColumnStretch(5, 1)
        utilization_tab_frame0_grid.setColumnStretch(6, 1)
        utilization_tab_frame0_grid.setColumnStretch(7, 1)
        utilization_tab_frame0_grid.setColumnStretch(8, 1)
        utilization_tab_frame0_grid.setColumnStretch(9, 2)

        self.utilization_tab_frame0.setLayout(utilization_tab_frame0_grid)

        # Init self.utilization_tab_frame0.
        self.set_utilization_tab_hardware_combo()
        self.update_utilization_tab_frame1()

    def set_utilization_tab_hardware_combo(self):
        """
        Set (initialize) self.utilization_tab_hardware_combo.
        """
        self.utilization_tab_hardware_combo.clear()
        self.utilization_tab_hardware_combo.addItem('')

        for hardware in self.hardware_list:
            if hardware in self.history_palladium_path_dic.keys():
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

    def set_utilization_tab_tag_combo(self):
        """
        Set (initialize) self.utilization_tab_tag_combo.
        """
        hardware = self.utilization_tab_hardware_combo.currentText().strip()
        self.utilization_tab_tag_combo.clear()
        self.utilization_tab_tag_combo.addCheckBoxItem('None')

        if hardware in self.label_dic:
            for label in self.label_dic[hardware]:
                self.utilization_tab_tag_combo.addCheckBoxItem(label)

        self.utilization_tab_tag_combo.stateChangedconnect(self.set_utilization_tab_tag_list)
        self.utilization_tab_tag_combo.selectItems(['None'])

        self.update_utilization_tab_frame0(hardware, reset=True)

    def set_utilization_tab_tag_list(self):
        """
        Select tag selected list
        """
        hardware = self.utilization_tab_hardware_combo.currentText().strip()
        label_list = self.utilization_tab_tag_combo.qLineEdit.text().strip().split()

        if hardware not in self.label_dic:
            return

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s domain information, please check!" % hardware)
            return

        if not label_list:
            return

        rack_list, cluster_list, logic_drawer_list, domain_list = self.get_label_selected_list(hardware, label_list)

        self.utilization_tab_rack_combo.unselectAllItems()
        self.utilization_tab_cluster_combo.unselectAllItems()
        self.utilization_tab_logic_drawer_combo.unselectAllItems()
        self.utilization_tab_domain_combo.unselectAllItems()

        self.utilization_tab_rack_combo.selectItems(rack_list)
        self.utilization_tab_cluster_combo.selectItems(cluster_list)
        self.utilization_tab_logic_drawer_combo.selectItems(logic_drawer_list)
        self.utilization_tab_domain_combo.selectItems(domain_list)

    def get_utilization_dic(self, hardware, emulator, start_date, end_date):
        """
        Get utilization_dic, with "date - utilization" information.
        """
        utilization_file = str(config.db_path) + '/' + str(hardware) + '/' + str(emulator) + '/utilization'
        start_date_utc = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date_utc = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        utilization_dic = {}

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
                            full_utilization_dic[date].setdefault(time, float(utilization) * 100)

            if self.enable_utilization_detail:
                for date in full_utilization_dic.keys():
                    for timestamp in full_utilization_dic[date].keys():
                        utilization_dic['%s-%s' % (date, timestamp)] = full_utilization_dic[date][timestamp]
            else:
                utilization_dic = {(start_date_utc + datetime.timedelta(days=d)).strftime('%Y%m%d'): 0 for d in range((end_date_utc - start_date_utc).days)}

                for date in full_utilization_dic.keys():
                    utilization = int(sum(full_utilization_dic[date].values()) / len(full_utilization_dic[date]))
                    utilization_dic[date] = utilization

        return utilization_dic

    @staticmethod
    def is_file_writing(file_path):
        init_mtime = os.path.getmtime(file_path)
        time.sleep(0.1)
        current_mtime = os.path.getmtime(file_path)
        return init_mtime != current_mtime

    def get_domain_utilization_dic(self, hardware, emulator, start_date, end_date):
        """
        Get detail utilization_dic, with "date - utilization" information.
        """
        start_date_utc = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date_utc = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        utilization_dic = {(start_date_utc + datetime.timedelta(days=d)).strftime('%Y%m%d'): 0 for d in range((end_date_utc - start_date_utc).days)}
        utilization_dir = str(config.db_path) + '/' + str(hardware) + '/' + str(emulator) + '/detail'

        if not os.path.exists(utilization_dir):
            logger.error("Could not find domain based utilization information, please check db path!")
        else:
            month_num = (end_date_utc.year - start_date_utc.year) * 12 + (end_date_utc.month - start_date_utc.month)

            for month in range(start_date_utc.month - 1, start_date_utc.month + month_num):
                current_year = start_date_utc.year + month // 12
                current_month = month % 12 + 1

                current_utilization_file = os.path.join(utilization_dir, '%s.%s.utilization' % (str(current_year), str(current_month).zfill(2)))

                if not os.path.exists(current_utilization_file):
                    continue

                while self.is_file_writing(current_utilization_file):
                    time.sleep(1)

                if not os.path.exists(current_utilization_file):
                    continue

                with open(current_utilization_file, 'r') as uf:
                    try:
                        current_utilization_dic = yaml.load(uf, Loader=yaml.FullLoader)
                    except Exception as error:
                        logger.error(str(error))
                        logger.error('Error occur when reading utilization file {}'.format(current_utilization_dic))
                        return utilization_dic

                for current_date in current_utilization_dic:
                    current_date_utc = datetime.datetime.strptime(current_date, '%Y-%m-%d')
                    current_date_format = current_date_utc.strftime("%Y%m%d")

                    if start_date_utc > current_date_utc or current_date_utc > end_date_utc:
                        continue
                    else:
                        utilization_sampling = 0
                        utilization_used = 0

                        for rack in current_utilization_dic[current_date]:
                            if rack not in self.utilization_rack_list and 'ALL' not in self.utilization_rack_list:
                                continue

                            for cluster in current_utilization_dic[current_date][rack]:
                                if cluster not in self.utilization_cluster_list and 'ALL' not in self.utilization_cluster_list:
                                    continue

                                for logic_drawer in current_utilization_dic[current_date][rack][cluster]:
                                    if logic_drawer not in self.utilization_logic_drawer_list and 'ALL' not in self.utilization_logic_drawer_list:
                                        continue

                                    for domain in current_utilization_dic[current_date][rack][cluster][logic_drawer]:
                                        if domain not in self.utilization_domain_list and 'ALL' not in self.utilization_domain_list:
                                            continue

                                        utilization_sampling += current_utilization_dic[current_date][rack][cluster][logic_drawer][domain]['sampling']
                                        utilization_used += current_utilization_dic[current_date][rack][cluster][logic_drawer][domain]['used']

                    if utilization_sampling != 0:
                        utilization = round((utilization_used / utilization_sampling) * 100, 2)
                    else:
                        utilization = 0

                    utilization_dic[current_date_format] = utilization

        return utilization_dic

    def gen_utilization_tab_frame1(self):
        """
        Generate empty self.utilization_tab_frame1.
        """
        # self.utilization_tab_frame1.
        self.utilization_figure_canvas = FigureCanvas()
        self.utilization_navigation_toolbar = common_pyqt5.NavigationToolbar2QT(self.utilization_figure_canvas, self, x_is_date=True)

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

        self.utilization_rack_list = ['ALL', ] if not self.utilization_tab_rack_combo.qLineEdit.text().strip().split() else self.utilization_tab_rack_combo.qLineEdit.text().strip().split()
        self.utilization_cluster_list = ['ALL', ] if not self.utilization_tab_cluster_combo.qLineEdit.text().strip().split() else self.utilization_tab_cluster_combo.qLineEdit.text().strip().split()
        self.utilization_logic_drawer_list = ['ALL', ] if not self.utilization_tab_logic_drawer_combo.qLineEdit.text().strip().split() else self.utilization_tab_logic_drawer_combo.qLineEdit.text().strip().split()
        self.utilization_domain_list = ['ALL', ] if not self.utilization_tab_domain_combo.qLineEdit.text().strip().split() else self.utilization_tab_domain_combo.qLineEdit.text().strip().split()

        self.update_utilization_tab_frame0(hardware=hardware)

        logger.critical("Loading utilization information, please wait ...")

        if not self.first_open_flag:
            my_show_message = common_pyqt5.ShowMessage('Info', 'Loading utilization information, please wait a moment ...')
            my_show_message.start()

        if hardware and emulator and start_date and end_date:
            if 'ALL' in self.utilization_rack_list and 'ALL' in self.utilization_cluster_list and 'ALL' in self.utilization_logic_drawer_list and 'ALL' in self.utilization_domain_list:
                utilization_dic = self.get_utilization_dic(hardware, emulator, start_date, end_date)
            else:
                if not self.enable_utilization_detail:
                    utilization_dic = self.get_domain_utilization_dic(hardware, emulator, start_date, end_date)
                else:
                    logger.warning('Could not generate detail utilization information based on domain!')
                    self.utilization_tab_rack_combo.unselectAllItems()
                    self.utilization_tab_rack_combo.selectItems(['ALL'])
                    self.utilization_tab_cluster_combo.unselectAllItems()
                    self.utilization_tab_cluster_combo.selectItems(['ALL'])
                    self.utilization_tab_logic_drawer_combo.unselectAllItems()
                    self.utilization_tab_logic_drawer_combo.selectItems(['ALL'])
                    self.utilization_tab_domain_combo.unselectAllItems()
                    self.utilization_tab_domain_combo.selectItems(['ALL'])
                    self.utilization_tab_tag_combo.unselectAllItems()
                    self.utilization_tab_tag_combo.selectItems(['None'])

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
                    if self.enable_utilization_detail:
                        date_list[i] = datetime.datetime.strptime(date_list[i], '%Y%m%d-%H%M%S')
                    else:
                        date_list[i] = datetime.datetime.strptime(date_list[i], '%Y%m%d')

                av_utilization = round((sum(utilization_list) / len(utilization_list)), 1)

                self.draw_utilization_curve(fig, av_utilization, date_list, utilization_list)

        if not self.first_open_flag:
            my_show_message.terminate()

    def update_utilization_tab_frame0(self, hardware, reset=False):
        domain_dic = {}

        if hardware in self.hardware_dic:
            if 'domain_dic' not in self.hardware_dic[hardware]:
                return

            domain_dic = self.hardware_dic[hardware]['domain_dic']

        if not domain_dic:
            return

        if reset:
            self.utilization_rack_list = ['ALL', ]
            self.utilization_cluster_list = ['ALL', ]
            self.utilization_logic_drawer_list = ['ALL', ]
            self.utilization_domain_list = ['ALL', ]

        # Update self.current_tab_rack_combo
        self.utilization_tab_rack_combo.clear()
        self.utilization_tab_rack_combo.addCheckBoxItem('ALL')
        self.utilization_tab_rack_combo.addCheckBoxItems(domain_dic['rack_list'])
        self.utilization_tab_rack_combo.stateChangedconnect(self.utilization_tab_rack_combo_change)

        self.utilization_tab_rack_combo.selectItems(self.utilization_rack_list)

    def utilization_tab_rack_combo_change(self):
        hardware = self.utilization_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.utilization_tab_rack_combo.selectedItems().items()]
        self.utilization_rack_list = rack_list

        if 'ALL' in rack_list:
            cluster_list = self.total_hardware_dic[hardware]['domain_dic']['cluster_list']
        else:
            cluster_list = []

            for rack in rack_list:
                cluster_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack].keys())

        self.utilization_tab_cluster_combo.clear()
        self.utilization_tab_cluster_combo.addCheckBoxItem('ALL')
        self.utilization_tab_cluster_combo.addCheckBoxItems(sorted(cluster_list, key=lambda k: int(k)))
        self.utilization_tab_cluster_combo.stateChangedconnect(self.utilization_tab_cluster_combo_change)
        self.utilization_tab_cluster_combo.selectItems(self.utilization_cluster_list)

        if not self.utilization_tab_cluster_combo.selectedItems():
            self.utilization_cluster_list = ['ALL']
            self.utilization_tab_cluster_combo.selectItems(self.utilization_cluster_list)

    def utilization_tab_cluster_combo_change(self):
        hardware = self.utilization_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.utilization_tab_rack_combo.selectedItems().items()]
        cluster_list = [rack for _, rack in self.utilization_tab_cluster_combo.selectedItems().items()]
        self.utilization_cluster_list = cluster_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        board_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' in cluster_list or cluster in cluster_list:
                    board_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster])

        self.utilization_tab_logic_drawer_combo.clear()
        self.utilization_tab_logic_drawer_combo.addCheckBoxItem('ALL')
        self.utilization_tab_logic_drawer_combo.addCheckBoxItems(sorted(board_list, key=lambda k: int(k)))
        self.utilization_tab_logic_drawer_combo.stateChangedconnect(self.utilization_tab_board_combo_change)
        self.utilization_tab_logic_drawer_combo.selectItems(self.utilization_logic_drawer_list)

        if not self.utilization_tab_logic_drawer_combo.selectedItems():
            self.utilization_logic_drawer_list = ['ALL']
            self.utilization_tab_logic_drawer_combo.selectItems(self.utilization_logic_drawer_list)

    def utilization_tab_board_combo_change(self):
        hardware = self.utilization_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.utilization_tab_rack_combo.selectedItems().items()]
        cluster_list = [cluster for _, cluster in self.utilization_tab_cluster_combo.selectedItems().items()]
        board_list = [board for _, board in self.utilization_tab_logic_drawer_combo.selectedItems().items()]
        self.utilization_logic_drawer_list = board_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        domain_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' not in cluster_list and cluster not in cluster_list:
                    continue

                for board in self.total_hardware_dic[hardware]['domain_dic'][rack][cluster]:
                    if 'ALL' in board_list or board in board_list:
                        domain_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster][board])

        self.utilization_tab_domain_combo.clear()
        self.utilization_tab_domain_combo.addCheckBoxItem('ALL')
        self.utilization_tab_domain_combo.addCheckBoxItems(sorted(domain_list, key=lambda k: float(k)))
        self.utilization_tab_domain_combo.stateChangedconnect(self.utilization_tab_domain_combo_change)
        self.utilization_tab_domain_combo.selectItems(self.utilization_domain_list)

        if not self.utilization_tab_domain_combo.selectedItems():
            self.utilization_domain_list = ['ALL']
            self.utilization_tab_domain_combo.selectItems(self.utilization_domain_list)

    def utilization_tab_domain_combo_change(self):
        domain_list = [domain for _, domain in self.utilization_tab_domain_combo.selectedItems().items()]
        self.utilization_tab_domain_list = domain_list

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
        self.cost_tab_hardware_combo.activated.connect(self.set_cost_tab_tag_combo)

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

        cost_tab_tag_label = QLabel('Label', self.cost_tab_frame0)
        cost_tab_tag_label.setStyleSheet("font-weight: bold;")
        cost_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_tag_combo = common_pyqt5.QComboCheckBox(self.cost_tab_frame0)
        self.cost_tab_tag_combo.activated.connect(self.set_cost_tab_tag_list)

        cost_tab_rack_label = QLabel('Rack', self.cost_tab_frame0)
        cost_tab_rack_label.setStyleSheet("font-weight: bold;")
        cost_tab_rack_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_rack_combo = common_pyqt5.QComboCheckBox(self.cost_tab_frame0)

        cost_tab_cluster_label = QLabel('Cluster', self.cost_tab_frame0)
        cost_tab_cluster_label.setStyleSheet("font-weight: bold;")
        cost_tab_cluster_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_cluster_combo = common_pyqt5.QComboCheckBox(self.cost_tab_frame0)

        cost_tab_logic_drawer_label = QLabel('Board', self.cost_tab_frame0)
        cost_tab_logic_drawer_label.setStyleSheet("font-weight: bold;")
        cost_tab_logic_drawer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_logic_drawer_combo = common_pyqt5.QComboCheckBox(self.cost_tab_frame0)

        cost_tab_domain_label = QLabel('Domain', self.cost_tab_frame0)
        cost_tab_domain_label.setStyleSheet("font-weight: bold;")
        cost_tab_domain_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_domain_combo = common_pyqt5.QComboCheckBox(self.cost_tab_frame0)

        cost_tab_check_label = QLabel('', self.cost_tab_frame0)
        cost_tab_check_button = QPushButton('Check', self.cost_tab_frame0)
        cost_tab_check_button.setStyleSheet("font-weight: bold;")
        cost_tab_check_button.clicked.connect(self.gen_cost_tab_table)

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
        cost_tab_frame0_grid.addWidget(cost_tab_check_label, 0, 8)
        cost_tab_frame0_grid.addWidget(cost_tab_check_button, 0, 9)
        cost_tab_frame0_grid.addWidget(cost_tab_rack_label, 1, 0)
        cost_tab_frame0_grid.addWidget(self.cost_tab_rack_combo, 1, 1)
        cost_tab_frame0_grid.addWidget(cost_tab_cluster_label, 1, 2)
        cost_tab_frame0_grid.addWidget(self.cost_tab_cluster_combo, 1, 3)
        cost_tab_frame0_grid.addWidget(cost_tab_logic_drawer_label, 1, 4)
        cost_tab_frame0_grid.addWidget(self.cost_tab_logic_drawer_combo, 1, 5)
        cost_tab_frame0_grid.addWidget(cost_tab_domain_label, 1, 6)
        cost_tab_frame0_grid.addWidget(self.cost_tab_domain_combo, 1, 7)
        cost_tab_frame0_grid.addWidget(cost_tab_tag_label, 1, 8)
        cost_tab_frame0_grid.addWidget(self.cost_tab_tag_combo, 1, 9)

        cost_tab_frame0_grid.setColumnStretch(0, 1)
        cost_tab_frame0_grid.setColumnStretch(1, 1)
        cost_tab_frame0_grid.setColumnStretch(2, 1)
        cost_tab_frame0_grid.setColumnStretch(3, 1)
        cost_tab_frame0_grid.setColumnStretch(4, 1)
        cost_tab_frame0_grid.setColumnStretch(5, 1)
        cost_tab_frame0_grid.setColumnStretch(6, 1)
        cost_tab_frame0_grid.setColumnStretch(7, 1)
        cost_tab_frame0_grid.setColumnStretch(8, 1)
        cost_tab_frame0_grid.setColumnStretch(9, 1)

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

        if not self.first_open_flag:
            my_show_message = common_pyqt5.ShowMessage('Info', 'Loading cost information, please wait a moment ...')
            my_show_message.start()

        begin_date = self.cost_tab_start_date_edit.date().toPyDate()
        end_date = self.cost_tab_end_date_edit.date().toPyDate()
        day_inteval = (end_date - begin_date).days

        selected_hardware = self.cost_tab_hardware_combo.currentText().strip()
        selected_emulator = self.cost_tab_emulator_combo.currentText().strip()

        self.cost_rack_list = ['ALL', ] if not self.cost_tab_rack_combo.qLineEdit.text().strip().split() else self.cost_tab_rack_combo.qLineEdit.text().strip().split()
        self.cost_cluster_list = ['ALL', ] if not self.cost_tab_cluster_combo.qLineEdit.text().strip().split() else self.cost_tab_cluster_combo.qLineEdit.text().strip().split()
        self.cost_logic_drawer_list = ['ALL', ] if not self.cost_tab_logic_drawer_combo.qLineEdit.text().strip().split() else self.cost_tab_logic_drawer_combo.qLineEdit.text().strip().split()
        self.cost_domain_list = ['ALL', ] if not self.cost_tab_domain_combo.qLineEdit.text().strip().split() else self.cost_tab_domain_combo.qLineEdit.text().strip().split()

        self.update_cost_tab_frame0(hardware=selected_hardware)

        if 'ALL' not in self.cost_rack_list or 'ALL' not in self.cost_cluster_list or 'ALL' not in self.cost_logic_drawer_list or 'ALL' not in self.cost_domain_list:
            if 'ALL' != selected_hardware:
                cost_dic = self.get_domain_cost_dic(begin_date, end_date, selected_hardware, emulator=selected_emulator)

                if not self.first_open_flag:
                    my_show_message.terminate()

                return cost_dic
            else:
                self.cost_rack_list = ['ALL', ]
                self.cost_cluster_list = ['ALL', ]
                self.cost_logic_drawer_list = ['ALL', ]
                self.cost_domain_list = ['ALL', ]
                self.update_cost_tab_frame0(hardware=selected_hardware)

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

        if not self.first_open_flag:
            my_show_message.terminate()

        return cost_dic

    def get_domain_cost_dic(self, start_date_utc, end_date_utc, hardware='ALL', emulator='ALL'):
        """
        Get domain based cost dict
        """
        cost_dic = {}
        cost_dic.setdefault(hardware, {})
        cost_dic[hardware].setdefault(emulator, {})

        cost_dir = str(config.db_path) + '/' + str(hardware) + '/' + str(emulator) + '/detail'

        if not os.path.exists(cost_dir):
            logger.error("Could not find domain based cost information, please check db path!")
        else:
            month_num = (end_date_utc.year - start_date_utc.year) * 12 + (end_date_utc.month - start_date_utc.month)

            for month in range(start_date_utc.month - 1, start_date_utc.month + month_num):
                current_year = start_date_utc.year + month // 12
                current_month = month % 12 + 1

                current_cost_file = os.path.join(cost_dir, '%s.%s.cost' % (str(current_year), str(current_month).zfill(2)))

                if not os.path.exists(current_cost_file):
                    continue

                with open(current_cost_file, 'r') as uf:
                    current_cost_dic = yaml.load(uf, Loader=yaml.FullLoader)

                for current_date in current_cost_dic:
                    current_date_utc = datetime.datetime.strptime(current_date, '%Y-%m-%d').date()

                    if start_date_utc <= current_date_utc <= end_date_utc:
                        for rack in current_cost_dic[current_date]:
                            if rack not in self.cost_rack_list and 'ALL' not in self.cost_rack_list:
                                continue

                            for cluster in current_cost_dic[current_date][rack]:
                                if cluster not in self.cost_cluster_list and 'ALL' not in self.cost_cluster_list:
                                    continue

                                for logic_drwer in current_cost_dic[current_date][rack][cluster]:
                                    if logic_drwer not in self.cost_logic_drawer_list and 'ALL' not in self.cost_logic_drawer_list:
                                        continue

                                    for domain in current_cost_dic[current_date][rack][cluster][logic_drwer]:
                                        if domain not in self.cost_domain_list and 'ALL' not in self.cost_domain_list:
                                            continue

                                        if not current_cost_dic[current_date][rack][cluster][logic_drwer][domain]:
                                            continue

                                        for project in current_cost_dic[current_date][rack][cluster][logic_drwer][domain]:
                                            if project in cost_dic[hardware][emulator]:
                                                cost_dic[hardware][emulator][project] += current_cost_dic[current_date][rack][cluster][logic_drwer][domain][project]
                                            else:
                                                cost_dic[hardware][emulator][project] = current_cost_dic[current_date][rack][cluster][logic_drwer][domain][project]

        return cost_dic

    def update_cost_tab_frame0(self, hardware='ALL', reset=False):
        if hardware == 'ALL':
            return

        domain_dic = {}

        if hardware in self.hardware_dic:
            domain_dic = self.hardware_dic[hardware]['domain_dic']

        if not domain_dic:
            return

        if reset:
            self.cost_rack_list = ['ALL', ]
            self.cost_cluster_list = ['ALL', ]
            self.cost_logic_drawer_list = ['ALL', ]
            self.cost_domain_list = ['ALL', ]

        # Update self.current_tab_rack_combo
        self.cost_tab_rack_combo.clear()
        self.cost_tab_rack_combo.addCheckBoxItem('ALL')
        self.cost_tab_rack_combo.addCheckBoxItems(domain_dic['rack_list'])
        self.cost_tab_rack_combo.stateChangedconnect(self.cost_rack_combo_change)
        self.cost_tab_rack_combo.selectItems(self.cost_rack_list)

    def cost_rack_combo_change(self):
        hardware = self.cost_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.cost_tab_rack_combo.selectedItems().items()]
        self.cost_rack_list = rack_list

        if 'ALL' in rack_list:
            cluster_list = self.total_hardware_dic[hardware]['domain_dic']['cluster_list']
        else:
            cluster_list = []

            for rack in rack_list:
                cluster_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack].keys())

        self.cost_tab_cluster_combo.clear()
        self.cost_tab_cluster_combo.addCheckBoxItem('ALL')
        self.cost_tab_cluster_combo.addCheckBoxItems(sorted(cluster_list, key=lambda k: int(k)))
        self.cost_tab_cluster_combo.stateChangedconnect(self.cost_tab_cluster_combo_change)
        self.cost_tab_cluster_combo.selectItems(self.cost_cluster_list)

        if not self.cost_tab_cluster_combo.selectedItems():
            self.cost_cluster_list = ['ALL']
            self.cost_tab_cluster_combo.selectItems(self.cost_cluster_list)

    def cost_tab_cluster_combo_change(self):
        hardware = self.cost_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.cost_tab_rack_combo.selectedItems().items()]
        cluster_list = [rack for _, rack in self.cost_tab_cluster_combo.selectedItems().items()]
        self.cost_cluster_list = cluster_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        board_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' in cluster_list or cluster in cluster_list:
                    board_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster])

        self.cost_tab_logic_drawer_combo.clear()
        self.cost_tab_logic_drawer_combo.addCheckBoxItem('ALL')
        self.cost_tab_logic_drawer_combo.addCheckBoxItems(sorted(board_list, key=lambda k: int(k)))
        self.cost_tab_logic_drawer_combo.stateChangedconnect(self.cost_tab_board_combo_change)
        self.cost_tab_logic_drawer_combo.selectItems(self.cost_logic_drawer_list)

        if not self.cost_tab_logic_drawer_combo.selectedItems():
            self.cost_logic_drawer_list = ['ALL']
            self.cost_tab_logic_drawer_combo.selectItems(self.cost_logic_drawer_list)

    def cost_tab_board_combo_change(self):
        hardware = self.cost_tab_hardware_combo.currentText().strip()
        rack_list = [rack for _, rack in self.cost_tab_rack_combo.selectedItems().items()]
        cluster_list = [cluster for _, cluster in self.cost_tab_cluster_combo.selectedItems().items()]
        board_list = [board for _, board in self.cost_tab_logic_drawer_combo.selectedItems().items()]
        self.cost_logic_drawer_list = board_list

        rack_list = rack_list if 'ALL' not in rack_list else self.total_hardware_dic[hardware]['domain_dic']['rack_list']
        domain_list = []

        for rack in rack_list:
            for cluster in self.total_hardware_dic[hardware]['domain_dic'][rack]:
                if 'ALL' not in cluster_list and cluster not in cluster_list:
                    continue

                for board in self.total_hardware_dic[hardware]['domain_dic'][rack][cluster]:
                    if 'ALL' in board_list or board in board_list:
                        domain_list += list(self.total_hardware_dic[hardware]['domain_dic'][rack][cluster][board])

        self.cost_tab_domain_combo.clear()
        self.cost_tab_domain_combo.addCheckBoxItem('ALL')
        self.cost_tab_domain_combo.addCheckBoxItems(sorted(domain_list, key=lambda k: float(k)))
        self.cost_tab_domain_combo.stateChangedconnect(self.cost_tab_domain_combo_change)
        self.cost_tab_domain_combo.selectItems(self.cost_domain_list)

        if not self.cost_tab_domain_combo.selectedItems():
            self.cost_domain_list = ['ALL']
            self.cost_tab_domain_combo.selectItems(self.cost_domain_list)

    def cost_tab_domain_combo_change(self):
        domain_list = [domain for _, domain in self.cost_tab_domain_combo.selectedItems().items()]
        self.cost_tab_domain_list = domain_list

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
            if hardware in self.hardware_dic:
                project_list = self.hardware_dic[hardware]['project_list']
                default_project_cost_dic = self.hardware_dic[hardware]['default_project_cost_dic']
            else:
                return

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

        for hardware in self.history_palladium_path_dic.keys():
            if hardware in self.hardware_list:
                self.cost_tab_hardware_combo.addItem(hardware)

        self.set_cost_tab_emulator_combo()
        self.set_cost_tab_tag_combo()

    def set_cost_tab_emulator_combo(self):
        """
        Set (initialize) self.cost_tab_emulator_combo.
        """
        hardware = self.cost_tab_hardware_combo.currentText().strip()

        emulator_list = []

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

    def set_cost_tab_tag_combo(self):
        """
        Set (initialize) self.utilization_tab_tag_combo.
        """
        hardware = self.cost_tab_hardware_combo.currentText().strip()
        self.cost_tab_tag_combo.clear()
        self.cost_tab_tag_combo.addCheckBoxItem('None')

        if hardware in self.label_dic:
            for label in self.label_dic[hardware]:
                self.cost_tab_tag_combo.addCheckBoxItem(label)

        if hardware in self.hardware_dic:
            self.cost_tab_tag_combo.selectItems(['None'])

        self.cost_tab_tag_combo.stateChangedconnect(self.set_cost_tab_tag_list)

        self.update_cost_tab_frame0(hardware=hardware, reset=True)

    def set_cost_tab_tag_list(self):
        """
        Select tag selected list
        """
        hardware = self.cost_tab_hardware_combo.currentText().strip()
        label_list = self.cost_tab_tag_combo.qLineEdit.text().strip().split()

        if hardware not in self.label_dic:
            return

        if 'domain_dic' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s domain information, please check!" % hardware)
            return

        if not label_list:
            return

        rack_list, cluster_list, logic_drawer_list, domain_list = self.get_label_selected_list(hardware, label_list)

        self.cost_tab_rack_combo.unselectAllItems()
        self.cost_tab_cluster_combo.unselectAllItems()
        self.cost_tab_logic_drawer_combo.unselectAllItems()
        self.cost_tab_domain_combo.unselectAllItems()

        self.cost_tab_rack_combo.selectItems(rack_list)
        self.cost_tab_cluster_combo.selectItems(cluster_list)
        self.cost_tab_logic_drawer_combo.selectItems(logic_drawer_list)
        self.cost_tab_domain_combo.selectItems(domain_list)

    def func_enable_cost_others_project(self, state):
        """
        Class no-project license usage to "others" project with self.enable_cost_others_project.
        """
        if state:
            self.enable_cost_others_project = True

            if 'others' not in self.total_project_list:
                self.total_project_list.append('others')

            for hardware in self.hardware_dic:
                if 'others' not in self.hardware_dic[hardware]['project_list']:
                    self.hardware_dic[hardware]['project_list'].append('others')

        else:
            self.enable_cost_others_project = False

            if 'others' in self.total_project_list:
                self.total_project_list.remove('others')

            for hardware in self.hardware_dic:
                if 'others' in self.hardware_dic[hardware]['project_list']:
                    self.hardware_dic[hardware]['project_list'].remove('others')

        self.gen_cost_tab_table()

    def func_enable_utilization_detail(self, state):
        if state:
            self.enable_utilization_detail = True
            self.utilization_tab_start_date_edit.setDate(QDate.currentDate().addDays(-7))
        else:
            self.enable_utilization_detail = False
            self.utilization_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))

    def func_enable_use_default_cost_rate(self, state):
        if state:
            self.enable_use_default_cost_rate = True
        else:
            self.enable_use_default_cost_rate = False

        self.gen_cost_tab_table()
# For cost TAB (end) #

    def export_current_table(self):
        self.export_table('current', self.current_tab_table, self.palladium_record_table_title_list)

    def export_history_table(self):
        self.export_table('history', self.history_tab_table, self.palladium_record_table_title_list)

    def export_cost_table(self):
        self.export_table('cost', self.cost_tab_table, self.cost_tab_table_title_list)

    def export_table(self, table_type, table_item, title_list):
        """
        Export specified table info into an Excel.
        """
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_time_string = re.sub('-', '', current_time)
        current_time_string = re.sub(':', '', current_time_string)
        current_time_string = re.sub(' ', '_', current_time_string)
        default_output_file = './palladiumMonitor_' + str(table_type) + '_' + str(current_time_string) + '.xlsx'
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

    def closeEvent(self, QCloseEvent):
        """
        When window close, post-process.
        """
        logger.critical('Bye')


class WindowForLabel(QMainWindow):
    save_signal = pyqtSignal(bool)

    def __init__(self, label_info_dic):
        super().__init__()
        self.label_info_dic = label_info_dic
        self.label_name = 'label.0'

        self.init_ui()

    def init_ui(self):
        title = 'Save Label'
        self.setFixedSize(600, 300)
        self.setWindowTitle(title)

        self.top_widget = QWidget()
        self.top_layout = QVBoxLayout()
        self.top_widget.setLayout(self.top_layout)
        self.setCentralWidget(self.top_widget)

        self.main_widget = self.gen_main_frame()

        self.save_button = QPushButton('save')
        self.save_button.clicked.connect(self.save)
        self.cancel_button = QPushButton('cancel')
        self.cancel_button.clicked.connect(self.close)

        self.button_widget = QWidget()
        self.button_layout = QHBoxLayout()
        self.button_widget.setLayout(self.button_layout)
        self.button_layout.addStretch(1)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)

        self.top_layout.addWidget(self.main_widget, 0)
        self.top_layout.addWidget(self.button_widget, 1)
        self.top_layout.setStretch(0, 10)
        self.top_layout.setStretch(10, 11)

        common_pyqt5.center_window(self)

    def gen_main_frame(self):
        main_widget = QWidget()
        main_layout = QFormLayout()
        # hardware label
        hardware_text_label = QLabel(self.label_info_dic['hardware'])
        hardware_text_label.setStyleSheet("font-weight: bold;")
        main_layout.addRow('Hardware', hardware_text_label)

        # rack list QEditLine
        self.rack_list_editline = QLineEdit(','.join(self.label_info_dic['rack_list']))
        self.rack_list_editline.returnPressed.connect(self.change_label_info)
        main_layout.addRow('Rack List', self.rack_list_editline)

        # cluster list QEditLine
        self.cluster_list_editline = QLineEdit(','.join(self.label_info_dic['cluster_list']))
        self.cluster_list_editline.returnPressed.connect(self.change_label_info)
        main_layout.addRow('Cluster List', self.cluster_list_editline)

        # logic drawer list QEditLine
        self.logic_drawer_list_editline = QLineEdit(','.join(self.label_info_dic['logic_drawer_list']))
        self.logic_drawer_list_editline.returnPressed.connect(self.change_label_info)
        main_layout.addRow('Board List', self.logic_drawer_list_editline)

        # domain list QEditLine
        self.domain_list_editline = QLineEdit(','.join(self.label_info_dic['domain_list']))
        self.domain_list_editline.returnPressed.connect(self.change_label_info)
        main_layout.addRow('Domain List', self.domain_list_editline)

        # label name QEditLine
        self.label_name_editline = QLineEdit(self.label_name)
        main_layout.addRow('Label Name', self.label_name_editline)

        self.set_tooltip()

        self.save_combo = QComboBox()
        self.save_combo.addItem('For ALL')
        self.save_combo.addItem('For Me')
        main_layout.addRow('Save For', self.save_combo)

        main_widget.setLayout(main_layout)

        return main_widget

    def set_tooltip(self):
        rack_list, cluster_list, logic_drawer_list, domain_list = self.get_selected_item()

        self.rack_list_editline.setToolTip(', '.join(rack_list))
        self.cluster_list_editline.setToolTip(', '.join(cluster_list))
        self.logic_drawer_list_editline.setToolTip(', '.join(logic_drawer_list))
        self.domain_list_editline.setToolTip(', '.join(domain_list))

    def change_label_info(self):
        rack_list = self.rack_list_editline.text().strip().split(',')
        cluster_list = self.cluster_list_editline.text().strip().split(',')
        logic_drawer_list = self.logic_drawer_list_editline.text().strip().split(',')
        domain_list = self.domain_list_editline.text().strip().split(',')

        rack_list = [str(item) for item in rack_list]

        check_info, check_flag = self.check_item_available(
            rack_list=rack_list,
            cluster_list=cluster_list,
            logic_drawer_list=logic_drawer_list,
            domain_list=domain_list)

        if not check_flag:
            common_pyqt5.Dialog('Error', check_info, icon=QMessageBox.Warning)
            return
        else:
            self.label_info_dic['rack_list'] = rack_list
            self.label_info_dic['cluster_list'] = cluster_list
            self.label_info_dic['logic_drawer_list'] = logic_drawer_list
            self.label_info_dic['domain_list'] = domain_list

        self.set_tooltip()

    def check_item_available(self, rack_list: list = [], cluster_list: list = [], logic_drawer_list: list = [], domain_list: list = []):
        check_info, check_flag = '', True

        for rack in rack_list:
            rack = rack.strip()
            if rack not in self.label_info_dic['domain_dic']['rack_list'] and rack != 'ALL':
                check_info = r'%s in not in rack list' % str(rack)
                return check_info, False

        for cluster in cluster_list:
            cluster = cluster.strip()
            if cluster not in self.label_info_dic['domain_dic']['cluster_list'] and cluster != 'ALL':
                check_info = r'%s in not in cluster list' % str(cluster)
                return check_info, False

        for logic_drawer in logic_drawer_list:
            logic_drawer = logic_drawer.strip()
            if logic_drawer not in self.label_info_dic['domain_dic']['logic_drawer_list'] and logic_drawer != 'ALL':
                check_info = r'%s in not in logic drawer list' % str(logic_drawer)
                return check_info, False

        for domain in domain_list:
            domain = domain.strip()
            if domain not in self.label_info_dic['domain_dic']['domain_list'] and domain != 'ALL':
                check_info = r'%s in not in domain list' % str(domain)
                return check_info, False

        return check_info, check_flag

    def get_selected_item(self):
        rack_list, cluster_list, logic_drawer_list, domain_list = [], [], [], []

        if 'ALL' in self.label_info_dic['rack_list']:
            rack_list = self.label_info_dic['domain_dic']['rack_list']
        else:
            rack_list = self.label_info_dic['rack_list']

        if 'ALL' not in self.label_info_dic['cluster_list']:
            cluster_list = self.label_info_dic['cluster_list']
        else:
            for rack in rack_list:
                for cluster in self.label_info_dic['domain_dic'][rack]:
                    cluster_list.append(cluster)

        if 'ALL' not in self.label_info_dic['logic_drawer_list']:
            logic_drawer_list = self.label_info_dic['logic_drawer_list']
        else:
            for rack in rack_list:
                for cluster in self.label_info_dic['domain_dic'][rack]:
                    if cluster not in cluster_list:
                        continue

                    for logic_drawer in self.label_info_dic['domain_dic'][rack][cluster]:
                        logic_drawer_list.append(logic_drawer)

        if 'ALL' not in self.label_info_dic['domain_list']:
            domain_list = self.label_info_dic['domain_list']
        else:
            for rack in rack_list:
                for cluster in self.label_info_dic['domain_dic'][rack]:
                    if cluster not in cluster_list:
                        continue

                    for logic_drawer in self.label_info_dic['domain_dic'][rack][cluster]:
                        if logic_drawer not in logic_drawer_list:
                            continue

                        for domain in self.label_info_dic['domain_dic'][rack][cluster][logic_drawer]:
                            domain_list.append(domain)

        return rack_list, cluster_list, logic_drawer_list, domain_list

    def save(self):
        config_dic = {}

        if self.rack_list_editline.text().strip() != 'ALL':
            config_dic['rack_list'] = [item.replace(" ", "") for item in self.rack_list_editline.text().split(',')]

        if self.cluster_list_editline.text().strip() != 'ALL':
            config_dic['cluster_list'] = [item.replace(" ", "") for item in self.cluster_list_editline.text().split(',')]

        if self.logic_drawer_list_editline.text().strip() != 'ALL':
            config_dic['logic_drawer_list'] = [item.replace(" ", "") for item in self.logic_drawer_list_editline.text().replace(" ", "").split(',')]

        if self.domain_list_editline.text().strip() != 'ALL':
            config_dic['domain_list'] = [item.replace(" ", "") for item in self.domain_list_editline.text().split(',')]

        config_dic['hardware'] = self.label_info_dic['hardware']

        save_mode = self.save_combo.currentText().strip()
        label_name = self.label_name_editline.text().strip()
        unique_flag = self.check_label_unique(label_name)

        if not unique_flag:
            common_pyqt5.Dialog('Duplicate Name', 'Label Name already exists, please change a label name!', QMessageBox.Warning)
            return

        if save_mode == 'For ALL':
            save_dir = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']), 'config/palladium/label/')
            permission = os.access(str(os.environ['EMU_MONITOR_INSTALL_PATH']), os.W_OK)

            if not permission:
                common_pyqt5.Dialog('Permission Denied', 'You do not have permission save Label For ALL!', QMessageBox.Warning)
                return

            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            save_path = os.path.join(save_dir, r'%s.config.yaml' % str(label_name))
        elif save_mode == 'For Me':
            usr_home_path = os.path.expanduser('~')
            save_dir = os.path.join(usr_home_path, '.config/emuMonitor/label/')

            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            save_path = os.path.join(save_dir, r'%s.config.yaml' % str(label_name))

        with open(save_path, 'w') as sf:
            sf.write(yaml.dump(config_dic, allow_unicode=True))

        self.save_signal.emit(True)
        self.close()

    @staticmethod
    def check_label_unique(label):
        check_flag = True

        # search install path
        install_label_path = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']), 'config/palladium/label/')

        if os.path.exists(install_label_path):
            for file in os.listdir(install_label_path):
                if my_match := re.match(r'(\S+).config.yaml', file):
                    label_name = my_match.group(1)

                    if label_name.strip() == label.strip():
                        return False

        # search usr home path
        usr_home_path = os.path.expanduser('~')
        label_config_path = os.path.join(usr_home_path, '.config/emuMonitor/label/')

        if os.path.exists(label_config_path):
            for file in os.listdir(label_config_path):
                if my_match := re.match(r'(\S+).config.yaml', file):
                    label_name = my_match.group(1)

                    if label_name.strip() == label.strip():
                        return False

        return check_flag


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
