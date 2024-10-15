#!/ic/software/tools/python3/3.8.8/bin/python3
# -*- coding: utf-8 -*-
################################
# File Name   : ptm_monitor.py
# Author      : zhangjingwen.silvia
# Created On  : 2024-02-21 15:59:05
# Description :
################################
import os
import re
import sys
import yaml
import time
import logging
import datetime
import argparse

from PyQt5.QtWidgets import QApplication, QMainWindow, qApp, QFrame, QWidget, QTabWidget, QTableWidget, QGridLayout, QHeaderView, QAction, QMessageBox, QFileDialog, QPushButton, QLabel, QTableWidgetItem, QComboBox, QDateEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QDate, pyqtSignal

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']))
from config import config
from common import common, common_pyqt5, common_protium

os.environ["PYTHONUNBUFFERED"] = '1'

logger = common.get_logger(level=logging.DEBUG)


def read_args():
    """
    Read in arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='debug mode')

    args = parser.parse_args()

    return args


class MainWindow(QMainWindow):
    """
    Main Window for ProtiumMonitor
    """
    def __init__(self):
        super().__init__()

        self.current_protium_dic = {}
        self.history_protium_dic = {}
        self.history_protium_path_dic = self.parse_db_path()
        self.hardware_dic = common_protium.get_protium_host_info()
        self.hardware_list = list(self.hardware_dic.keys())

        self.first_open_flag = True
        self.enable_utilization_detail = False
        self.total_project_list = []

        for hardware in self.hardware_dic:
            for project in self.hardware_dic[hardware]['project_list']:
                if project not in self.total_project_list:
                    self.total_project_list.append(project)

        self.label_dic = self.get_label_dic()
        self.selected_label = ''

        if hasattr(config, 'protium_enable_cost_others_project'):
            self.enable_cost_others_project = config.protium_enable_cost_others_project
        else:
            logger.error("Could not find the definition of protium_enable_cost_others_project in config!")

        if hasattr(config, 'protium_enable_use_default_cost_rate'):
            self.enable_use_default_cost_rate = config.protium_enable_use_default_cost_rate
        else:
            logger.error("Could not find the definition of protium_enable_use_default_cost_rate in config!")

        if self.enable_cost_others_project:
            for hardware in self.hardware_dic:
                self.hardware_dic[hardware]['project_list'].append('others')
            self.total_project_list.append('others')

        self.init_ui()

        self.current_board_list = ['ALL', ]
        self.history_board_list = ['ALL', ]
        self.utilization_board_list = ['ALL', ]
        self.cost_board_list = ['ALL', ]

        self.first_open_flag = False

    @staticmethod
    def parse_db_path():
        """
        Parse config.db_path, get history_protium_path_dic with history protium info (yaml file).
        """
        db_path = os.path.join(config.db_path, 'protium')
        history_protium_path_dic = {}

        if not os.path.exists(db_path):
            logger.error("Could not find protium db path %s, please chekc!" % str(db_path))
        else:
            if not os.listdir(db_path):
                logger.error("Could not find any valid data in path %s, pelase check!" % str(db_path))
                return history_protium_path_dic

            for hardware in os.listdir(db_path):
                hardware_db_path = os.path.join(db_path, hardware)

                if not os.path.isdir(hardware_db_path):
                    continue

                history_protium_path_dic.setdefault(hardware, {})

                for year in os.listdir(hardware_db_path):
                    if not year.isdigit():
                        continue

                    year_db_path = os.path.join(hardware_db_path, year)

                    if not os.path.isdir(year_db_path):
                        continue

                    history_protium_path_dic[hardware].setdefault(year, {})

                    for month in os.listdir(year_db_path):
                        month_db_path = os.path.join(year_db_path, month)

                        if not os.path.isdir(month_db_path):
                            continue

                        history_protium_path_dic[hardware][year].setdefault(month, {})

                        for day in os.listdir(month_db_path):
                            day_db_path = os.path.join(month_db_path, day)

                            if not os.path.isdir(day_db_path):
                                continue

                            history_protium_path_dic[hardware][year][month].setdefault(day, {})

                            for file_name in os.listdir(day_db_path):
                                file_path = os.path.join(day_db_path, file_name)

                                if os.path.exists(file_path):
                                    history_protium_path_dic[hardware][year][month][day][file_name] = file_path

        return history_protium_path_dic

    @staticmethod
    def get_label_dic():
        """
        get label information from local home path -> install path
        label_dic = {'hardware': <hardware>, 'test_server': <test_server>, 'test_server_host': <test_server_host>, 'board_list': <board_list>}
        """
        label_dic = {}

        # search install path
        install_label_path = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']), 'config/protium/label/')

        if os.path.exists(install_label_path):
            for file in os.listdir(install_label_path):
                if my_match := re.match(r'^(\S+).config.yaml$', file):
                    label = my_match.group(1)
                    label_config_file = os.path.join(install_label_path, file)

                    with open(label_config_file, 'r') as cf:
                        info_dic = yaml.load(cf, Loader=yaml.CLoader)
                        hardware = info_dic['hardware']
                        label_dic.setdefault(hardware, {})
                        label_dic[hardware][label] = info_dic

        # search usr home path
        usr_home_path = os.path.expanduser('~')
        label_config_path = os.path.join(usr_home_path, '.config/emuMonitor/protium/label/')

        if os.path.exists(label_config_path):
            for file in os.listdir(label_config_path):
                if my_match := re.match(r'^(\S+).config.yaml$', file):
                    label = my_match.group(1)
                    label_config_file = os.path.join(label_config_path, file)

                    with open(label_config_file, 'r') as cf:
                        info_dic = yaml.load(cf, Loader=yaml.CLoader)
                        hardware = info_dic['hardware']
                        label_dic.setdefault(hardware, {})
                        label_dic[hardware][label] = info_dic

        return label_dic

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
        self.setWindowTitle('emuMonitor - Protium')
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

        about_action = QAction('About protiumMonitor', self)
        about_action.setIcon(QIcon(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/data/pictures/about.png'))
        about_action.triggered.connect(self.show_about)

        help_menu = self.menubar.addMenu('Help')
        help_menu.addAction(version_action)
        help_menu.addAction(about_action)

    def show_version(self):
        """
        Show protiumMonitor version information.
        """
        version = 'V1.2'
        QMessageBox.about(self, 'protiumMonitor', 'Version: ' + str(version) + '        ')

    def show_about(self):
        """
        Show protiumMonitor about information.
        """
        about_message = """
Thanks for downloading protiumMonitor.

