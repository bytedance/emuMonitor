# -*- coding: utf-8 -*-

import os
import re
import sys
import yaml
import argparse
import datetime
import logging

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/common')
import common_palladium
import common

# Import local config file if exists.
LOCAL_CONFIG_DIR = str(os.environ['HOME']) + '/.palladiumMonitor/config'
LOCAL_CONFIG = str(LOCAL_CONFIG_DIR) + '/config.py'

if os.path.exists(LOCAL_CONFIG):
    sys.path.append(LOCAL_CONFIG_DIR)
    import config
else:
    sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config')
    import config


os.environ["PYTHONUNBUFFERED"] = '1'
logger = common.get_logger(level=logging.WARNING)


def read_args():
    """
    Read arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-H', '--hardware',
                        choices=['Z1', 'Z2'],
                        default='Z1',
                        help='Specify hardware, it could be "Z1" or "Z2", default is "Z1".')
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        default=False,
                        help='Enable debug mode.')
    parser.add_argument('-re', '--reconfig',
                        action='store_true',
                        default=False,
                        help='reconfig cost and modify all cost infomation')

    args = parser.parse_args()

    if args.debug:
        logger = common.get_logger(level=logging.DEBUG)
    else:
        logger = common.get_logger(level=logging.WARNING)

    return args


class Sampling:
    """
    Sample palladium usage information with command "test_server".
    Save info into yaml files.
    """
    def __init__(self, hardware):
        self.hardware = hardware

        self.current_year = datetime.datetime.now().strftime('%Y')
        self.current_month = datetime.datetime.now().strftime('%m')
        self.current_day = datetime.datetime.now().strftime('%d')
        self.current_time = datetime.datetime.now().strftime('%H%M%S')
        self.current_date = datetime.datetime.now().strftime('%Y-%m-%d')

        self.palladium_dic = {}

        # Get project related information.
        project_list_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + r'/config/palladium/%s/project_list' % hardware
        project_execute_host_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/palladium/%s/project_execute_host' % hardware
        project_user_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/palladium/%s/project_user_file' % hardware

        self.project_list, self.default_project_cost_dic = common.parse_project_list_file(project_list_file)
        self.project_list.append('others')
        self.default_project_cost_dic['others'] = 0

        self.project_execute_host_dic = common.parse_project_proportion_file(project_execute_host_file)
        self.project_user_dic = common.parse_project_proportion_file(project_user_file)

        self.project_proportion_dic = {'execute_host': self.project_execute_host_dic, 'user': self.project_user_dic}

        self.palladium_cost_dic = {}

    def create_db_path(self):
        """
        Create db_path if not exists.
        """
        if not os.path.exists(self.current_db_path):
            try:
                os.system('mkdir -p ' + str(self.current_db_path))
            except Exception as error:
                logger.error('Failed on creating database directory "' + str(self.current_db_path) + '". \n' + str(error))
                sys.exit(1)

    def sampling(self):
        """
        Sample palladium usage information.
        """
        logger.critical('>>> Sampling palladium usage information ...')

        # Get palladium_dic.
        test_server_info = common_palladium.get_test_server_info(self.hardware)
        self.palladium_dic = common_palladium.parse_test_server_info(test_server_info)

        if self.palladium_dic:
            # Print debug information.
            logger.debug('    Sample Time : ' + str(self.current_year) + str(self.current_month) + str(self.current_day) + '_' + str(self.current_time))
            logger.debug('    Hardware : ' + self.palladium_dic['hardware'])
            logger.debug('    Emulator : ' + self.palladium_dic['emulator'])
            logger.debug('    Status : ' + self.palladium_dic['emulator_status'])
            logger.debug('    Utilization : ' + str(self.palladium_dic['utilization']))

            # Create datebase path.
            emulator = self.palladium_dic['emulator']
            self.current_db_path = str(config.db_path) + '/' + str(self.hardware) + '/' + str(emulator) + '/' + str(self.current_year) + '/' + str(self.current_month) + '/' + str(self.current_day)
            self.create_db_path()

            # Save palladium_dic.
            palladium_info_file = str(self.current_db_path) + '/' + str(self.current_time)

            with open(palladium_info_file, 'a', encoding='utf-8') as PIF:
                yaml.dump(self.palladium_dic, PIF, indent=4, sort_keys=False)

            # Save utilizationps
            utilization = self.palladium_dic['utilization']
            self.utilization_file = str(config.db_path) + '/' + str(self.hardware) + '/' + str(emulator) + '/utilization'

            with open(self.utilization_file, 'a', encoding='utf-8') as URF:
                URF.write(str(self.current_year) + str(self.current_month) + str(self.current_day) + ' ' + str(self.current_time) + ' : ' + str(utilization) + '\n')

            # get self.palladium_cost_dic.
            self.get_cost_info()

            # Update palladium cost file.
            self.update_cost_file(emulator)

    def get_cost_info(self):
        """
        Get emulator sampling record project infomation, generate self.palladium_cost_dic.
        self.palladium_cost_dic = {<Hardware> : {<Emulator>: {<Project>: <sampling_counts>}}}
        <project> including all project from self.project_list, and self.project*file if the project sampling is not 0
        """
        emulator = self.palladium_dic['emulator']

        self.palladium_cost_dic.setdefault(self.hardware, {})
        self.palladium_cost_dic[self.hardware].setdefault(emulator, {})

        self.palladium_cost_dic[self.hardware][emulator] = {project: 0 for project in self.project_list}

        self.project_primary_factors = ''

        if self.hardware == 'Z1':
            if hasattr(config, 'Z1_project_primary_factors'):
                self.project_primary_factors = config.Z1_project_primary_factors
        elif self.hardware == 'Z2':
            if hasattr(config, 'Z2_project_primary_factors'):
                self.project_primary_factors = config.Z1_project_primary_factors

        for rack in self.palladium_dic['rack'].keys():
            for cluster in self.palladium_dic['rack'][rack]['cluster'].keys():
                for logic_drawer in self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"].keys():
                    for domain, palladium_record in self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'].items():
                        owner = palladium_record['owner']
                        pid = palladium_record['pid']

                        if pid == 0 or pid == '0':
                            continue

                        exec_host = pid.split(':')[0]

                        if exec_host:
                            project_dic = common.get_project_info(self.project_primary_factors, self.project_proportion_dic, execute_host=exec_host, user=owner)

                            if project_dic:
                                for project in project_dic.keys():
                                    if project not in self.palladium_cost_dic[self.hardware][emulator]:
                                        self.palladium_cost_dic[self.hardware][emulator].setdefault(project, project_dic[project])
                                    else:
                                        self.palladium_cost_dic[self.hardware][emulator][project] += project_dic[project]

                                    if project not in self.project_list:
                                        self.project_list.append(project)
                            else:
                                self.palladium_cost_dic[self.hardware][emulator]['others'] += 1

    def update_cost_file(self, emulator):
        """
        Update cost_file for specified emulator.
        """
        cost_file = str(config.db_path) + '/' + str(self.hardware) + '/' + str(emulator) + '/cost'
        current_project_dic = self.palladium_cost_dic[self.hardware][emulator]
        total_cost_dic = {}

        logger.critical('>>> Updating palladium cost file ...')

        # Parsing cost file and get cost dic
        if not os.path.exists(cost_file):
            total_cost_dic[self.current_date] = current_project_dic
        else:
            with open(cost_file, 'r') as CF:
                for line in CF:
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

            # Get cost file total project list
            total_project_list = list(total_cost_dic[list(total_cost_dic.keys())[0]].keys())
            total_project_list = list(set(total_project_list).union(set(list(current_project_dic.keys()))))

            for project in total_project_list:
                for date in total_cost_dic:
                    if project not in total_cost_dic[date]:
                        total_cost_dic[date][project] = 0

                if project not in current_project_dic:
                    current_project_dic[project] = 0

            if self.current_date in total_cost_dic:
                total_cost_dic[self.current_date] = {project: (total_cost_dic[self.current_date][project] + current_project_dic[project]) for project in current_project_dic.keys()}
            else:
                total_cost_dic[self.current_date] = current_project_dic

        # write new cost file
        with open(cost_file, 'w') as CF:
            for date in total_cost_dic:
                line = date + ' '

                for project in total_cost_dic[date]:
                    line += '{:<15}'.format(r'%s:%s' % (project, str(total_cost_dic[date][project])))

                logger.debug('    ' + line)
                CF.write(line + '\n')

    def reconfig_cost_file(self):
        logger.info('Generate new cost infomation ...')

        if not os.path.exists(config.db_path):
            logger.error('Could not find db path: %s' % str(config.db_path))

        for dir_path, dir_name_list, file_name_list in os.walk(config.db_path):
            for file_name in file_name_list:
                if re.match(r'^cost$', file_name):
                    file_path = os.path.join(dir_path, file_name)
                    os.rename(os.path.join(dir_path, file_name), r'%s.%s' % (file_path, datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')))

                if re.match(r'^\d+$', file_name):
                    file_path = os.path.join(dir_path, file_name)
                    self.palladium_dic = {}

                    with open(file_path, 'r') as ff:
                        self.palladium_dic = yaml.load(ff, Loader=yaml.FullLoader)

                    dir_item_list = dir_path.split('/')

                    if self.palladium_dic['hardware'].find('Z1') != -1:
                        self.hardware = 'Z1'
                    elif self.palladium_dic['hardware'].find('Z2') != -1:
                        self.hardware = 'Z2'
                    else:
                        continue

                    emulator = self.palladium_dic['emulator']
                    self.current_date = r'%s-%s-%s' % (dir_item_list[-3], dir_item_list[-2], dir_item_list[-1])

                    # get self.palladium_cost_dic.
                    self.get_cost_info()

                    # Update palladium cost file.
                    self.update_cost_file(emulator)


#################
# Main Function #
#################
def main():
    args = read_args()
    my_sampling = Sampling(args.hardware)

    if not args.reconfig:
        my_sampling.sampling()
    else:
        my_sampling.reconfig_cost_file()


if __name__ == '__main__':
    main()
