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
                        help='Enable deabut mode.')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.WARNING, datefmt='%Y-%m-%d %H:%M:%S')

    return (args.hardware)


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
        self.project_list = self.parse_project_list_file()
        self.project_list.append('others')
        self.project_execute_host_dic = self.parse_project_proportion_file(config.project_execute_host_file)
        self.project_user_dic = self.parse_project_proportion_file(config.project_user_file)
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
                logging.error('*Error*: Failed on creating database directory "' + str(self.current_db_path) + '".')
                logging.error('         ' + str(error))
                sys.exit(1)

    def sampling(self):
        """
        Sample palladium usage information.
        """
        logging.critical('>>> Sampling palladium usage information ...')

        # Get palladium_dic.
        test_server_info = common_palladium.get_test_server_info(self.hardware)
        self.palladium_dic = common_palladium.parse_test_server_info(test_server_info)

        if self.palladium_dic:
            # Print debug information.
            logging.debug('    Sample Time : ' + str(self.current_year) + str(self.current_month) + str(self.current_day) + '_' + str(self.current_time))
            logging.debug('    Hardware : ' + self.palladium_dic['hardware'])
            logging.debug('    Emulator : ' + self.palladium_dic['emulator'])
            logging.debug('    Status : ' + self.palladium_dic['emulator_status'])
            logging.debug('    Utilization : ' + str(self.palladium_dic['utilization']))

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

    def parse_project_list_file(self):
        """
        Parse project_list_file and return List "project_list".
        """
        project_list = []

        if config.project_list_file and os.path.exists(config.project_list_file):
            with open(config.project_list_file, 'r') as PLF:
                for line in PLF.readlines():
                    line = line.strip()

                    if re.match(r'^\s*#.*$', line) or re.match(r'^\s*$', line):
                        continue
                    else:
                        if line not in project_list:
                            project_list.append(line)

        return project_list

    def parse_project_proportion_file(self, project_proportion_file):
        """
        Parse config.project_*_file and return dictory "project_proportion_dic".
        """
        project_proportion_dic = {}

        if project_proportion_file and os.path.exists(project_proportion_file):
            with open(project_proportion_file, 'r') as PPF:
                for line in PPF.readlines():
                    line = line.strip()

                    if re.match(r'^\s*#.*$', line) or re.match(r'^\s*$', line):
                        continue
                    elif re.match(r'^(\S+)\s*:\s*(\S+)$', line):
                        my_match = re.match(r'^(\S+)\s*:\s*(\S+)$', line)
                        item = my_match.group(1)
                        project = my_match.group(2)

                        if item in project_proportion_dic.keys():
                            logging.warning('*Warning*: "' + str(item) + '": repeated item on "' + str(project_proportion_file) + '", ignore.')
                            continue
                        else:
                            project_proportion_dic[item] = {project: 1}
                    elif re.match(r'^(\S+)\s*:\s*(.+)$', line):
                        my_match = re.match(r'^(\S+)\s*:\s*(.+)$', line)
                        item = my_match.group(1)
                        project_string = my_match.group(2)
                        tmp_dic = {}

                        for project_setting in project_string.split():
                            if re.match(r'^(\S+)\((0.\d+)\)$', project_setting):
                                my_match = re.match(r'^(\S+)\((0.\d+)\)$', project_setting)
                                project = my_match.group(1)
                                project_proportion = my_match.group(2)

                                if project in tmp_dic.keys():
                                    tmp_dic = {}
                                    break
                                else:
                                    tmp_dic[project] = float(project_proportion)
                            else:
                                tmp_dic = {}
                                break

                        if not tmp_dic:
                            logging.warning('*Warning*: invalid line on "' + str(project_proportion_file) + '", ignore.')
                            logging.warning('           ' + str(line))
                            continue
                        else:
                            sum_proportion = sum(list(tmp_dic.values()))

                            if sum_proportion == 1.0:
                                project_proportion_dic[item] = tmp_dic
                            else:
                                logging.warning('*Warning*: invalid line on "' + str(project_proportion_file) + '", ignore.')
                                logging.warning('           ' + str(line))
                                continue
                    else:
                        logging.warning('*Warning*: invalid line on "' + str(project_proportion_file) + '", ignore.')
                        logging.warning('           ' + str(line))
                        continue

        return project_proportion_dic

    def get_project_info(self, execute_host, user):
        """
        Get project information based on submit_host/execute_host/user.
        """
        project_dic = {}
        factor_dic = {'execute_host': execute_host, 'user': user}

        if config.project_primary_factors:
            project_primary_factor_list = config.project_primary_factors.split()

            for project_primary_factor in project_primary_factor_list:
                if project_primary_factor not in factor_dic.keys():
                    logging.error('*Error*: "' + str(project_primary_factor) + '": invalid project_primary_factors setting on config file.')
                    sys.exit(1)
                else:
                    factor_value = factor_dic[project_primary_factor]
                    project_proportion_dic = {}

                    if factor_value in self.project_proportion_dic[project_primary_factor].keys():
                        project_proportion_dic = self.project_proportion_dic[project_primary_factor][factor_value]

                    if project_proportion_dic:
                        project_dic = project_proportion_dic
                        break
                    else:
                        continue

        return project_dic

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

        for rack in self.palladium_dic['rack'].keys():
            for cluster in self.palladium_dic['rack'][rack]['cluster'].keys():
                for logic_drawer in self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"].keys():
                    for domain, palladium_record in self.palladium_dic['rack'][rack]['cluster'][cluster]["logic_drawer"][logic_drawer]['domain'].items():
                        owner = palladium_record['owner']
                        pid = palladium_record['pid']

                        if pid == 0:
                            continue

                        exec_host = pid.split(':')[0]

                        if exec_host:
                            project_dic = self.get_project_info(execute_host=exec_host, user=owner)

                            if project_dic:
                                for project in project_dic.keys():
                                    if project not in self.palladium_cost_dic[self.hardware][emulator]:
                                        self.palladium_cost_dic[self.hardware][emulator].setdefault(project, project_dic[project])
                                    else:
                                        self.palladium_cost_dic[self.hardware][emulator][project] += project_dic[project]

                                    if project not in self.project_list:
                                        self.project_list.append(project)

    def update_cost_file(self, emulator):
        """
        Update cost_file for specified emulator.
        """
        cost_file = str(config.db_path) + '/' + str(self.hardware) + '/' + str(emulator) + '/cost'
        current_project_dic = self.palladium_cost_dic[self.hardware][emulator]
        total_cost_dic = {}

        logging.critical('>>> Updating palladium cost file ...')

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
                        logging.warning('*Warning*: Could not find valid infomation in cost file line: ' + line + '!')
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

                logging.debug('    ' + line)
                CF.write(line + '\n')


#################
# Main Function #
#################
def main():
    (hardware) = read_args()
    my_sampling = Sampling(hardware)
    my_sampling.sampling()


if __name__ == '__main__':
    main()