protiumMonitor is an open source software for protium information data-collection, data-analysis and data-display."""

        QMessageBox.about(self, 'protiumMonitor', about_message)

    def export_table(self, table_type, table_item, title_list):
        """
        Export specified table info into an Excel.
        """
        current_time_string = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        default_output_file = './protiumMonitor_' + str(table_type) + '_' + str(current_time_string) + '.xlsx'
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
            logger.critical('Writing ' + str(table_type) + ' table into "' + str(output_file) + '" ...')

            common.write_excel(excel_file=output_file, contents_list=table_info_list, specified_sheet_name=table_type)

    def get_label_selected_list(self, hardware, label_list):
        if hardware not in self.label_dic:
            return ['ALL']

        board_set = set()

        for label in label_list:
            if label not in self.label_dic[hardware]:
                continue

            if label in self.label_dic[hardware]:
                if 'board_list' in self.label_dic[hardware][label]:
                    board_set.update(self.label_dic[hardware][label]['board_list'])

        board_list = list(board_set) if board_set else ['ALL', ]

        board_list = self.check_selected_list(hardware=hardware, board_list=board_list)

        return board_list

    def check_selected_list(self, hardware='', board_list=None):
        new_board_list = []
        error_info = 'Following selected is failed, please check!'
        error_flag = False

        if 'board_list' not in self.hardware_dic[hardware]:
            logger.error("Could not find board information is %s, please check!" % hardware)
            return

        if board_list:
            error_info += '\nBoard:'

            for board in board_list:
                if board != 'ALL' and board not in self.hardware_dic[hardware]['board_list']:
                    error_info += '%s ' % str(board)
                    error_flag = True
                    continue

                new_board_list.append(board)

        if error_flag:
            common_pyqt5.Dialog(title='Selected Error',
                                info=error_info,
                                icon=QMessageBox.Warning)

        return new_board_list

    @staticmethod
    def is_file_writing(file_path):
        init_mtime = os.path.getmtime(file_path)
        time.sleep(0.1)
        current_mtime = os.path.getmtime(file_path)
        return init_mtime != current_mtime

    def gen_save_label_window(self):
        """
        selected_info_dic = {'hardware':<hardware>, 'board_list': <board_list>}
        """
        tab_index = self.main_tab.currentIndex()
        label_info_dic = {}
        board_list = []

        if tab_index == 0:
            if self.current_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.current_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            board_list = self.current_board_list
        elif tab_index == 1:
            if self.history_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.history_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            board_list = self.history_board_list
        elif tab_index == 2:
            if self.utilization_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.utilization_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            board_list = self.utilization_board_list
        elif tab_index == 3:
            if self.cost_tab_hardware_combo.currentText().strip() in self.hardware_list:
                hardware = self.cost_tab_hardware_combo.currentText().strip()
            else:
                hardware = self.hardware_list[0]

            board_list = self.cost_board_list

        if hardware not in self.hardware_dic:
            logger.warning("Please select valid hardware first!")
            return

        if 'board_list' not in self.hardware_dic[hardware]:
            logger.warning("Please check palladium information first!")
            return

        label_info_dic['board_list'] = board_list
        label_info_dic['valid_list'] = self.hardware_dic[hardware]['board_list']
        label_info_dic['hardware'] = hardware

        self.label_window = WindowForLabel(label_info_dic)
        self.label_window.save_signal.connect(self.save_label)
        self.label_window.show()

    def save_label(self):
        self.label_dic = self.get_label_dic()
        self.set_current_tab_tag_combo()
        self.set_history_tab_tag_combo()
        self.set_utilization_tab_tag_combo()
        self.set_cost_tab_tag_combo()

# CURRENT

    def gen_current_tab(self):
        """
        Generate the CURRENT tab on protiumMonitor GUI, show current protium usage informations.
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
        Current TAB selection box genenration.
        Generate self.current_tab_frame.
        """
        # self.current_tab_frame
        current_tab_hardware_label = QLabel('Hardware', self.current_tab_frame)
        current_tab_hardware_label.setStyleSheet("font-weight: bold;")
        current_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_hardware_combo = QComboBox(self.current_tab_frame)
        self.current_tab_hardware_combo.addItems(list(self.hardware_dic.keys()))
        self.current_tab_hardware_combo.activated.connect(self.set_current_tab_tag_combo)

        # self.current_tab_frame
        current_tab_board_label = QLabel('Board', self.current_tab_frame)
        current_tab_board_label.setStyleSheet("font-weight: bold;")
        current_tab_board_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_board_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_tag_label = QLabel('Label', self.current_tab_frame)
        current_tab_tag_label.setStyleSheet("font-weight: bold;")
        current_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_tag_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_check_button = QPushButton('Check', self.current_tab_frame)
        current_tab_check_button.setStyleSheet("font-weight: bold;")
        current_tab_check_button.clicked.connect(self.check_current_protium_info)

        current_tab_fpga_label = QLabel('FPGA', self.current_tab_frame)
        current_tab_fpga_label.setStyleSheet("font-weight: bold;")
        current_tab_fpga_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_fpga_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_submit_host_label = QLabel('Submit Host', self.current_tab_frame)
        current_tab_submit_host_label.setStyleSheet("font-weight: bold;")
        current_tab_submit_host_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_submit_host_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_user_label = QLabel('User', self.current_tab_frame)
        current_tab_user_label.setStyleSheet("font-weight: bold;")
        current_tab_user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_user_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        current_tab_pid_label = QLabel('Pid', self.current_tab_frame)
        current_tab_pid_label.setStyleSheet("font-weight: bold;")
        current_tab_pid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.current_tab_pid_combo = common_pyqt5.QComboCheckBox(self.current_tab_frame)

        # self.current_tab_frame - Grid
        current_tab_frame_grid = QGridLayout()

        current_tab_frame_grid.addWidget(current_tab_hardware_label, 0, 0)
        current_tab_frame_grid.addWidget(self.current_tab_hardware_combo, 0, 1)
        current_tab_frame_grid.addWidget(current_tab_board_label, 0, 2)
        current_tab_frame_grid.addWidget(self.current_tab_board_combo, 0, 3)
        current_tab_frame_grid.addWidget(current_tab_tag_label, 0, 4)
        current_tab_frame_grid.addWidget(self.current_tab_tag_combo, 0, 5)
        current_tab_frame_grid.addWidget(current_tab_check_button, 0, 7)
        current_tab_frame_grid.addWidget(current_tab_fpga_label, 1, 0)
        current_tab_frame_grid.addWidget(self.current_tab_fpga_combo, 1, 1)
        current_tab_frame_grid.addWidget(current_tab_submit_host_label, 1, 2)
        current_tab_frame_grid.addWidget(self.current_tab_submit_host_combo, 1, 3)
        current_tab_frame_grid.addWidget(current_tab_user_label, 1, 4)
        current_tab_frame_grid.addWidget(self.current_tab_user_combo, 1, 5)
        current_tab_frame_grid.addWidget(current_tab_pid_label, 1, 6)
        current_tab_frame_grid.addWidget(self.current_tab_pid_combo, 1, 7)

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

        if 'board_list' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s board information, please check!" % hardware)
            return

        if not label_list:
            return

        board_list = self.get_label_selected_list(hardware, label_list)

        self.current_tab_board_combo.unselectAllItems()
        self.current_tab_board_combo.selectItems(board_list)

    def gen_current_tab_table(self):
        self.gen_protium_info_table(self.current_tab_table, self.current_protium_dic)

    def update_current_tab_table(self):
        board = self.current_tab_board_combo.currentText().strip()
        ip = self.current_tab_ip_combo.currentText().strip()
        fpga = self.current_tab_fpga_combo.currentText().strip()
        submit_host = self.current_tab_submit_host_combo.currentText().strip()
        user = self.current_tab_user_combo.currentText().strip()
        pid = self.current_tab_pid_combo.currentText().strip()

        if self.current_protium_dic:
            # Update QComboBox items.
            protium_dic = common_protium.multifilter_protium_dic(
                self.current_protium_dic,
                specified_board_list=[board, ],
                specified_ip_list=[ip, ],
                specified_user_list=[user, ],
                specified_submit_host_list=[submit_host, ],
                specified_fpga_list=[fpga, ],
                specified_pid_list=[pid, ],
            )

            self.gen_protium_info_table(self.current_tab_table, protium_dic)

    def gen_protium_info_table(self, protium_info_table, protium_dic):
        """
        Common function, generate specified table with specified protium info (protium_dic).
        """
        # protium_info_table
        protium_info_table.setShowGrid(True)
        protium_info_table.setSortingEnabled(True)
        protium_info_table.setColumnCount(0)
        protium_info_table.setColumnCount(7)
        self.protium_record_table_title_list = ['Board', 'Board ip', 'FPGA', 'User', 'Host', 'Pid', 'started_time']
        protium_info_table.setHorizontalHeaderLabels(self.protium_record_table_title_list)

        protium_info_table.setColumnWidth(0, 60)
        protium_info_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        protium_info_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        protium_info_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        protium_info_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        protium_info_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        protium_info_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)

        row = -1

        # Fill protium_info_table.
        protium_info_table.setRowCount(0)
        protium_info_list = []

        if not protium_dic:
            return
        else:
            for _, board_dic in protium_dic.items():
                board_id = board_dic['board_id']
                board_ip = board_dic['board_ip']

                if not board_dic['used_record']:
                    fpga, user, host, pid, started_time = '--', '--', '--', '--', '--'
                    protium_info_list.append([board_id, board_ip, fpga, user, host, pid, started_time])
                    continue
                else:
                    for used_record_dic in board_dic['used_record']:
                        fpga = used_record_dic['FPGA']
                        user = used_record_dic['user']
                        host = used_record_dic['host']
                        pid = used_record_dic['pid']
                        started_time = used_record_dic['started_time']

                        protium_info_list.append([board_id, board_ip, fpga, user, host, pid, started_time])

        protium_info_list = sorted(protium_info_list, key=lambda x: int(x[0]))

        protium_info_table.setRowCount(len(protium_info_list))

        for protium_info in protium_info_list:
            row += 1
            # Fill "Board"
            item = QTableWidgetItem(protium_info[0])
            protium_info_table.setItem(row, 0, item)

            # Fill "Ip"
            item = QTableWidgetItem(protium_info[1])
            protium_info_table.setItem(row, 1, item)

            # Fill "FPGA"
            item = QTableWidgetItem(protium_info[2])
            protium_info_table.setItem(row, 2, item)

            # Fill "user"
            item = QTableWidgetItem(protium_info[3])
            protium_info_table.setItem(row, 3, item)

            # Fill "Host"
            item = QTableWidgetItem(protium_info[4])
            protium_info_table.setItem(row, 4, item)

            # Fill "pid"
            item = QTableWidgetItem(protium_info[5])
            protium_info_table.setItem(row, 5, item)

            # Fill "started_time"
            item = QTableWidgetItem(protium_info[6])
            protium_info_table.setItem(row, 6, item)

    def check_current_protium_info(self):
        """
        Generate self.current_tab_table
        """
        hardware = self.current_tab_hardware_combo.currentText().strip()
        label_list = self.current_tab_tag_combo.qLineEdit.text().split()

        if 'board_list' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s board information, please protium_sample -H %s" % (hardware, hardware))
            return

        if label_list != ['None']:
            self.current_board_list = self.get_label_selected_list(hardware, label_list)
        else:
            self.current_board_list = ['ALL', ] if not self.current_tab_board_combo.qLineEdit.text().strip().split() else self.current_tab_board_combo.qLineEdit.text().strip().split()

        self.current_fpga_list = ['ALL', ] if not self.current_tab_fpga_combo.qLineEdit.text().strip().split() else self.current_tab_fpga_combo.qLineEdit.text().strip().split()
        self.current_submit_host_list = ['ALL', ] if not self.current_tab_submit_host_combo.qLineEdit.text().strip().split() else self.current_tab_submit_host_combo.qLineEdit.text().strip().split()
        self.current_user_list = ['ALL', ] if not self.current_tab_user_combo.qLineEdit.text().strip().split() else self.current_tab_user_combo.qLineEdit.text().strip().split()
        self.current_pid_list = ['ALL', ] if not self.current_tab_pid_combo.qLineEdit.text().strip().split() else self.current_tab_pid_combo.qLineEdit.text().strip().split()

        logger.critical("Loading current %s information, please wait ..." % str(hardware))

        self.my_show_message = common_pyqt5.ShowMessage('Info', 'Loading protium current information, please wait a moment ...')
        self.my_show_message.start()

        if hardware not in self.hardware_dic:
            logger.error("Invalid hardware, please check!")
            return

        check_info_command = self.hardware_dic[hardware]['check_info_command']

        logger.info("Check protium information command: %s" % str(check_info_command))

        # Get self.current_protium_dic.
        protium_sys_info_list = common_protium.get_protium_sys_info(command=check_info_command)
        self.current_protium_dic = common_protium.parse_protium_sys_info(protium_sys_info_list)

        self.my_show_message.terminate()

        if self.current_protium_dic:
            self.current_protium_dic = common_protium.multifilter_protium_dic(
                protium_dic=self.current_protium_dic,
                specified_board_list=self.current_board_list,
                specified_ip_list=['ALL'],
                specified_fpga_list=self.current_fpga_list,
                specified_user_list=self.current_user_list,
                specified_pid_list=self.current_pid_list,
                specified_submit_host_list=self.current_submit_host_list
            )
            # Update QComboBox items
            self.update_current_tab_frame()
        else:
            title = 'No valid information!'
            info = 'Not find any valid protium information. \n Please confirm that your current machine can access protium emulator.\n'

            if 'host' in self.hardware_dic[hardware] and self.hardware_dic[hardware]['host']:
                info += 'You can try to login this machine %s to get protium current information.\n' % str(self.hardware_dic[hardware]['host'])

            common_pyqt5.Dialog(title=title, info=info)
            logger.warning('Not find any valid protium information.')

        # Update self.current_tab_table.
        self.gen_current_tab_table()

    def update_current_tab_frame(self, reset=False):
        """
        Update *_combo items on self.current_tab_frame..
        """
        board_set, ip_set, fpga_set, submit_host_set, user_set, pid_set = set(), set(), set(), set(), set(), set()
        hardware = self.current_tab_hardware_combo.currentText().strip()

        for _, board_dic in self.current_protium_dic.items():
            board_set.add(board_dic['board_id'])
            ip_set.add(board_dic['board_ip'])

            if board_dic['used_record']:
                for used_record in board_dic['used_record']:
                    fpga_set.add(used_record['FPGA'])
                    submit_host_set.add(used_record['host'])
                    user_set.add(used_record['user'])
                    pid_set.add(used_record['pid'])

        board_list, ip_list, fpga_list, submit_host_list, user_list, pid_list = sorted(list(board_set), key=lambda x: int(x)), sorted(list(ip_set)), sorted(list(fpga_set)), sorted(list(submit_host_set)), sorted(list(user_set)), sorted(list(pid_set))

        if reset:
            self.current_board_list = ['ALL', ]
            self.current_fpga_list = ['ALL', ]
            self.current_submit_host_list = ['ALL', ]
            self.current_user_list = ['ALL', ]
            self.current_pid_list = ['ALL', ]

        board_list = self.hardware_dic[hardware]['board_list']

        # Update self.current_tab_board_combo
        self.current_tab_board_combo.clear()
        self.current_tab_board_combo.addCheckBoxItem('ALL')
        self.current_tab_board_combo.addCheckBoxItems(board_list)
        self.current_tab_board_combo.selectItems(self.current_board_list)

        # Update self.current_tab_ip_combo
        self.current_tab_pid_combo.clear()
        self.current_tab_pid_combo.addCheckBoxItem('ALL')
        self.current_tab_pid_combo.addCheckBoxItems(ip_list)
        self.current_tab_pid_combo.selectItems(self.current_pid_list)

        # Update self.current_tab_fpga_combo
        self.current_tab_fpga_combo.clear()
        self.current_tab_fpga_combo.addCheckBoxItem('ALL')
        self.current_tab_fpga_combo.addCheckBoxItems(fpga_list)
        self.current_tab_fpga_combo.selectItems(self.current_fpga_list)

        # Update self.current_tab_submit_host_combo
        self.current_tab_submit_host_combo.clear()
        self.current_tab_submit_host_combo.addCheckBoxItem('ALL')
        self.current_tab_submit_host_combo.addCheckBoxItems(submit_host_list)
        self.current_tab_submit_host_combo.selectItems(self.current_submit_host_list)

        # Update self.current_tab_user_combo
        self.current_tab_user_combo.clear()
        self.current_tab_user_combo.addCheckBoxItem('ALL')
        self.current_tab_user_combo.addCheckBoxItems(user_list)
        self.current_tab_user_combo.selectItems(self.current_user_list)

        # Update self.current_tab_pid_combo
        self.current_tab_pid_combo.clear()
        self.current_tab_pid_combo.addCheckBoxItem('ALL')
        self.current_tab_pid_combo.addCheckBoxItems(pid_list)
        self.current_tab_pid_combo.selectItems(self.current_pid_list)

    def export_current_table(self):
        self.export_table('current', self.current_tab_table, self.protium_record_table_title_list)

# HISTORY

    def gen_history_tab(self):
        """
        Generate the CURRENT tab on protiumMonitor GUI, show current protium usage informations.
        """
        # self.current_tab
        self.history_tab_frame = QFrame(self.current_tab)
        self.history_tab_frame.setFrameShadow(QFrame.Raised)
        self.history_tab_frame.setFrameShape(QFrame.Box)

        self.history_tab_table = QTableWidget(self.current_tab)

        # self.current_tab - Grid
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
        History TAB selection box genenration.
        Generate self.history_tab_frame.
        """
        history_tab_hardware_label = QLabel('Hardware', self.history_tab_frame)
        history_tab_hardware_label.setStyleSheet("font-weight: bold;")
        history_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_hardware_combo = QComboBox(self.history_tab_frame)
        self.history_tab_hardware_combo.addItems(list(self.history_protium_path_dic.keys()))
        self.history_tab_hardware_combo.activated.connect(self.set_history_tab_tag_combo)
        self.history_tab_hardware_combo.activated.connect(self.set_history_tab_year_combo)

        # self.history_tab_frame
        history_tab_board_label = QLabel('Board', self.history_tab_frame)
        history_tab_board_label.setStyleSheet("font-weight: bold;")
        history_tab_board_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_board_combo = common_pyqt5.QComboCheckBox(self.history_tab_frame)

        history_tab_tag_label = QLabel('Label', self.history_tab_frame)
        history_tab_tag_label.setStyleSheet("font-weight: bold;")
        history_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.history_tab_tag_combo = common_pyqt5.QComboCheckBox(self.history_tab_frame)

        history_tab_check_button = QPushButton('Check', self.history_tab_frame)
        history_tab_check_button.setStyleSheet("font-weight: bold;")
        history_tab_check_button.clicked.connect(self.check_history_protium_info)

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
        self.history_tab_time_combo.activated.connect(self.check_history_protium_info)

        # self.current_tab_frame - Grid
        history_tab_frame_grid = QGridLayout()

        history_tab_frame_grid.addWidget(history_tab_hardware_label, 0, 0)
        history_tab_frame_grid.addWidget(self.history_tab_hardware_combo, 0, 1)
        history_tab_frame_grid.addWidget(history_tab_board_label, 0, 2)
        history_tab_frame_grid.addWidget(self.history_tab_board_combo, 0, 3)
        history_tab_frame_grid.addWidget(history_tab_tag_label, 0, 4)
        history_tab_frame_grid.addWidget(self.history_tab_tag_combo, 0, 5)
        history_tab_frame_grid.addWidget(history_tab_check_button, 0, 7)

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

        if self.history_protium_path_dic:
            self.set_history_tab_hardware_combo()
            self.set_history_tab_tag_combo()
        else:
            logger.warning("Could not find protium history information, please use protium Sampling scripts first!")

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

        self.update_history_tab_frame(reset=True)

    def set_history_tab_tag_list(self):
        """
        Select tag selected list
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()
        label_list = self.history_tab_tag_combo.qLineEdit.text().strip().split()

        if hardware not in self.label_dic:
            return

        if 'board_list' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s board information, please check!" % hardware)
            return

        if not label_list:
            return

        board_list = self.get_label_selected_list(hardware, label_list)

        self.history_tab_board_combo.unselectAllItems()
        self.history_tab_board_combo.selectItems(board_list)

    def gen_history_tab_table(self):
        self.gen_protium_info_table(self.history_tab_table, self.history_protium_dic)

    def update_history_tab_table(self):
        hardware = self.history_tab_hardware_combo.currentText().strip()
        label_list = self.hisotry_tab_tag_combo.qLineEdit.text().split()

        if hardware not in self.hardware_dic or 'board_list' not in self.hardware_dic[hardware]:
            if not self.first_open_flag:
                error_info = 'Could not find hardware history information, please use protium_sample first!'
                common_pyqt5.Dialog('Error', error_info, icon=QMessageBox.Warning)
            return

        if label_list != ['None']:
            self.history_board_list = self.get_label_selected_list(hardware, label_list)
        else:
            self.history_board_list = ['ALL', ] if not self.history_tab_board_combo.qLineEdit.text().strip().split() else self.history_tab_board_combo.qLineEdit.text().strip().split()

        if self.history_protium_dic:
            # Update QComboBox items.
            protium_dic = common_protium.multifilter_protium_dic(
                self.history_protium_dic,
                specified_board_list=self.history_board_list,
                specified_ip_list=['ALL', ],
                specified_user_list=['ALL', ],
                specified_submit_host_list=['ALL', ],
                specified_fpga_list=['ALL', ],
                specified_pid_list=['ALL', ],
            )

            self.gen_protium_info_table(self.history_tab_table, protium_dic)

    def check_history_protium_info(self):
        """
        Generate self.history_tab_table
        """
        logger.critical("Loading history information, please wait ...")

        hardware = self.history_tab_hardware_combo.currentText().strip()
        year = self.history_tab_year_combo.currentText().strip()
        month = self.history_tab_month_combo.currentText().strip()
        day = self.history_tab_day_combo.currentText().strip()
        time_stamp = self.history_tab_time_combo.currentText().strip()

        self.history_protium_dic = {}

        if not self.first_open_flag:
            self.my_show_message = common_pyqt5.ShowMessage('Info', 'Loading protium history information, please wait a moment ...')
            self.my_show_message.start()

        if hardware and year and month and day and time_stamp:
            try:
                db_file = self.history_protium_path_dic[hardware][year][month][day][time_stamp]
            except ValueError:
                logger.error("Could not find db file in year %s month %s day %s time %s!" % (year, month, day, time_stamp))

                if not self.first_open_flag:
                    self.my_show_message.terminate()

                return

            if os.path.exists(db_file):
                try:
                    with open(db_file, 'r') as DF:
                        self.history_protium_dic = yaml.load(DF, Loader=yaml.CLoader)
                except Exception as error:
                    logger.error("Could not find valid protium information due to %s" % str(error))

                    if not self.first_open_flag:
                        self.my_show_message.terminate()
                    return

        if not self.first_open_flag:
            self.my_show_message.terminate()

        if self.history_protium_dic:
            hardware = self.history_tab_hardware_combo.currentText().strip()
            label_list = self.history_tab_tag_combo.qLineEdit.text().split()

            # Update QComboBox items.
            if label_list != ['None']:
                self.history_board_list = self.get_label_selected_list(hardware, label_list)
            else:
                self.history_board_list = ['ALL', ] if not self.history_tab_board_combo.qLineEdit.text().strip().split() else self.history_tab_board_combo.qLineEdit.text().strip().split()

            self.history_protium_dic = common_protium.multifilter_protium_dic(
                self.history_protium_dic,
                specified_board_list=self.history_board_list,
                specified_ip_list=['ALL', ],
                specified_pid_list=['ALL', ],
                specified_user_list=['ALL', ],
                specified_submit_host_list=['ALL', ],
                specified_fpga_list=['ALL', ]
            )

            self.update_history_tab_frame()
        else:
            logger.warning('Not find any valid protium information.')

        # Update self.current_tab_table.
        self.gen_history_tab_table()

    def update_history_tab_frame(self, reset=False):
        """
        Update *_combo items on self.current_tab_frame..
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()

        if hardware not in self.hardware_dic:
            return

        if 'board_list' not in self.hardware_dic[hardware]:
            return

        board_list = self.hardware_dic[hardware]['board_list']
        board_list = sorted(board_list, key=lambda x: int(x))

        # Update self.current_tab_board_combo
        self.history_tab_board_combo.clear()
        self.history_tab_board_combo.addCheckBoxItem('ALL')
        self.history_tab_board_combo.addCheckBoxItems(board_list)

        if not reset:
            self.history_tab_board_combo.selectItems(self.history_board_list)
        else:
            self.history_tab_board_combo.selectItems(['ALL'])

    def set_history_tab_hardware_combo(self):
        """
        Set (initialize) self.history_tab_year_combo.
        """
        self.history_tab_hardware_combo.clear()

        for hardware in self.history_protium_path_dic:
            self.history_tab_hardware_combo.addItem(str(hardware))

        self.set_history_tab_year_combo()

    def set_history_tab_year_combo(self):
        """
        Set (initialize) self.history_tab_year_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()

        self.history_tab_year_combo.clear()

        for year in self.history_protium_path_dic[hardware]:
            self.history_tab_year_combo.addItem(str(year))

        self.set_history_tab_month_combo()

    def set_history_tab_month_combo(self):
        """
        Set (initialize) self.history_tab_month_combo.
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()
        year = self.history_tab_year_combo.currentText().strip()

        self.history_tab_month_combo.clear()

        if year in self.history_protium_path_dic[hardware]:
            for month in sorted(self.history_protium_path_dic[hardware][year].keys(), key=lambda x: int(x), reverse=True):
                self.history_tab_month_combo.addItem(str(month))

        self.set_history_tab_day_combo()

    def set_history_tab_day_combo(self):
        """
        Set (initiaize) self.history_tab_day_combo
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()
        year = self.history_tab_year_combo.currentText().strip()
        month = self.history_tab_month_combo.currentText().strip()

        self.history_tab_day_combo.clear()

        if year in self.history_protium_path_dic[hardware] and month in self.history_protium_path_dic[hardware][year]:
            for day in sorted(self.history_protium_path_dic[hardware][year][month].keys(), key=lambda x: int(x), reverse=True):
                self.history_tab_day_combo.addItem(str(day))

        self.set_history_tab_time_combo()

    def set_history_tab_time_combo(self):
        """
        Set (initialize) self.history_tab_time_combo
        """
        hardware = self.history_tab_hardware_combo.currentText().strip()
        year = self.history_tab_year_combo.currentText().strip()
        month = self.history_tab_month_combo.currentText().strip()
        day = self.history_tab_day_combo.currentText().strip()

        latest_timestamp = None
        latest_time_utc = datetime.datetime.strptime('00-00-00', '%H-%M-%S')

        self.history_tab_time_combo.clear()

        if year in self.history_protium_path_dic[hardware] and month in self.history_protium_path_dic[hardware][year] and day in self.history_protium_path_dic[hardware][year][month]:
            for time_stamp in self.history_protium_path_dic[hardware][year][month][day]:
                time_stamp_utc = datetime.datetime.strptime(time_stamp, '%H-%M-%S')

                if time_stamp_utc > latest_time_utc:
                    latest_time_utc = time_stamp_utc
                    latest_timestamp = time_stamp

                self.history_tab_time_combo.addItem(str(time_stamp))

        self.history_tab_time_combo.setItemText(0, latest_timestamp)

        self.check_history_protium_info()

    def export_history_table(self):
        self.export_table('history', self.history_tab_table, self.protium_record_table_title_list)

# UTILIZATION

    def gen_utilization_tab(self):
        """
        Generate the UTILIZATION tab on protiumMonitor GUI, show protium utilization information.
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

        # Init self.utilization_tab_frame0.
        self.update_utilization_tab_frame1()

    def gen_utilization_tab_frame0(self):
        """
        initiarte utilzaition frame
        """
        utilization_tab_hardware_label = QLabel('Hardware', self.utilization_tab_frame0)
        utilization_tab_hardware_label.setStyleSheet("font-weight: bold;")
        utilization_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_hardware_combo = QComboBox(self.utilization_tab_frame0)
        self.utilization_tab_hardware_combo.addItems(list(self.history_protium_path_dic.keys()))
        self.utilization_tab_hardware_combo.activated.connect(self.set_utilization_tab_tag_combo)

        utilization_tab_board_label = QLabel('Board', self.utilization_tab_frame0)
        utilization_tab_board_label.setStyleSheet("font-weight: bold;")
        utilization_tab_board_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_board_combo = common_pyqt5.QComboCheckBox(self.utilization_tab_frame0)

        utilization_tab_tag_label = QLabel('Label', self.utilization_tab_frame0)
        utilization_tab_tag_label.setStyleSheet("font-weight: bold;")
        utilization_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.utilization_tab_tag_combo = common_pyqt5.QComboCheckBox(self.utilization_tab_frame0)
        self.set_utilization_tab_tag_combo()

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

        utilization_tab_check_label = QLabel('', self.utilization_tab_frame0)
        utilization_tab_check_button = QPushButton('Check', self.utilization_tab_frame0)
        utilization_tab_check_button.setStyleSheet("font-weight: bold;")
        utilization_tab_check_button.clicked.connect(self.update_utilization_tab_frame1)

        # self.utilization_tab_frame0 - Grid
        utilization_tab_frame0_grid = QGridLayout()

        utilization_tab_frame0_grid.addWidget(utilization_tab_hardware_label, 0, 0)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_hardware_combo, 0, 1)
        utilization_tab_frame0_grid.addWidget(utilization_tab_board_label, 0, 2)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_board_combo, 0, 3)
        utilization_tab_frame0_grid.addWidget(utilization_tab_tag_label, 0, 4)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_tag_combo, 0, 5)
        utilization_tab_frame0_grid.addWidget(utilization_tab_start_date_label, 1, 0)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_start_date_edit, 1, 1)
        utilization_tab_frame0_grid.addWidget(utilization_tab_end_date_label, 1, 2)
        utilization_tab_frame0_grid.addWidget(self.utilization_tab_end_date_edit, 1, 3)
        utilization_tab_frame0_grid.addWidget(utilization_tab_check_label, 1, 4)
        utilization_tab_frame0_grid.addWidget(utilization_tab_check_button, 1, 5)

        utilization_tab_frame0_grid.setColumnStretch(0, 1)
        utilization_tab_frame0_grid.setColumnStretch(1, 1)
        utilization_tab_frame0_grid.setColumnStretch(2, 1)
        utilization_tab_frame0_grid.setColumnStretch(3, 1)
        utilization_tab_frame0_grid.setColumnStretch(4, 1)
        utilization_tab_frame0_grid.setColumnStretch(5, 1)

        self.utilization_tab_frame0.setLayout(utilization_tab_frame0_grid)

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

        if 'board_list' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s board information, please check!" % hardware)
            return

        if not label_list:
            return

        board_list = self.get_label_selected_list(hardware, label_list)

        self.utilization_tab_board_combo.unselectAllItems()
        self.utilization_tab_board_combo.selectItems(board_list)

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
        label_list = self.utilization_tab_tag_combo.qLineEdit.text().split()
        start_date = self.utilization_tab_start_date_edit.date().toString(Qt.ISODate)
        end_date = self.utilization_tab_end_date_edit.date().toString(Qt.ISODate)

        if label_list != ['None']:
            self.utilization_board_list = self.get_label_selected_list(hardware, label_list)
        else:
            self.utilization_board_list = ['ALL', ] if not self.utilization_tab_board_combo.qLineEdit.text().strip().split() else self.utilization_tab_board_combo.qLineEdit.text().strip().split()

        self.update_utilization_tab_frame0(hardware=hardware)

        logger.critical("Loading utilization information, please wait ...")

        if start_date and end_date:
            if 'ALL' in self.utilization_board_list:
                utilization_dic = self.get_utilization_dic(hardware, start_date, end_date)
            else:
                if not self.enable_utilization_detail:
                    utilization_dic = self.get_board_utilization_dic(hardware, start_date, end_date)

                    if not utilization_dic:
                        utilization_dic = self.get_utilization_dic(hardware, start_date, end_date)
                        self.utilization_tab_board_combo.unselectAllItems()
                        self.utilization_tab_board_combo.selectItems(['ALL'])
                        self.utilization_tab_tag_combo.unselectAllItems()
                        self.utilization_tab_tag_combo.selectItems(['None'])
                else:
                    logger.warning('Could not generate detail utilization information based on board!')
                    self.utilization_tab_board_combo.unselectAllItems()
                    self.utilization_tab_board_combo.selectItems(['ALL'])
                    self.utilization_tab_tag_combo.unselectAllItems()
                    self.utilization_tab_tag_combo.selectItems(['None'])

                    utilization_dic = self.get_utilization_dic(hardware, start_date, end_date)

            if not utilization_dic:
                warning_info = "Could not find hardware utilization information, please use protium_sample first!"
                logger.warning(warning_info)

                if not self.first_open_flag:
                    common_pyqt5.Dialog('Error', warning_info, icon=QMessageBox.Warning)
            else:
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

                    av_utilization = int(sum(utilization_list) / len(utilization_list))

                    self.draw_utilization_curve(fig, av_utilization, date_list, utilization_list)

    def get_board_utilization_dic(self, hardware, start_date, end_date):
        """
        Get detail utilization_dic, with "date - utilization" information.
        """
        utilization_dic = {}
        utilization_dir = os.path.join(config.db_path, 'protium/%s/detail' % str(hardware))

        if not os.path.exists(utilization_dir):
            error_info = "Could not find board based utilization information, please check db path!"
            logger.error(error_info)
            common_pyqt5.Dialog('Error', error_info, icon=QMessageBox.Warning)
        else:
            start_date_utc = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date_utc = datetime.datetime.strptime(end_date, '%Y-%m-%d')

            month_num = (end_date_utc.year - start_date_utc.year) * 12 + (end_date_utc.month - start_date_utc.month)

            for month in range(start_date_utc.month - 1, start_date_utc.month + month_num):
                current_year = start_date_utc.year + month // 12
                current_month = month % 12 + 1

                current_utilization_file = os.path.join(utilization_dir, '%s.%s.utilization' % (str(current_year), str(current_month).zfill(2)))

                if not os.path.exists(current_utilization_file):
                    continue

                while (self.is_file_writing(current_utilization_file)):
                    time.sleep(1)

                if not os.path.exists(current_utilization_file):
                    continue

                with open(current_utilization_file, 'r') as uf:
                    current_utilization_dic = yaml.load(uf, Loader=yaml.FullLoader)

                for current_date in current_utilization_dic:
                    current_date_utc = datetime.datetime.strptime(current_date, '%Y-%m-%d')
                    current_date_format = current_date_utc.strftime("%Y%m%d")

                    if start_date_utc > current_date_utc or current_date_utc > end_date_utc:
                        continue
                    else:
                        utilization_sampling = 0
                        utilization_used = 0

                        for board in current_utilization_dic[current_date]:
                            if board not in self.utilization_board_list and 'ALL' not in self.utilization_board_list:
                                continue

                            utilization_sampling += current_utilization_dic[current_date][board]['sampling']
                            utilization_used += current_utilization_dic[current_date][board]['used']

                    if utilization_sampling != 0:
                        utilization = round((utilization_used / utilization_sampling) * 100, 2)
                    else:
                        utilization = 0

                    utilization_dic[current_date_format] = utilization

        return utilization_dic

    def update_utilization_tab_frame0(self, hardware, reset=False):
        """
        Update *_combo items on self.current_tab_frame..
        """
        if hardware not in self.hardware_dic:
            return

        if 'board_list' not in self.hardware_dic[hardware]:
            return

        board_list = self.hardware_dic[hardware]['board_list']

        board_list = sorted(board_list, key=lambda x: int(x))

        # Update self.current_tab_board_combo
        self.utilization_tab_board_combo.clear()
        self.utilization_tab_board_combo.addCheckBoxItem('ALL')
        self.utilization_tab_board_combo.addCheckBoxItems(board_list)

        if not reset:
            self.utilization_tab_board_combo.selectItems(self.utilization_board_list)
        else:
            self.utilization_tab_board_combo.selectItems(['ALL'])

    def get_utilization_dic(self, hardware=None, start_date=None, end_date=None):
        """
        Get utilization_dic, with "date - utilization" information.
        """
        utilization_dic = {}

        if not start_date or not end_date:
            logger.error("Could not find valid utilization information, please exec ptm_sample first!")
            return

        utilization_file = os.path.join(str(config.db_path), 'protium/%s/utilization' % str(hardware))

        if os.path.exists(utilization_file):
            full_utilization_dic = {}
            start_date_utc = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date_utc = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)

            with open(utilization_file, 'r') as UF:
                for line in UF.readlines():
                    if my_match := re.match(r'^\s*(\S+)\s*:\s*(\S+)\s*$', line):
                        date_utc = datetime.datetime.strptime(my_match.group(1), '%Y-%m-%d-%H-%M-%S')

                        if start_date_utc <= date_utc <= end_date_utc:
                            date = date_utc.strftime('%Y%m%d')
                            time = date_utc.strftime('%H%M%S')
                            utilization = my_match.group(2)
                            full_utilization_dic.setdefault(date, {})
                            full_utilization_dic[date].setdefault(time, float(utilization) * 100)

                if self.enable_utilization_detail:
                    for date in full_utilization_dic.keys():
                        for timestamp in full_utilization_dic[date].keys():
                            utilization_dic.setdefault(r'%s-%s' % (date, timestamp), full_utilization_dic[date][timestamp])
                else:
                    for date in full_utilization_dic.keys():
                        utilization = int(sum(full_utilization_dic[date].values()) / len(full_utilization_dic[date]))
                        utilization_dic.setdefault(date, utilization)

        return utilization_dic

    def func_enable_utilization_detail(self, state):
        if state:
            self.enable_utilization_detail = True
            self.utilization_tab_start_date_edit.setDate(QDate.currentDate().addDays(-7))
        else:
            self.enable_utilization_detail = False
            self.utilization_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))

        self.update_utilization_tab_frame1()

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

