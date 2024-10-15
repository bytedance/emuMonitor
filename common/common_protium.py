import os
import re
import sys
import copy
import yaml

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']))
from common import common
from config import config


def get_protium_sys_info(path=None, command=None):
    """
    Get protium sys information.
    """
    logger = common.get_logger()
    protium_sys_info_list = []
    if not path:
        path = os.path.expanduser('~')

    command = 'cd %s && %s' % (str(path), str(command))

    if not command:
        logger.error("Could not find protium sys command, please check config.py!")
        sys.exit(1)

    (return_code, stdout, stderr) = common.run_command(command)

    for line in str(stdout, 'utf-8').split('\n'):
        protium_sys_info_list.append(line.strip())

    return protium_sys_info_list


def parse_protium_sys_info(protium_sys_info_list=None):
    """
    Parsing protium sys information list
    Return protium board info dict:
    protium_board_info_dic = {
        <board_uuid>:
            {
                'board_uuid': <board_uuid>,
                'board_id': <board_id>,
                'board_ip': <board_ip>,
                'used_record':[
                    {
                        'FPGA': <fpga_id>,
                        'user': <user>,
                        'host': <host>,
                        'pid': <pid>,
                        'started_time': <started_time>
                    },
                    ...
                ]
    }
    """
    logger = common.get_logger()
    board_uuid = None
    protium_board_info_dic = {}

    if not isinstance(protium_sys_info_list, list):
        logger.error("Invalid protium information, please check config.py!")
        sys.exit(1)

    for line in protium_sys_info_list:
        if my_match := re.match(r'^\S+\s+\S+\s+(\d+)\s+([\d+\.]+)\s+\(\S+\)\s+\((\d+)\).*$', line):
            board_uuid = my_match.group(1)

            protium_board_info_dic.setdefault(board_uuid, {})
            protium_board_info_dic[board_uuid]['board_uuid'] = board_uuid
            protium_board_info_dic[board_uuid]['board_id'] = my_match.group(3)
            protium_board_info_dic[board_uuid]['board_ip'] = my_match.group(2)
            protium_board_info_dic[board_uuid]['used_record'] = []
        elif my_match := re.match(r'^\s*FPGA\s+(\S+)\s+\|\s*$', line):
            if not board_uuid or board_uuid not in protium_board_info_dic:
                logger.warning("Invalid line: %s, ignore." % str(line))
                continue

            record_dic = {
                'FPGA': my_match.group(1),
                'user': '--',
                'host': '--',
                'pid': '--',
                'started_time': '--'
            }
            protium_board_info_dic[board_uuid]['used_record'].append(record_dic)
        elif my_match := re.match(r'^\s*FPGA\s+(\S+)\s+\|\s+(\S+):(\S+):(\S+)\s+@\s+(\S+)\s*$', line):
            if not board_uuid or board_uuid not in protium_board_info_dic:
                logger.warning("Invalid line: %s, ignore." % str(line))
                continue

            record_dic = {
                'FPGA': my_match.group(1),
                'user': my_match.group(2),
                'host': my_match.group(3),
                'pid': my_match.group(4),
                'started_time': my_match.group(5)
            }
            protium_board_info_dic[board_uuid]['used_record'].append(record_dic)

    return protium_board_info_dic


def multifilter_protium_dic(
        protium_dic,
        specified_board_list=[],
        specified_ip_list=[],
        specified_fpga_list=[],
        specified_user_list=[],
        specified_submit_host_list=[],
        specified_pid_list=[],
):
    """
    return filtered protium information(dict)
    """
    filtered_protium_dic = copy.deepcopy(protium_dic)

    if protium_dic:
        for board_uuid in protium_dic:
            # Filter board id
            if specified_board_list and ('ALL' not in specified_board_list) and (protium_dic[board_uuid]['board_id'] not in specified_board_list):
                del filtered_protium_dic[board_uuid]
                continue

            # Filter board ip
            if specified_ip_list and ('ALL' not in specified_ip_list) and (protium_dic[board_uuid]['board_ip'] not in specified_ip_list):
                del filtered_protium_dic[board_uuid]
                continue

            del_idx_list = []

            if 'ALL' not in specified_fpga_list or 'ALL' not in specified_user_list or 'ALL' not in specified_submit_host_list or 'ALL' not in specified_pid_list:
                if not protium_dic[board_uuid]['used_record']:
                    del filtered_protium_dic[board_uuid]

            # Filter FPGA & user & host & pid
            for i in range(len(protium_dic[board_uuid]['used_record'])):
                used_record = protium_dic[board_uuid]['used_record'][i]

                if specified_fpga_list and ('ALL' not in specified_fpga_list) and (used_record['FPGA'] not in specified_fpga_list):
                    del_idx_list.append(i)
                    continue

                if specified_user_list and ('ALL' not in specified_user_list) and (used_record['user'] not in specified_user_list):
                    del_idx_list.append(i)
                    continue

                if specified_submit_host_list and ('ALL' not in specified_submit_host_list) and (used_record['host'] not in specified_submit_host_list):
                    del_idx_list.append(i)
                    continue

                if specified_pid_list and ('ALL' not in specified_pid_list) and (used_record['pid'] not in specified_pid_list):
                    del_idx_list.append(i)
                    continue

            for i in reversed(del_idx_list):
                del filtered_protium_dic[board_uuid]['used_record'][i]

    return filtered_protium_dic


