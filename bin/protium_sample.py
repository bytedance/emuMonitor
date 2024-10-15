#!/ic/software/tools/python3/3.8.8/bin/python3
# -*- coding: utf-8 -*-
################################
# File Name   : ptm_sample.py
# Author      : zhangjingwen.silvia
# Created On  : 2024-02-21 15:28:22
# Description :
################################
import os
import sys
import yaml
import logging
import datetime
import argparse

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']))
from config import config
from common import common, common_protium

os.environ["PYTHONUNBUFFERED"] = '1'
logger = common.get_logger(level=logging.DEBUG)


def read_args():
    """
    Read in arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-H', '--hardware',
                        default='X1',
                        help='Specify hardware, default is "X1".')

    args = parser.parse_args()

    return args


class PtmSampling:
    """
    Protium information sampling
    """
    def __init__(self, hardware):
        self.hardware = hardware
        self.hardware_dic = common_protium.get_protium_host_info()

        if hardware not in self.hardware_dic:
            logger.error("Invalid hardware, pelase check!")

        self.check_info_command = self.hardware_dic[hardware]['check_info_command']

        logger.info("Check protium information command: %s" % str(self.check_info_command))

        # Get project related information.
        project_list_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + r'/config/protium/%s/project_list' % self.hardware
        project_execute_host_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/protium/%s/project_execute_host' % self.hardware
        project_user_file = str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/protium/%s/project_user' % self.hardware

        self.project_list, self.default_project_cost_dic = common.parse_project_list_file(project_list_file)
        self.project_list.append('others')
        self.default_project_cost_dic['others'] = 0

        self.project_execute_host_dic = common.parse_project_proportion_file(project_execute_host_file)
        self.project_user_dic = common.parse_project_proportion_file(project_user_file)

        self.project_proportion_dic = {'execute_host': self.project_execute_host_dic, 'user': self.project_user_dic}

    def sampling(self):
        # db
        current_time_utc = datetime.datetime.now()
        self.current_year = current_time_utc.strftime('%Y')
        self.current_month = current_time_utc.strftime('%m')
        self.current_day = current_time_utc.strftime('%d')
        self.current_date = current_time_utc.strftime('%Y-%m-%d')
        self.current_time = current_time_utc.strftime('%H-%M-%S')

        # db path
        db_path = os.path.join(config.db_path, 'protium/%s/%s/%s/%s/' % (self.hardware, str(self.current_year), str(self.current_month), str(self.current_day)))

        if not os.path.exists(db_path):
            try:
                os.makedirs(db_path)
            except Exception as error:
                logger.error("Could nod mkdir db directory, because ERROR %s" % str(error))
                sys.exit(1)

        # sampling protium board information
        logger.info("Sampling protium sys information...")

        ptmrun_path = os.path.join(os.path.expanduser('~'), self.hardware)

        if not os.path.exists(ptmrun_path):
            os.makedirs(ptmrun_path)

        protium_sys_info_list = common_protium.get_protium_sys_info(path=ptmrun_path, command=self.check_info_command)
        protium_dic = common_protium.parse_protium_sys_info(protium_sys_info_list)

        if not protium_dic:
            logger.error('Could not find any valid information, please check!')
            sys.exit(1)

        logger.info("Sampling protium sys information done.")

        domain_list_file = os.path.join(str(config.db_path), 'protium/%s/board_list.yaml' % str(self.hardware))

        board_dic = {'board_list': []}

        for board_uuid in protium_dic:
            board_dic['board_list'].append(protium_dic[board_uuid]['board_id'])

        with open(domain_list_file, 'w') as df:
            df.write(yaml.dump(board_dic, allow_unicode=True))

        # Utilziation
        utilziation = self.get_protium_utilization(protium_dic)
        utilziation_file_path = os.path.join(config.db_path, 'protium/%s/utilization' % self.hardware)

        # Cost
        cost_dic = self.get_protium_cost(protium_dic)
        cost_file_path = os.path.join(config.db_path, 'protium/%s/cost' % self.hardware)

        # Save inforamtion to database, including utilization and board based information.
        logger.info("Save to db ...")

        # sampling file path
        db_file_path = os.path.join(db_path, self.current_time)

        with open(db_file_path, 'w') as DF:
            DF.write(yaml.dump(protium_dic, allow_unicode=True))

        with open(utilziation_file_path, 'a+') as UF:
            UF.write('%s-%s: %s\n' % (self.current_date, self.current_time, utilziation))

        with open(cost_file_path, 'a+') as UF:
            line = '%s-%s ' % (self.current_date, self.current_time)

            for project, sampling_num in cost_dic.items():
                line += ' %s:%s' % (str(project), str(sampling_num))

            UF.write(line + '\n')

        self.get_protium_board_info(protium_dic=protium_dic)

        logger.info("Done")

    @staticmethod
    def get_protium_utilization(protium_dic=None):
        total_board_num = len(protium_dic.keys())
        used_board_num = 0
        utilization = 0

        for _, board_info_dic in protium_dic.items():
            if board_info_dic['used_record']:
                used_board_num += 1

        if total_board_num:
            utilization = round((used_board_num / total_board_num), 2)
        return utilization

    def get_protium_cost(self, protium_dic=None):
        """
        Get emulator sampling record project infomation, generate self.palladium_cost_dic.
        self.palladium_cost_dic = {<Project>: <sampling_counts>}
        <project> including all project from self.project_list, and self.project*file if the project sampling is not 0
        """
        cost_dic = {project: 0 for project in self.project_list}
        project_primary_factors = self.hardware_dic[self.hardware]['project_primary_factors']

        for _, board_info_dic in protium_dic.items():
            if 'used_record' in board_info_dic:
                for record_dic in board_info_dic['used_record']:
                    host = record_dic['host']
                    user = record_dic['user']

                    if host == '--' or user == '--':
                        continue

                    if host and user:
                        project_dic = common.get_project_info(project_primary_factors, self.project_proportion_dic, execute_host=host, user=user)

                        if project_dic:
                            for project in project_dic.keys():
                                if project not in cost_dic:
                                    cost_dic.setdefault(project, project_dic[project])
                                else:
                                    cost_dic[project] += project_dic[project]

                                if project not in self.project_list:
                                    self.project_list.append(project)
                        else:
                            cost_dic['others'] += 1

        return cost_dic

    def get_protium_board_info(self, protium_dic=None):
        """
        get palladium detail info based on domain
        """
        if not protium_dic:
            return

        project_primary_factors = self.hardware_dic[self.hardware]['project_primary_factors']

        detail_info_dir = os.path.join(config.db_path, 'protium/%s/detail' % (self.hardware))

        if not os.path.exists(detail_info_dir):
            os.makedirs(detail_info_dir)

        utilization_detail_file = os.path.join(detail_info_dir, '%s.%s.utilization' % (str(self.current_year), str(self.current_month)))
        cost_detail_file = os.path.join(detail_info_dir, '%s.%s.cost' % (str(self.current_year), str(self.current_month)))

        if not os.path.exists(utilization_detail_file):
            utilization_detail_file_dic = {}
        else:
            with open(utilization_detail_file, 'r') as uf:
                utilization_detail_file_dic = yaml.load(uf, Loader=yaml.FullLoader)

        if not os.path.exists(cost_detail_file):
            cost_detail_file_dic = {}
        else:
            with open(cost_detail_file, 'r') as cf:
                cost_detail_file_dic = yaml.load(cf, Loader=yaml.FullLoader)

        utilization_detail_file_dic.setdefault(self.current_date, {})
        cost_detail_file_dic.setdefault(self.current_date, {})

        for board_uuid in protium_dic:
            board_id = protium_dic[board_uuid]['board_id']
            utilization_detail_file_dic[self.current_date].setdefault(board_id, {'sampling': 0, 'used': 0})
            utilization_detail_file_dic[self.current_date][board_id]['sampling'] += 1

            cost_detail_file_dic[self.current_date].setdefault(board_id, {})

            if not protium_dic[board_uuid]['used_record']:
                continue

            utilization_detail_file_dic[self.current_date][board_id]['used'] += 1

            for used_record in protium_dic[board_uuid]['used_record']:
                if used_record['user'] and used_record['host']:
                    project_dic = common.get_project_info(project_primary_factors, self.project_proportion_dic, execute_host=used_record['host'], user=used_record['user'])

                    for project in project_dic:
                        if project in cost_detail_file_dic[self.current_date][board_id]:
                            cost_detail_file_dic[self.current_date][board_id][project] += project_dic[project]
                        else:
                            cost_detail_file_dic[self.current_date][board_id][project] = project_dic[project]

        with open(utilization_detail_file, 'w') as uf:
            uf.write(yaml.dump(utilization_detail_file_dic, allow_unicode=True))

        with open(cost_detail_file, 'w') as cf:
            cf.write(yaml.dump(cost_detail_file_dic, allow_unicode=True))


################
# Main Process #
################
def main():
    args = read_args()

    if args.hardware:
        protium_sample = PtmSampling(args.hardware)
        protium_sample.sampling()


if __name__ == '__main__':
    main()