# COST

    def gen_cost_tab(self):
        """
        Generate the COST tab on palladiumMonitor GUI, show palladium cost informations.
        """
        # self.utilization_tab
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
        cost_tab_hardware_label = QLabel('Hardware', self.cost_tab_frame)
        cost_tab_hardware_label.setStyleSheet("font-weight: bold;")
        cost_tab_hardware_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_hardware_combo = QComboBox(self.cost_tab_frame)
        self.cost_tab_hardware_combo.addItems(list(self.history_protium_path_dic.keys()))
        self.cost_tab_hardware_combo.activated.connect(self.set_cost_tab_tag_combo)

        cost_tab_tag_label = QLabel('Label', self.cost_tab_frame)
        cost_tab_tag_label.setStyleSheet("font-weight: bold;")
        cost_tab_tag_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_tag_combo = common_pyqt5.QComboCheckBox(self.cost_tab_frame)
        self.cost_tab_tag_combo.activated.connect(self.set_cost_tab_tag_list)

        cost_tab_board_label = QLabel('Board', self.cost_tab_frame)
        cost_tab_board_label.setStyleSheet("font-weight: bold;")
        cost_tab_board_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_board_combo = common_pyqt5.QComboCheckBox(self.cost_tab_frame)

        cost_tab_start_date_label = QLabel('Start_Date', self.cost_tab_frame)
        cost_tab_start_date_label.setStyleSheet("font-weight: bold;")
        cost_tab_start_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_start_date_edit = QDateEdit(self.cost_tab_frame)
        self.cost_tab_start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.cost_tab_start_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.cost_tab_start_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.cost_tab_start_date_edit.setCalendarPopup(True)
        self.cost_tab_start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.cost_tab_start_date_edit.dateChanged.connect(self.gen_cost_tab_table)

        cost_tab_end_date_label = QLabel('End_Date', self.cost_tab_frame)
        cost_tab_end_date_label.setStyleSheet("font-weight: bold;")
        cost_tab_end_date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cost_tab_end_date_edit = QDateEdit(self.cost_tab_frame)
        self.cost_tab_end_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.cost_tab_end_date_edit.setMinimumDate(QDate.currentDate().addDays(-3652))
        self.cost_tab_end_date_edit.setMaximumDate(QDate.currentDate().addDays(0))
        self.cost_tab_end_date_edit.setCalendarPopup(True)
        self.cost_tab_end_date_edit.setDate(QDate.currentDate())
        self.cost_tab_end_date_edit.dateChanged.connect(self.gen_cost_tab_table)

        cost_tab_check_label = QLabel('', self.cost_tab_frame)
        cost_tab_check_button = QPushButton('Check', self.cost_tab_frame)
        cost_tab_check_button.setStyleSheet("font-weight: bold;")
        cost_tab_check_button.clicked.connect(self.gen_cost_tab_table)

        # self.utilization_tab_frame0 - Grid
        cost_tab_frame_grid = QGridLayout()

        cost_tab_frame_grid.addWidget(cost_tab_hardware_label, 0, 0)
        cost_tab_frame_grid.addWidget(self.cost_tab_hardware_combo, 0, 1)
        cost_tab_frame_grid.addWidget(cost_tab_board_label, 0, 2)
        cost_tab_frame_grid.addWidget(self.cost_tab_board_combo, 0, 3)
        cost_tab_frame_grid.addWidget(cost_tab_tag_label, 0, 4)
        cost_tab_frame_grid.addWidget(self.cost_tab_tag_combo, 0, 5)
        cost_tab_frame_grid.addWidget(cost_tab_start_date_label, 1, 0)
        cost_tab_frame_grid.addWidget(self.cost_tab_start_date_edit, 1, 1)
        cost_tab_frame_grid.addWidget(cost_tab_end_date_label, 1, 2)
        cost_tab_frame_grid.addWidget(self.cost_tab_end_date_edit, 1, 3)
        cost_tab_frame_grid.addWidget(cost_tab_check_label, 1, 4)
        cost_tab_frame_grid.addWidget(cost_tab_check_button, 1, 5)

        cost_tab_frame_grid.setColumnStretch(0, 1)
        cost_tab_frame_grid.setColumnStretch(1, 1)
        cost_tab_frame_grid.setColumnStretch(2, 1)
        cost_tab_frame_grid.setColumnStretch(3, 1)
        cost_tab_frame_grid.setColumnStretch(4, 1)
        cost_tab_frame_grid.setColumnStretch(5, 1)

        self.cost_tab_frame.setLayout(cost_tab_frame_grid)

        # Init self.utilization_tab_frame0.
        self.set_cost_tab_tag_combo()

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

        if 'board_list' not in self.hardware_dic[hardware]:
            logger.error("Could not find hardware %s board information, please check!" % hardware)
            return

        if not label_list:
            return

        board_list = self.get_label_selected_list(hardware, label_list)

        self.cost_tab_board_combo.unselectAllItems()
        self.cost_tab_board_combo.selectItems(board_list)

    def update_cost_tab_frame0(self, hardware='ALL', reset=False):
        if hardware == 'ALL':
            return

        if hardware not in self.hardware_dic or 'board_list' not in self.hardware_dic[hardware]:
            return

        board_list = self.hardware_dic[hardware]['board_list']

        if reset:
            self.cost_board_list = ['ALL', ]

        # Update self.current_tab_board_combo
        self.cost_tab_board_combo.clear()
        self.cost_tab_board_combo.addCheckBoxItem('ALL')
        self.cost_tab_board_combo.addCheckBoxItems(board_list)
        self.cost_tab_board_combo.selectItems(self.cost_board_list)

    def get_cost_info(self, hardware=None):
        """
        Get protium sampling counts information from config.db_path cost file
        cost_dic = {<project>: <project_sampling>}
        """
        # Print loading cost informaiton message.
        logger.critical('Loading cost information, please wait a moment ...')

        if not self.first_open_flag:
            my_show_message = common_pyqt5.ShowMessage('Info', 'Loading cost information, please wait a moment ...')
            my_show_message.start()

        begin_date = self.cost_tab_start_date_edit.date().toPyDate()
        end_date = self.cost_tab_end_date_edit.date().toPyDate()
        day_inteval = (end_date - begin_date).days
        hardware = self.cost_tab_hardware_combo.currentText().strip()
        label_list = self.cost_tab_tag_combo.qLineEdit.text().split()

        if label_list != ['None']:
            self.cost_board_list = self.get_label_selected_list(hardware, label_list)
        else:
            self.cost_board_list = ['ALL', ] if not self.cost_tab_board_combo.qLineEdit.text().strip().split() else self.cost_tab_board_combo.qLineEdit.text().strip().split()

        self.update_cost_tab_frame0(hardware=hardware)

        if 'ALL' not in self.cost_board_list:
            if 'ALL' != hardware:
                cost_dic = self.get_domain_cost_dic(begin_date, end_date, hardware)

                if not self.first_open_flag:
                    my_show_message.terminate()

                return cost_dic
            else:
                self.cost_board_list = ['ALL', ]
                self.update_cost_tab_frame0(hardware=hardware)

        if not self.first_open_flag:
            my_show_message.terminate()

        cost_dic = {}

        cost_file = os.path.join(config.db_path, 'protium/%s/cost' % str(hardware))

        if os.path.exists(cost_file):
            total_cost_dic = {}

            with open(cost_file, 'r') as cf:
                for line in cf:
                    line_s = line.replace('\n', '').split()

                    if re.match(r'^\s*$', line):
                        continue

                    # Get date & project:cost infomation
                    if re.match(r'^\S+\s*(\S+:\S+\s*)+$', line):
                        date_utc = datetime.datetime.strptime(line.split()[0], '%Y-%m-%d-%H-%M-%S')
                        date = date_utc.strftime('%Y-%m-%d')

                        if date not in total_cost_dic:
                            total_cost_dic[date] = {cost_info.split(':')[0].strip(): int(cost_info.split(':')[1].strip()) for cost_info in line_s[1:]}
                        else:
                            history_cost_dic = {cost_info.split(':')[0].strip(): int(cost_info.split(':')[1].strip()) for cost_info in line_s[1:]}

                            for project in history_cost_dic:
                                if project in total_cost_dic[date]:
                                    total_cost_dic[date][project] += history_cost_dic[project]
                                else:
                                    total_cost_dic[date][project] = history_cost_dic[project]
                    else:
                        logger.warning('Could not find valid infomation in cost file line: ' + line + '!')
                        continue

            for day in range(0, day_inteval + 1):
                cost_date = (begin_date + datetime.timedelta(days=day)).strftime('%Y-%m-%d')

                if cost_date in total_cost_dic:
                    for project in total_cost_dic[cost_date]:
                        if project in cost_dic:
                            cost_dic[project] += total_cost_dic[cost_date][project]
                        else:
                            cost_dic.setdefault(project, total_cost_dic[cost_date][project])

        return cost_dic

    def get_domain_cost_dic(self, start_date_utc, end_date_utc, hardware='ALL'):
        """
        Get domain based cost dict
        """
        cost_dic = {}

        cost_dir = os.path.join(config.db_path, 'protium/%s/detail' % str(hardware))

        if not os.path.exists(cost_dir):
            logger.error("Could not find board based cost information, please check db path!")
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
                        for board in current_cost_dic[current_date]:
                            if board not in self.cost_board_list and 'ALL' not in self.cost_board_list:
                                continue

                            for project in current_cost_dic[current_date][board]:
                                if project in cost_dic:
                                    cost_dic[project] += current_cost_dic[current_date][board][project]
                                else:
                                    cost_dic[project] = current_cost_dic[current_date][board][project]

        return cost_dic

    def gen_cost_tab_table(self):
        """
        Generate self.cost_tab_table.
        """
        hardware = self.cost_tab_hardware_combo.currentText().strip()

        if not hardware:
            if not self.first_open_flag:
                error_info = 'Could not find hardware cost information, please use protium_sample first!'
                common_pyqt5.Dialog('Error', error_info, icon=QMessageBox.Warning)
            return

        self.cost_tab_table_title_list = ['Board', 'TotalSamping']
        self.cost_tab_table_title_list.extend(self.total_project_list)

        self.cost_tab_table.setShowGrid(True)
        self.cost_tab_table.setSortingEnabled(True)
        self.cost_tab_table.setColumnCount(0)
        self.cost_tab_table.setColumnCount(len(self.cost_tab_table_title_list))
        self.cost_tab_table.setHorizontalHeaderLabels(self.cost_tab_table_title_list)
        self.cost_tab_table.setColumnWidth(0, 100)

        for column in range(1, len(self.cost_tab_table_title_list)):
            self.cost_tab_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Stretch)

        # Set self.cost_tab_table row length.
        row_length = 1

        self.cost_tab_table.setRowCount(0)
        self.cost_tab_table.setRowCount(row_length)

        # Get total_runtime information.
        total_sampling = 0
        others_sampling = 0

        cost_dic = self.get_cost_info(hardware=hardware)
        project_list = self.hardware_dic[hardware]['project_list']
        default_project_cost_dic = self.hardware_dic[hardware]['default_project_cost_dic']

        if cost_dic:
            for project in cost_dic:
                project_sampling = cost_dic[project]
                total_sampling += project_sampling

                if project not in project_list:
                    others_sampling += cost_dic[project]

        # Fill "Board" item.
        item = QTableWidgetItem(hardware)
        self.cost_tab_table.setItem(0, 0, item)

        # Fill "total_samping" item
        total_sampling = total_sampling if self.enable_cost_others_project else (total_sampling - others_sampling)

        item = QTableWidgetItem(str(total_sampling))
        self.cost_tab_table.setItem(0, 1, item)

        # Fill "project*" item.
        j = 1

        for project in self.total_project_list:
            if project in cost_dic:
                project_sampling = cost_dic[project]
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
            self.cost_tab_table.setItem(0, j, item)

    def func_enable_use_default_cost_rate(self, state):
        if state:
            self.enable_use_default_cost_rate = True
        else:
            self.enable_use_default_cost_rate = False

        self.gen_cost_tab_table()

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

    def export_cost_table(self):
        self.export_table('cost', self.cost_tab_table, self.cost_tab_table_title_list)


