import sys
import os
import yaml
import random
import re
import shutil
import argparse

from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import QDate

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/bin'))
import pmonitor
import zmonitor
from psample import Sampling

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH'] + '/test/test_config')))
import test_config

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config'))
import config


class ZebuTestResult:
    def __init__(self):
        # Zmonitor
        print('Start generate zebu test db ...')

        self.zmonitor_gui = zmonitor.MainWindow()
        self.test_zmonitor_result()
        self.zmonitor_gui.close()

    def test_zmonitor_result(self):
        self.test_result_zmonitor_init_ui()

        self.test_zmonitor_get_utilization_info()

    def test_result_zmonitor_init_ui(self):
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
        init_ui_tab_dic['utilization_tab'][
            'utilization_rowCount'] = self.zmonitor_gui.utilization_tab.layout().rowCount()
        init_ui_tab_dic['utilization_tab'].setdefault('utilization_frame0_tab', [])

        for i in range(len(self.zmonitor_gui.utilization_tab_frame0.findChildren(QLabel))):
            tab_text = self.zmonitor_gui.utilization_tab_frame0.findChildren(QLabel)[i].text()

            if tab_text != '':
                init_ui_tab_dic['utilization_tab']['utilization_frame0_tab'].append(tab_text)

        func_test_file = os.path.join(test_config.test_result, 'test_zmonitor_init_ui')

        with open(func_test_file, 'w') as tf:
            tf.write(yaml.dump(init_ui_tab_dic, allow_unicode=True))

    def test_zmonitor_get_utilization_info(self):
        start_date = '2020-01-01'
        end_date = '2023-08-01'
        zebu_dic = self.zmonitor_gui.current_zebu_dic

        utilization_info_dic = {}
        record = 0

        for unit in zebu_dic['info']:
            for module in zebu_dic['info'][unit]:
                for sub_module in zebu_dic['info'][unit][module]:
                    record += 1
                    utilization_info_dic[record] = self.zmonitor_gui.get_utilization_info(unit, module, sub_module,
                                                                                          start_date, end_date)

        func_test_file = os.path.join(test_config.test_result, 'test_zmonitor_get_utilization_info')

        with open(func_test_file, 'w') as tf:
            tf.write(yaml.dump(utilization_info_dic, allow_unicode=True))