def get_protium_host_info():
    """
    hardware_host_dic = {<hardware>: {'test_server_host': <test_server_host>, 'test_server': <test_server>
                                        'project_list': <project_list>, 'project_primary_factors': '',
                                        ''default_project_cost_dic': <default_project_cost_dic>, 'domain_dic': <domain_dic>}}
    """
    logger = common.get_logger()
    hardware_dic = {}
    protium_config_dir = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/protium/')

    if not os.path.exists(protium_config_dir):
        logger.error("Could not find any hardware information, please check!")
        sys.exit(1)

    for hardware in os.listdir(protium_config_dir):
        if re.match('label', hardware):
            continue

        hardware_dic.setdefault(hardware, {})
        hardware_config_dir = os.path.join(protium_config_dir, '%s/' % str(hardware))

        for file in os.listdir(hardware_config_dir):
            if re.match(r'project_list', file):
                file_path = os.path.join(hardware_config_dir, file)
                hardware_dic[hardware]['project_list'], hardware_dic[hardware]['default_project_cost_dic'] = common.parse_project_list_file(file_path)
                hardware_dic[hardware]['default_project_cost_dic']['others'] = 0

            if not re.match(r'config.py', file):
                continue

            file_path = os.path.join(hardware_config_dir, file)

            with open(file_path, 'r') as ff:
                for line in ff:
                    if my_match := re.match(r'host\s*=\s*\"(.*)\"\s*', line):
                        hardware_dic[hardware]['host'] = my_match.group(1)
                    elif my_match := re.match(r'ptmRun\s*=\s*(\S+)\s*', line):
                        hardware_dic[hardware]['ptmRun'] = my_match.group(1).replace('"', '')
                    elif my_match := re.match(r'ptmRun_bsub_command\s*=\s*(\S+)\s*', line):
                        hardware_dic[hardware]['ptmRun_bsub_command'] = my_match.group(1).replace('"', '')
                    elif my_match := re.match(r'PTM_SYS_IP_LIST\s*=\s*\"(.*)\"\s*', line):
                        hardware_dic[hardware]['PTM_SYS_IP_LIST'] = my_match.group(1)
                    elif my_match := re.match(r'project_primary_factors\s*=\s*\"(.*)\"\s*', line):
                        hardware_dic[hardware]['project_primary_factors'] = my_match.group(1)

        ssh_command = ''

        check_info_command = '%s export PTM_SYSTEM_IP_LIST=%s;%s %s -init %s' % (
            ssh_command,
            hardware_dic[hardware]['PTM_SYS_IP_LIST'],
            hardware_dic[hardware]['ptmRun_bsub_command'],
            hardware_dic[hardware]['ptmRun'],
            config.ptmRun_check_info_file
        )

        hardware_dic[hardware]['check_info_command'] = check_info_command

        hardware_domain_file = os.path.join(config.db_path, 'protium/%s/board_list.yaml' % str(hardware))

        if not os.path.exists(hardware_domain_file):
            logger.error("Could not find %s domain list, please use protium_sample -H %s first!" % (hardware, hardware))
            hardware_dic[hardware]['board_list'] = []
        else:
            with open(hardware_domain_file, 'r') as df:
                hardware_dic[hardware].update(yaml.load(df, Loader=yaml.FullLoader))

    return hardware_dic
