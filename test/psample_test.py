import unittest
import sys
import os
import yaml
import shutil

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/bin'))
from psample import Sampling

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/test_config'))
import config

sys.path.append(sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH'] + '/test/test_config')))
import test_config


class TestSampling(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        """
        Sampling Test setup
        Exec psample -H test_hardware
        """
        self.hardware = test_config.test_hardware
        self.sampling_test = Sampling(self.hardware)
        self.sampling_test.sampling()

        print('Sampling test begin with hardware ' + self.hardware + '...\n')

    @classmethod
    def tearDownClass(self):
        """
        Samplnig Test tear down
        Deleting all file connected with testing when test is finished.
        """
        # clean db file
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

        print('\n\nSampling test end...')

    def test_psample_init(self):
        """
        Testing sampling __init__ func
        Test Sampling hardware = hardware
        Test Sampling parse project_list, project_execute_host_list, project_user_dic, project_proportion_dic result
        """
        self.assertEqual(self.sampling_test.hardware, self.hardware)

        func_name = sys._getframe().f_code.co_name
        func_test_file = os.path.join(test_config.test_result, func_name)
        test_init_dic = {}

        with open(func_test_file, 'r') as tf:
            test_init_dic = yaml.load(tf, Loader=yaml.FullLoader)

        self.assertEqual(self.sampling_test.project_list, test_init_dic['project_list'])
        self.assertEqual(self.sampling_test.project_execute_host_dic, test_init_dic['project_execute_host_dic'])
        self.assertEqual(self.sampling_test.project_user_dic, test_init_dic['project_user_dic'])
        self.assertEqual(self.sampling_test.project_proportion_dic, test_init_dic['project_proportion_dic'])

    def test_psample_palladium_dic(self):
        """
        Testing palladium infomation accessibility
        Test palladium_dci type and keyword
        """
        self.assertIsInstance(self.sampling_test.palladium_dic, dict)
        self.assertNotEqual(self.sampling_test.palladium_dic, {})

        self.assertIn('hardware', self.sampling_test.palladium_dic.keys())
        self.assertEqual(self.sampling_test.palladium_dic['hardware'], r'Palladium %s' % (self.hardware))

        self.assertIn('rack', self.sampling_test.palladium_dic.keys())
        self.assertIn('utilization', self.sampling_test.palladium_dic.keys())

    def test_sampling_file_existence(self):
        """
        Testing palladium infomation file existence
        Test file: db_file, cost_file, utilization_file
        """
        self.assertTrue(os.path.exists(r'%s/%s' % (self.sampling_test.current_db_path, self.sampling_test.current_time)))
        self.assertTrue(os.path.exists(self.sampling_test.utilization_file))
        self.assertTrue(os.path.exists(self.sampling_test.cost_file))

    def test_palladium_data_correctness(self):
        """
        Testing palladium_dic and bd_file have the same content.
        """
        palladium_info_file = str(self.sampling_test.current_db_path) + '/' + str(self.sampling_test.current_time)

        with open(palladium_info_file, 'r') as sf:
            palladium_sampling_dic = yaml.load(sf.read(), Loader=yaml.FullLoader)

        self.assertEqual(self.sampling_test.palladium_dic, palladium_sampling_dic)

    def test_utilization_data_correctness(self):
        """
        Testing palladium_dic utilization is same as utilization file
        """
        palladium_utilization = str(self.sampling_test.palladium_dic['utilization'])

        with open(self.sampling_test.utilization_file, 'r') as uf:
            lines = uf.readlines()
            file_utilization = lines[-1].split()[-1]

        # Testing utilization
        self.assertEqual(file_utilization, palladium_utilization)

    def test_cost_data_correctness(self):
        """
        Testing whether cost file save today infomation and include project:cost infomation
        """
        current_cost_line = ''

        with open(self.sampling_test.cost_file, 'r') as cf:
            lines = cf.readlines()
            current_cost_line = lines[-1]

        # Testing date
        current_date = current_cost_line.split()[0]
        self.assertEqual(current_date, self.sampling_test.current_date)

        # Testing project:cost
        project_cost_dic = {}

        try:
            project_cost_dic = {cost_info.split(':')[0]: int(cost_info.split(':')[1]) for cost_info in current_cost_line.split()[1:]}
        except ValueError:
            self.assertEqual(1, 0, msg='Could not get project:cost infomation from ' + self.sampling_test.cost_file + '!')

        self.assertIn('others', project_cost_dic.keys())


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

    # Testing data structure
    suite_data = unittest.TestSuite()
    suite_data.addTest(TestSampling('test_psample_init'))
    suite_data.addTest(TestSampling('test_psample_palladium_dic'))
    suite_data.addTest(TestSampling('test_sampling_file_existence'))

    # Testing sampling function
    suite_func = unittest.TestSuite()
    suite_func.addTest(TestSampling('test_palladium_data_correctness'))
    suite_func.addTest(TestSampling('test_utilization_data_correctness'))
    suite_func.addTest(TestSampling('test_cost_data_correctness'))

    suite = unittest.TestSuite([suite_data, suite_func])

    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == '__main__':
    main()