class PalladiumTestResult:
    def __init__(self):
        print('Start generate palladium test db ...')

        # Pmonitor
        self.pmonitor_gui = pmonitor.MainWindow()
        self.test_pmonitor_result()
        self.pmonitor_gui.close()

        # Psample
        self.hardware = test_config.test_hardware
        self.sampling_test = Sampling(self.hardware)

        self.sampling_test.sampling()

        self.test_psample_result()

        if os.path.exists(test_config.db_path):
            for dir in os.listdir(test_config.db_path):
                delete_dir = ''

                hardware_dir = os.path.join(test_config.db_path, dir)

                if dir != self.hardware:
                    delete_dir = hardware_dir
                else:
                    for subdir in os.listdir(hardware_dir):
                        if subdir != 'emulator':
                            delete_dir = os.path.join(hardware_dir, subdir)

                if delete_dir:
                    if os.path.isdir(delete_dir):
                        print("deleting ...", delete_dir)
                        shutil.rmtree(delete_dir)

    def test_pmonitor_result(self):
        self.test_result_parse_db_path()

        self.test_result_cost_table()

        self.test_pmonitor_result_combo()

        self.test_result_pmonitor_init_ui()

        self.test_result_gen_palladium_info_dic_table()

        self.test_result_parse_project_list_file()

    def test_psample_result(self):
        self.test_result_psample_init()

    def test_result_psample_init(self):
        test_init_dic = {}

        test_init_dic['project_list'] = self.sampling_test.project_list
        test_init_dic['project_execute_host_dic'] = self.sampling_test.project_execute_host_dic
        test_init_dic['project_user_dic'] = self.sampling_test.project_user_dic
        test_init_dic['project_proportion_dic'] = self.sampling_test.project_proportion_dic

        func_test_file = os.path.join(test_config.test_result, 'test_psample_init')

        with open(func_test_file, 'w') as tf:
            tf.write(yaml.dump(test_init_dic, allow_unicode=True))

    def test_result_parse_db_path(self):
        path_dic = self.pmonitor_gui.parse_db_path()
        func_test_file = os.path.join(test_config.test_result, 'test_parse_db_path')

        with open(func_test_file, 'w') as tf:
            tf.write(yaml.dump(path_dic, allow_unicode=True))

    def test_result_cost_table(self):
        # Setting date from 20000702 -- 20230703
        self.pmonitor_gui.cost_tab_start_date_edit.setDate(QDate(2000, 6, 30))
        self.pmonitor_gui.cost_tab_end_date_edit.setDate(QDate(2023, 7, 3))
        self.pmonitor_gui.gen_cost_tab_table()

        test_table_dic = {}
        test_table_dic['row_count'] = self.pmonitor_gui.cost_tab_table.rowCount()
        test_table_dic['column_count'] = self.pmonitor_gui.cost_tab_table.columnCount()
        test_table_dic.setdefault('items', {})

        for row in range(test_table_dic['row_count']):
            test_table_dic['items'].setdefault(row, {})

            for column in range(test_table_dic['column_count']):
                test_table_dic['items'][row].setdefault(column, '')
                test_table_dic['items'][row][column] = self.pmonitor_gui.cost_tab_table.item(row, column).text()

        func_test_file = os.path.join(test_config.test_result, 'test_cost_table')

        with open(func_test_file, 'w') as tf:
            tf.write(yaml.dump(test_table_dic, allow_unicode=True))

    def test_pmonitor_result_combo(self):
        combo_test_dic = {}

        combo_test_dic['hardware_list'] = ['Z1', 'Z2']
        # Test set_current_tab_hardware_combo
        self.pmonitor_gui.set_current_tab_hardware_combo(hardware_list=combo_test_dic['hardware_list'])

        combo_test_dic.setdefault('history_combo', {})
        combo_test_dic['history_combo']['test_hardware'] = test_config.test_hardware
        # Test set_history_tab_hardware_combo
        self.pmonitor_gui.set_history_tab_hardware_combo()
        self.pmonitor_gui.history_tab_hardware_combo.setCurrentText(combo_test_dic['history_combo']['test_hardware'])
        self.pmonitor_gui.set_history_tab_emulator_combo()
        self.pmonitor_gui.set_history_tab_year_combo()
        self.pmonitor_gui.set_history_tab_month_combo()
        self.pmonitor_gui.set_history_tab_day_combo()

        test_hardware_item_list = [self.pmonitor_gui.history_tab_hardware_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_hardware_combo.count())]
        combo_test_dic['history_combo']['hardware_list'] = test_hardware_item_list

        test_emulator_item_list = [self.pmonitor_gui.history_tab_emulator_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_emulator_combo.count())]
        combo_test_dic['history_combo']['emulator'] = test_emulator_item_list

        test_year_item_list = [self.pmonitor_gui.history_tab_year_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_year_combo.count())]
        combo_test_dic['history_combo']['year'] = test_year_item_list

        test_month_item_list = [self.pmonitor_gui.history_tab_month_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_month_combo.count())]
        combo_test_dic['history_combo']['month'] = test_month_item_list

        test_day_item_list = [self.pmonitor_gui.history_tab_day_combo.itemText(i) for i in range(self.pmonitor_gui.history_tab_day_combo.count())]
        combo_test_dic['history_combo']['day'] = test_day_item_list

        # Utilization
        combo_test_dic.setdefault('utilization_combo', {})
        combo_test_dic['utilization_combo']['test_hardware'] = test_config.test_hardware

        self.pmonitor_gui.set_utilization_tab_hardware_combo()
        self.pmonitor_gui.utilization_tab_hardware_combo.setCurrentText(combo_test_dic['utilization_combo']['test_hardware'])
        self.pmonitor_gui.set_utilization_tab_emulator_combo()

        test_use_hardware_item_list = [self.pmonitor_gui.utilization_tab_hardware_combo.itemText(i) for i in range(self.pmonitor_gui.utilization_tab_hardware_combo.count())]
        combo_test_dic['utilization_combo']['hardware_list'] = test_use_hardware_item_list

        test_use_emulator_item_list = [self.pmonitor_gui.utilization_tab_emulator_combo.itemText(i) for i in range(self.pmonitor_gui.utilization_tab_emulator_combo.count())]
        combo_test_dic['utilization_combo']['emulator'] = test_use_emulator_item_list

        # Cost
        combo_test_dic.setdefault('cost_combo', {})
        combo_test_dic['cost_combo']['test_hardware'] = test_config.test_hardware

        self.pmonitor_gui.set_cost_tab_hardware_combo()
        self.pmonitor_gui.cost_tab_hardware_combo.setCurrentText(combo_test_dic['cost_combo']['test_hardware'])
        self.pmonitor_gui.set_cost_tab_emulator_combo()

        test_cosr_hardware_item_list = [self.pmonitor_gui.cost_tab_hardware_combo.itemText(i) for i in range(self.pmonitor_gui.cost_tab_hardware_combo.count())]
        combo_test_dic['cost_combo']['hardware_list'] = test_cosr_hardware_item_list

        test_cosr_emulator_item_list = [self.pmonitor_gui.cost_tab_emulator_combo.itemText(i) for i in range(self.pmonitor_gui.cost_tab_emulator_combo.count())]
        combo_test_dic['cost_combo']['emulator'] = test_cosr_emulator_item_list

        test_func_file = os.path.join(test_config.test_result, 'test_pmonitor_combo')

        with open(test_func_file, 'w') as tf:
            tf.write(yaml.dump(combo_test_dic, allow_unicode=True))

    def test_result_pmonitor_init_ui(self):
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

        func_test_file = os.path.join(test_config.test_result, 'test_pmonitor_init_ui')

        with open(func_test_file, 'w') as tf:
            tf.write(yaml.dump(init_ui_tab_dic, allow_unicode=True))

    def test_result_gen_palladium_info_dic_table(self):
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

        func_test_file = os.path.join(test_config.test_result, 'test_gen_palladium_info_table')

        with open(func_test_file, 'w') as tf:
            tf.write(yaml.dump(test_table_dic, allow_unicode=True))

    def test_result_parse_project_list_file(self):
        project_list = ['projectA', 'projectB', 'projectC', 'projectD', 'projectE']

        func_test_file = os.path.join(test_config.test_result, 'test_parse_project_list_file')

        with open(func_test_file, 'w') as tf:
            for project in project_list:
                tf.write(project + '\n')