class FigureCanvas(FigureCanvasQTAgg):
    """
    Generate a new figure canvas.
    """
    def __init__(self):
        self.figure = Figure()
        super().__init__(self.figure)


class WindowForLabel(QMainWindow):
    save_signal = pyqtSignal(bool)

    def __init__(self, label_info_dic):
        super().__init__()
        self.label_info_dic = label_info_dic
        self.label_name = 'label.0'

        self.init_ui()

    def init_ui(self):
        title = 'Save Label'
        self.setFixedSize(600, 240)
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
        self.board_list_editline = QLineEdit(','.join(self.label_info_dic['board_list']))
        self.board_list_editline.returnPressed.connect(self.change_label_info)
        self.board_list_editline.setToolTip(', '.join(self.label_info_dic['valid_list']))
        main_layout.addRow('Board List', self.board_list_editline)

        # label name QEditLine
        self.label_name_editline = QLineEdit(self.label_name)
        main_layout.addRow('Label Name', self.label_name_editline)

        self.save_combo = QComboBox()
        self.save_combo.addItem('For ALL')
        self.save_combo.addItem('For Me')
        main_layout.addRow('Save For', self.save_combo)

        main_widget.setLayout(main_layout)

        return main_widget

    def change_label_info(self):
        board_list = self.board_list_editline.text().strip().split(',')
        board_list = [str(item) for item in board_list]

        check_info, check_flag = self.check_item_available(board_list=board_list)

        if not check_flag:
            common_pyqt5.Dialog('Error', check_info, icon=QMessageBox.Warning)
            return
        else:
            self.label_info_dic['board_list'] = board_list

    def check_item_available(self, board_list=[]):
        check_info, check_flag = '', True

        for board in board_list:
            board = board.strip()
            if board not in self.label_info_dic['valid_list'] and board != 'ALL':
                check_info = r'%s in not in board list' % str(board)
                return check_info, False

        return check_info, check_flag

    def save(self):
        config_dic = {}

        board_list = [item.replace(" ", "") for item in self.board_list_editline.text().split(',')]

        check_info, check_flag = self.check_item_available(board_list=board_list)

        if not check_flag:
            common_pyqt5.Dialog('Error', check_info, icon=QMessageBox.Warning)
            return
        else:
            self.label_info_dic['board_list'] = board_list

        if self.board_list_editline.text().strip() != 'ALL':
            config_dic['board_list'] = [item.replace(" ", "") for item in self.board_list_editline.text().split(',')]

        config_dic['hardware'] = self.label_info_dic['hardware']

        save_mode = self.save_combo.currentText().strip()
        label_name = self.label_name_editline.text().strip()
        unique_flag = self.check_label_unique(label_name)

        if not unique_flag:
            common_pyqt5.Dialog('Duplicate Name', 'Label Name already exists, please change a label name!', QMessageBox.Warning)
            return

        if save_mode == 'For ALL':
            save_dir = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']), 'config/protium/label/')
            permission = os.access(str(os.environ['EMU_MONITOR_INSTALL_PATH']), os.W_OK)

            if not permission:
                common_pyqt5.Dialog('Permission Denied', 'You do not have permission save Label For ALL!', QMessageBox.Warning)
                return

            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            save_path = os.path.join(save_dir, r'%s.config.yaml' % str(label_name))
        elif save_mode == 'For Me':
            usr_home_path = os.path.expanduser('~')
            save_dir = os.path.join(usr_home_path, '.config/emuMonitor/protium/label/')

            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            save_path = os.path.join(save_dir, r'%s.config.yaml' % str(label_name))

        print("save_path:", save_path)

        with open(save_path, 'w') as sf:
            sf.write(yaml.dump(config_dic, allow_unicode=True))

        self.save_signal.emit(True)
        self.close()

    @staticmethod
    def check_label_unique(label):
        check_flag = True

        # search install path
        install_label_path = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']), 'config/protium/label/')

        if os.path.exists(install_label_path):
            for file in os.listdir(install_label_path):
                if my_match := re.match(r'(\S+).config.yaml', file):
                    label_name = my_match.group(1)

                    if label_name.strip() == label.strip():
                        return False

        # search usr home path
        usr_home_path = os.path.expanduser('~')
        label_config_path = os.path.join(usr_home_path, '.config/emuMonitor/protium/label/')

        if os.path.exists(label_config_path):
            for file in os.listdir(label_config_path):
                if my_match := re.match(r'(\S+).config.yaml', file):
                    label_name = my_match.group(1)

                    if label_name.strip() == label.strip():
                        return False

        return check_flag


################
# Main Process #
################
def main():
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
