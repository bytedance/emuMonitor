import unittest
import sys
import os
import yaml

from PyQt5.QtWidgets import QLabel

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/bin'))
import pmonitor

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH'] + '/test/test_config')))
import test_config

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config'))
import config


class TestPmonitor(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        """
        Pmonitor test set up
        open pmonitor
        """
        app = pmonitor.QApplication(sys.argv)
        self.pmonitor_gui = pmonitor.MainWindow()
        print('\nStarting tesing pmonitor ...')

    @classmethod
    def tearDownClass(self):
        """
        Pmonitor Tear down
        close pmonitor
        """
        self.pmonitor_gui.close()
        print('\nEnding testing ...')

    def test_parse_db_path(self):
        """
        Test func: parse_db_path()
        test result type and data
        """
        history_palladium_path_dic = self.pmonitor_gui.parse_db_path()

        # Test type
        self.assertIsInstance(history_palladium_path_dic, dict)

        # Test content
        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)
        test_palladium_dic = {}

        with open(func_test_file, 'r') as tf:
            test_palladium_dic = yaml.load(tf, Loader=yaml.FullLoader)

        self.assertEqual(test_palladium_dic, history_palladium_path_dic)

    def test_parse_project_list_file(self):
        """
        Test func: parse_project_list_file
        test result type and data
        """
        project_list = self.pmonitor_gui.parse_project_list_file()

        # Test type
        self.assertIsInstance(project_list, list)

        # Test content
        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)
        test_project_list = []

        with open(func_test_file, 'r') as tf:
            for line in tf:
                test_project_list.append(line.replace('\n', '').strip())

        self.assertEqual(set(test_project_list), set(project_list))

    def test_gen_palladium_info_table(self):
        """
        Test func: gen_palladium_info_table(CURRENT/HISTORY)
        test layout and data
        """
        test_table_dic = {}

        with open(test_config.test_palladium_db, 'r') as tf:
            test_palladium_dic = yaml.load(tf, Loader=yaml.FullLoader)

        self.pmonitor_gui.current_palladium_dic = test_palladium_dic
        self.pmonitor_gui.gen_current_tab_table()

        test_table_dic['row_count'] = self.pmonitor_gui.current_tab_table.rowCount()
        test_table_dic['column_count'] = self.pmonitor_gui.current_tab_table.columnCount()
        test_table_dic.setdefault('items', {})

        for row in range(test_table_dic['row_count']):
            test_table_dic['items'].setdefault(row, {})

            for column in range(test_table_dic['column_count']):
                test_table_dic['items'][row].setdefault(column, '')
                test_table_dic['items'][row][column] = self.pmonitor_gui.current_tab_table.item(row, column).text()

        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)

        with open(func_test_file, 'r') as tf:
            test_current_table_dic = yaml.load(tf, Loader=yaml.FullLoader)

        self.assertEqual(test_current_table_dic, test_table_dic)

    def test_pmonitor_init_ui(self):
        """
        Test init_ui
        test tab and tab/frame1 lable/combo all exist.
        """
        init_ui_tab_dic = {}

        # main tab
        init_ui_tab_dic.setdefault('main_tab', [])
        for i in range(self.pmonitor_gui.main_tab.count()):
            init_ui_tab_dic['main_tab'].append(self.pmonitor_gui.main_tab.tabText(i))

        # current_tab
        init_ui_tab_dic.setdefault('current_tab', {})
        init_ui_tab_dic['current_tab']['layout_rowCount'] = self.pmonitor_gui.current_tab.layout().rowCount()
        init_ui_tab_dic['current_tab'].setdefault('current_frame_tab', [])

        for i in range(len(self.pmonitor_gui.current_tab_frame.findChildren(QLabel))):
            tab_text = self.pmonitor_gui.current_tab_frame.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['current_tab']['current_frame_tab'].append(tab_text)

        # history_tab
        init_ui_tab_dic.setdefault('history_tab', {})
        init_ui_tab_dic['history_tab']['layout_rowCount'] = self.pmonitor_gui.history_tab.layout().rowCount()
        init_ui_tab_dic['history_tab'].setdefault('history_frame_tab', [])

        for i in range(len(self.pmonitor_gui.history_tab_frame.findChildren(QLabel))):
            tab_text = self.pmonitor_gui.history_tab_frame.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['history_tab']['history_frame_tab'].append(tab_text)

        # utilization_tab
        init_ui_tab_dic.setdefault('utilization_tab', {})
        init_ui_tab_dic['utilization_tab']['utilization_rowCount'] = self.pmonitor_gui.utilization_tab.layout().rowCount()
        init_ui_tab_dic['utilization_tab'].setdefault('utilization_frame0_tab', [])

        for i in range(len(self.pmonitor_gui.utilization_tab_frame0.findChildren(QLabel))):
            tab_text = self.pmonitor_gui.utilization_tab_frame0.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['utilization_tab']['utilization_frame0_tab'].append(tab_text)

        # cost tab
        init_ui_tab_dic.setdefault('cost_tab', {})
        init_ui_tab_dic['cost_tab']['cost_tab_rowCount'] = self.pmonitor_gui.cost_tab.layout().rowCount()
        init_ui_tab_dic['cost_tab'].setdefault('cost_frame0_tab', [])

        for i in range(len(self.pmonitor_gui.cost_tab_frame0.findChildren(QLabel))):
            tab_text = self.pmonitor_gui.cost_tab_frame0.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['cost_tab']['cost_frame0_tab'].append(tab_text)

        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)

        with open(func_test_file, 'r') as tf:
            test_tab_dic = yaml.load(tf, Loader=yaml.FullLoader)

        self.assertEqual(test_tab_dic, init_ui_tab_dic)

    def test_pmonitor_combo(self):
        """
        Test func: *combo
        test combo setting
        """
        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)

        with open(func_test_file, 'r') as tf:
            combo_test_dic = yaml.load(tf, Loader=yaml.FullLoader)

        # Test set_current_tab_hardware_combo
        self.pmonitor_gui.set_current_tab_hardware_combo(hardware_list=combo_test_dic['hardware_list'])

        for i in range(len(combo_test_dic['hardware_list'])):
            self.assertEqual(self.pmonitor_gui.current_tab_hardware_combo.itemText(i), combo_test_dic['hardware_list'][i])

        # Test set_history_tab_hardware_combo
        self.pmonitor_gui.set_history_tab_hardware_combo()
        self.pmonitor_gui.history_tab_hardware_combo.setCurrentText(combo_test_dic['history_combo']['test_hardware'])
        self.pmonitor_gui.set_history_tab_emulator_combo()
        self.pmonitor_gui.set_history_tab_year_combo()
        self.pmonitor_gui.set_history_tab_month_combo()
        self.pmonitor_gui.set_history_tab_day_combo()

        test_hardware_item_list = [self.pmonitor_gui.history_tab_hardware_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_hardware_combo.count())]
        self.assertEqual(set(test_hardware_item_list), set(combo_test_dic['history_combo']['hardware_list']))

        test_emulator_item_list = [self.pmonitor_gui.history_tab_emulator_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_emulator_combo.count())]
        self.assertEqual(set(test_emulator_item_list), set(combo_test_dic['history_combo']['emulator']))

        test_year_item_list = [self.pmonitor_gui.history_tab_year_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_year_combo.count())]
        self.assertEqual(set(test_year_item_list), set(combo_test_dic['history_combo']['year']))

        test_month_item_list = [self.pmonitor_gui.history_tab_month_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_month_combo.count())]
        self.assertEqual(set(test_month_item_list), set(combo_test_dic['history_combo']['month']))

        test_day_item_list = [self.pmonitor_gui.history_tab_day_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_day_combo.count())]
        self.assertEqual(set(test_day_item_list), set(combo_test_dic['history_combo']['day']))

        # Utilization
        self.pmonitor_gui.set_utilization_tab_hardware_combo()
        self.pmonitor_gui.utilization_tab_hardware_combo.setCurrentText(combo_test_dic['utilization_combo']['test_hardware'])
        self.pmonitor_gui.set_utilization_tab_emulator_combo()

        test_use_hardware_item_list = [self.pmonitor_gui.utilization_tab_hardware_combo.itemText(i) for i in range(self.pmonitor_gui.utilization_tab_hardware_combo.count())]
        self.assertEqual(set(test_use_hardware_item_list), set(combo_test_dic['utilization_combo']['hardware_list']))

        test_use_emulator_item_list = [self.pmonitor_gui.utilization_tab_emulator_combo.itemText(i) for i in range(self.pmonitor_gui.utilization_tab_emulator_combo.count())]
        self.assertEqual(set(test_use_emulator_item_list), set(combo_test_dic['utilization_combo']['emulator']))

        # Cost
        self.pmonitor_gui.set_cost_tab_hardware_combo()
        self.pmonitor_gui.cost_tab_hardware_combo.setCurrentText(combo_test_dic['cost_combo']['test_hardware'])
        self.pmonitor_gui.set_cost_tab_emulator_combo()

        test_cosr_hardware_item_list = [self.pmonitor_gui.cost_tab_hardware_combo.itemText(i) for i in range(self.pmonitor_gui.cost_tab_hardware_combo.count())]
        self.assertEqual(set(test_cosr_hardware_item_list), set(combo_test_dic['cost_combo']['hardware_list']))

        test_cosr_emulator_item_list = [self.pmonitor_gui.cost_tab_emulator_combo.itemText(i) for i in range(self.pmonitor_gui.cost_tab_emulator_combo.count())]
        self.assertEqual(set(test_cosr_emulator_item_list), set(combo_test_dic['cost_combo']['emulator']))


def init_config():
    """
        Test configure initialization.
        Change config.db_path, config.project_list_file, config.project_execute_host_file, config.project_user_file, config.project_primary_factors for test.
    """
    config.db_path = test_config.db_path
    config.project_list_file = test_config.project_list_file
    config.project_execute_host_file = test_config.project_execute_host_file
    config.project_user_file = test_config.project_user_file
    config.project_primary_factors = test_config.project_primary_factors


def main():
    init_config()
    # Testing suite
    suite_data = unittest.TestSuite()
    suite_data.addTest(TestPmonitor('test_parse_db_path'))
    suite_data.addTest(TestPmonitor('test_parse_project_list_file'))
    suite_data.addTest(TestPmonitor('test_gen_palladium_info_table'))

    suite_gui = unittest.TestSuite()
    suite_gui.addTest(TestPmonitor('test_pmonitor_init_ui'))
    suite_gui.addTest(TestPmonitor('test_pmonitor_combo'))

    suite = unittest.TestSuite([suite_data, suite_gui])

    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == '__main__':
    main()