class TestDB:
    def __init__(self):
        self.hardware = 'Z2'
        self.emulator = 'Emulator'
        self.palladium_dic = self.parse_palladium_db(test_config.test_palladium_db)

        self.choice_letter_list = ['A', 'B', 'C', 'D', 'E']
        self.choice_num_list = [i for i in range(20)]
        self.day_list = [str(i).zfill(2) for i in range(1, 3)]
        self.month = '07'
        self.year = '2000'

        self.gen_random_db_file(test_config.db_path)

        self.gen_config_file()

    def parse_palladium_db(self, db_file):
        with open(db_file, 'r') as df:
            palladium_dic = yaml.load(df, Loader=yaml.FullLoader)

        return palladium_dic

    def gen_random_db_file(self, db_path):
        owner_list = ['None', ]
        pid_list = ['0', ]
        db_path = os.path.join(db_path, self.hardware, self.emulator)
        use_file = os.path.join(db_path, 'utilization')
        cost_file = os.path.join(db_path, 'cost')

        for letter in self.choice_letter_list:
            for num in self.choice_num_list:
                owner = r'user_%s%s' % (letter, str(num))
                owner_list.append(owner)

                server = r'server_%s%s' % (letter, str(num))
                pid = r'%s:%s' % (server, str(random.randint(0, 10000)))
                pid_list.append(pid)

        for day in self.day_list:
            cost_dic = {}
            db_dir = r'%s/%s/%s/%s' % (db_path, self.year, self.month, str(day))

            for letter in self.choice_letter_list:
                cost_dic[letter] = 0

            if not os.path.exists(db_dir):
                os.makedirs(db_dir)

            for hour in range(0, 23):
                db_file_path = os.path.join(db_dir, r'%s0001' % (str(hour).zfill(2)))

                use_num = 0
                for rack in self.palladium_dic['rack']:
                    for cluster in self.palladium_dic['rack'][rack]['cluster']:
                        for logic_drawer in self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"]:
                            for domain in self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain']:
                                owner = random.choice(owner_list)
                                self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['owner'] = owner

                                if owner != 'None':
                                    use_num += 1
                                    pid = random.choice(pid_list)
                                    self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['pid'] = pid

                                    for letter in self.choice_letter_list:
                                        if re.match(r'server_%s(\S+)\s*$' % (letter), pid):
                                            cost_dic[letter] += 1
                                            break
                                else:
                                    self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['pid'] = '0'

                                self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['pid'] = random.choice(pid_list)
                                self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['tpod'] = '-- --'
                                self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['design'] = 'design'
                                self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['elaptime'] = '01:00:00'
                                self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'][domain]['elaptime'] = '--'

                self.palladium_dic['utilization'] = str(round(use_num / 192, 2))

                with open(db_file_path, 'w') as df:
                    df.write(yaml.dump(self.palladium_dic, allow_unicode=True))

                with open(use_file, 'a+') as uf:
                    uf.write(r'202307%s %s0001 : %s' % (str(day), str(hour), self.palladium_dic['utilization']) + '\n')

            with open(cost_file, 'a+') as cf:
                line = '2023-07-%s' % (str(day)) + '\t'

                for letter in cost_dic:
                    line += '{:<15}'.format(r'project%s:%s' % (letter, str(cost_dic[letter])))

                cf.write(line + '\n')

    def gen_config_file(self):
        project_host = test_config.project_execute_host_file
        project_user = test_config.project_user_file

        with open(project_user, 'w') as uf:
            for letter in self.choice_letter_list:
                for num in self.choice_num_list:
                    line = r'user_%s%s : project%s' % (letter, str(num), letter)
                    uf.write(line + '\n')

        with open(project_host, 'w') as hf:
            for letter in self.choice_letter_list:
                for num in self.choice_num_list:
                    line = r'server_%s%s : project%s' % (letter, str(num), letter)
                    hf.write(line + '\n')


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


def init_test_path():
    if not os.path.exists(test_config.db_path):
        os.makedirs(test_config.db_path)

    if not os.path.exists(test_config.test_result):
        os.makedirs(test_config.test_result)


def read_args():
    """
    Read in arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', '--tool',
                        default=None,
                        help='tool: palladium/zebu')

    args = parser.parse_args()

    return args


def main():
    app = QApplication(sys.argv)

    init_config()

    init_test_path()

    test_db = TestDB()

    if test_db:
        print(">>> Successfully generate palladium test db ...")

    args = read_args()

    if args.tool.lower() == 'palladium':
        test_palladium_result = PalladiumTestResult()

        if test_palladium_result:
            print(">>> Successfully generate pmonitor and psample test file ...")

    elif args.tool.lower() == 'zebu':
        test_zebu_result = ZebuTestResult()

        if test_zebu_result:
            print(">>> Successfully generate zmonitor test file ...")


if __name__ == '__main__':
    main()
