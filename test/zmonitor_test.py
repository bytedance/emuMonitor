import unittest
import sys
import os
import yaml

from PyQt5.QtWidgets import QLabel

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/bin'))
import zmonitor

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH'] + '/test/test_config')))
import test_config


class TestZmonitor(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        """
        Pmonitor test set up
        open zmonitor
        """
        app = zmonitor.QApplication(sys.argv)
        self.zmonitor_gui = zmonitor.MainWindow()
        print('\nStarting tesing zmonitor ...')

    @classmethod
    def tearDownClass(self):
        """
        Pmonitor Tear down
        close zmonitor
        """
        self.zmonitor_gui.close()
        print('\nEnding testing ...')

    def test_zmonitor_init_ui(self):
        """
        Test init_ui
        test tab and tab/frame1 lable/combo all exist.
        """
        init_ui_tab_dic = {}

        # main tab
        init_ui_tab_dic.setdefault('main_tab', [])
        for i in range(self.zmonitor_gui.main_tab.count()):
            init_ui_tab_dic['main_tab'].append(self.zmonitor_gui.main_tab.tabText(i))

        # current_tab
        init_ui_tab_dic.setdefault('current_tab', {})
        init_ui_tab_dic['current_tab']['layout_rowCount'] = self.zmonitor_gui.current_tab.layout().rowCount()
        init_ui_tab_dic['current_tab'].setdefault('current_frame_tab', [])

        for i in range(len(self.zmonitor_gui.current_tab_frame.findChildren(QLabel))):
            tab_text = self.zmonitor_gui.current_tab_frame.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['current_tab']['current_frame_tab'].append(tab_text)

        # history_tab
        init_ui_tab_dic.setdefault('history_tab', {})
        init_ui_tab_dic['history_tab']['layout_rowCount'] = self.zmonitor_gui.history_tab.layout().rowCount()
        init_ui_tab_dic['history_tab'].setdefault('history_frame_tab', [])

        for i in range(len(self.zmonitor_gui.history_tab_frame.findChildren(QLabel))):
            tab_text = self.zmonitor_gui.history_tab_frame.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['history_tab']['history_frame_tab'].append(tab_text)

        # utilization_tab
        init_ui_tab_dic.setdefault('utilization_tab', {})
        init_ui_tab_dic['utilization_tab']['utilization_rowCount'] = self.zmonitor_gui.utilization_tab.layout().rowCount()
        init_ui_tab_dic['utilization_tab'].setdefault('utilization_frame0_tab', [])

        for i in range(len(self.zmonitor_gui.utilization_tab_frame0.findChildren(QLabel))):
            tab_text = self.zmonitor_gui.utilization_tab_frame0.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['utilization_tab']['utilization_frame0_tab'].append(tab_text)

        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)

        with open(func_test_file, 'r') as tf:
            test_tab_dic = yaml.load(tf, Loader=yaml.FullLoader)

        self.assertEqual(test_tab_dic, init_ui_tab_dic)
        # Get information
        self.zmonitor_gui.check_current_zebu_info()
        self.zmonitor_gui.update_current_tab_combo()

    def test_zmonitor_combo(self):
        # unit combo
        unit_list = self.zmonitor_gui.current_zebu_dic['unit_list']
        unit_list.append('ALL')

        test_unit_current_combo = [self.zmonitor_gui.current_tab_unit_combo.itemText(i) for i in range(self.zmonitor_gui.current_tab_unit_combo.count())]
        test_unit_history_combo = [self.zmonitor_gui.history_tab_unit_combo.itemText(i) for i in range(self.zmonitor_gui.history_tab_unit_combo.count())]
        test_unit_utilization_combo = [self.zmonitor_gui.history_tab_unit_combo.itemText(i) for i in range(self.zmonitor_gui.utilization_tab_unit_combo.count())]

        self.assertEqual(set(unit_list), set(test_unit_current_combo))
        self.assertEqual(set(unit_list), set(test_unit_history_combo))
        self.assertEqual(set(unit_list), set(test_unit_utilization_combo))

        # module combo
        module_list = self.zmonitor_gui.current_zebu_dic['module_list']
        module_list.append('ALL')

        test_module_current_combo = [self.zmonitor_gui.current_tab_module_combo.itemText(i) for i in range(self.zmonitor_gui.current_tab_module_combo.count())]
        test_module_history_combo = [self.zmonitor_gui.history_tab_module_combo.itemText(i) for i in range(self.zmonitor_gui.history_tab_module_combo.count())]
        test_module_utilization_combo = [self.zmonitor_gui.history_tab_module_combo.itemText(i) for i in range(self.zmonitor_gui.utilization_tab_module_combo.count())]

        self.assertEqual(set(module_list), set(test_module_current_combo))
        self.assertEqual(set(module_list), set(test_module_history_combo))
        self.assertEqual(set(module_list), set(test_module_utilization_combo))

        # history tab
        sub_module_list = self.zmonitor_gui.current_zebu_dic['sub_module_list']
        sub_module_list.append('ALL')

        test_sub_module_current_combo = [self.zmonitor_gui.current_tab_sub_module_combo.itemText(i) for i in range(self.zmonitor_gui.current_tab_sub_module_combo.count())]
        test_sub_module_history_combo = [self.zmonitor_gui.history_tab_sub_module_combo.itemText(i) for i in range(self.zmonitor_gui.history_tab_sub_module_combo.count())]
        test_sub_module_utilization_combo = [self.zmonitor_gui.history_tab_sub_module_combo.itemText(i) for i in range(self.zmonitor_gui.utilization_tab_sub_module_combo.count())]

        self.assertEqual(set(sub_module_list), set(test_sub_module_current_combo))
        self.assertEqual(set(sub_module_list), set(test_sub_module_history_combo))
        self.assertEqual(set(sub_module_list), set(test_sub_module_utilization_combo))

    def test_zmonitor_gen_current_table(self):
        """
        Test func: gen_current_tab_table(CURRENT)
        """
        self.zmonitor_gui.gen_current_tab_table()

        zebu_dic = self.zmonitor_gui.current_zebu_dic

        # Test row&column count
        self.assertEqual(self.zmonitor_gui.current_tab_table.columnCount(), 8)

        row = 0

        for unit in zebu_dic['info']:
            for module in zebu_dic['info'][unit]:
                for sub_module in zebu_dic['info'][unit][module]:
                    item_info_list = [unit, module, sub_module]

                    for record in zebu_dic['info'][unit][module][sub_module].values():
                        item_info_list.append(record)

                    for column in range(0, 7):
                        self.assertEqual(item_info_list[column], self.zmonitor_gui.current_tab_table.item(row, column).text())

                    row += 1

    def test_zmonitor_get_utilization_info(self):
        """
        Test func: get_utilization_info
        """
        start_date = '2020-01-01'
        end_date = '2023-08-01'
        zebu_dic = self.zmonitor_gui.current_zebu_dic

        utilization_info_dic = {}
        record = 0

        for unit in zebu_dic['info']:
            for module in zebu_dic['info'][unit]:
                for sub_module in zebu_dic['info'][unit][module]:
                    record += 1
                    utilization_info_dic[record] = self.zmonitor_gui.get_utilization_info(unit, module, sub_module, start_date, end_date)

        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)

        with open(func_test_file, 'r') as tf:
            test_utilization_info_dic = yaml.load(tf, Loader=yaml.FullLoader)

        self.assertEqual(test_utilization_info_dic, utilization_info_dic)


def main():
    # Testing suite
    suite_data = unittest.TestSuite()
    suite_data.addTest(TestZmonitor('test_zmonitor_gen_current_table'))
    suite_data.addTest(TestZmonitor('test_zmonitor_get_utilization_info'))

    suite_gui = unittest.TestSuite()
    suite_gui.addTest(TestZmonitor('test_zmonitor_init_ui'))
    suite_gui.addTest(TestZmonitor('test_zmonitor_combo'))

    suite = unittest.TestSuite([suite_gui, suite_data])

    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == '__main__':
    main()
