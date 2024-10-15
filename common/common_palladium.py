import os
import re
import sys
import copy
import socket
import yaml

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']))
from config import config
from common import common


def get_test_server_info(hardware, test_server, host):
    test_server_info = []

    # get current server ip and hostname
    current_hostname = socket.gethostname()
    current_ip = socket.gethostbyname(current_hostname)

    if not test_server:
        common.print_warning('*Warning*: test_server path is not specified on config/config.py.')
    else:
        command = test_server

        if host.strip() != str(current_ip).strip() and host.strip() != str(current_hostname).strip():
            command = 'ssh ' + str(host) + ' "' + str(command) + '"'
        else:
            command = '"' + str(command) + '"'

        (return_code, stdout, stderr) = common.run_command(command)

        for line in str(stdout, 'utf-8').split('\n'):
            test_server_info.append(line.strip())

    return test_server_info


def parse_test_server_info(test_server_info):
    palladium_dic = {}

    emulator_compile = re.compile(r'^\s*Emulator:\s*(.+?)\s* Hardware:\s*(.+?)\s* Configmgr:\s*(.+?)\s* Status:\s*(.+?)\s*$')
    rack_clusters_compile = re.compile(r'^\s*Rack\s*(\d+)\s*has\s*(\d+)\s*clusters\s*$')
    cluster_drawers_compile = re.compile(r'^Cluster\s*(\d+)\s*has\s*(\d+)\s*logic drawers\s+CCD:\s*(.+?)\s*$')
    drawer_domains_compile = re.compile(r'^\s*Logic drawer\s*(\d+)\s*has\s*(\d+)\s*domains\s+Logic drawer:\s*(.+?)\s*$')
    domain_compile = re.compile(r'^\s*(\d+\.\d+)\s+(\S+)\s+(\S+)\s+(\S+\s+\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$')

    current_rack = 0
    current_cluster = 0
    current_logic_drawer = 0

    owner_list = []

    for line in test_server_info:
        if emulator_compile.match(line):
            my_match = emulator_compile.match(line)
            emulator = my_match.group(1)
            hardware = my_match.group(2)
            emulator_status = my_match.group(4)
            palladium_dic = {'emulator': emulator,
                             'hardware': hardware,
                             'emulator_status': emulator_status,
                             'utilization': 0,
                             'domain_line_num': 0,
                             'rack_list': [],
                             'cluster_list': [],
                             'logic_drawer_list': [],
                             'domain_list': [],
                             'owner_list': [],
                             'pid_list': [],
                             'tpod_list': [],
                             'design_list': [],
                             'rack': {}}
        elif rack_clusters_compile.match(line):
            my_match = rack_clusters_compile.match(line)
            rack = my_match.group(1)
            current_rack = rack
            palladium_dic['rack'].setdefault(rack, {'cluster': {}})

            if rack not in palladium_dic['rack_list']:
                palladium_dic['rack_list'].append(rack)
        elif cluster_drawers_compile.match(line):
            my_match = cluster_drawers_compile.match(line)
            cluster = my_match.group(1)
            current_cluster = cluster
            ccd_status = my_match.group(3)
            palladium_dic['rack'][current_rack]['cluster'].setdefault(cluster, {'ccd_status': ccd_status, 'logic_drawer': {}})

            if cluster not in palladium_dic['cluster_list']:
                palladium_dic['cluster_list'].append(cluster)
        elif drawer_domains_compile.match(line):
            my_match = drawer_domains_compile.match(line)
            logic_drawer = my_match.group(1)
            current_logic_drawer = logic_drawer
            logic_drawer_status = my_match.group(3)
            palladium_dic['rack'][current_rack]['cluster'][current_cluster]['logic_drawer'].setdefault(logic_drawer, {'logic_drawer_status': logic_drawer_status, 'domain': {}})

            if logic_drawer not in palladium_dic['logic_drawer_list']:
                palladium_dic['logic_drawer_list'].append(logic_drawer)
        elif domain_compile.match(line):
            my_match = domain_compile.match(line)
            domain = my_match.group(1)
            owner = my_match.group(2)
            owner_list.append(owner)
            pid = my_match.group(3)
            tpod = my_match.group(4)
            design = my_match.group(5)
            elaptime = my_match.group(6)
            reservedkey = my_match.group(7)
            palladium_dic['domain_line_num'] += 1
            palladium_dic['rack'][current_rack]['cluster'][current_cluster]['logic_drawer'][current_logic_drawer]['domain'].setdefault(domain, {'owner': owner,
                                                                                                                                                'pid': pid,
                                                                                                                                                'tpod': tpod,
                                                                                                                                                'design': design,
                                                                                                                                                'elaptime': elaptime,
                                                                                                                                                'reservedkey': reservedkey})

            if domain not in palladium_dic['domain_list']:
                palladium_dic['domain_list'].append(domain)

            if owner not in palladium_dic['owner_list']:
                palladium_dic['owner_list'].append(owner)

            if pid not in palladium_dic['pid_list']:
                palladium_dic['pid_list'].append(pid)

            if tpod not in palladium_dic['tpod_list']:
                palladium_dic['tpod_list'].append(tpod)

            if design not in palladium_dic['design_list']:
                palladium_dic['design_list'].append(design)

    if owner_list:
        utilization = round(1-owner_list.count('NONE')/len(owner_list), 2)
        palladium_dic['utilization'] = utilization

    return palladium_dic


def filter_palladium_dic(
        palladium_dic,
        specified_rack='',
        specified_cluster='',
        specified_logic_drawer='',
        specified_domain='',
        specified_owner='',
        specified_pid='',
        specified_tpod='',
        specified_design=''
):
    filtered_palladium_dic = copy.deepcopy(palladium_dic)

    if palladium_dic:
        for rack in palladium_dic['rack'].keys():
            # Filter rack
            if specified_rack and (specified_rack != 'ALL') and (specified_rack != rack):
                del filtered_palladium_dic['rack'][rack]
            else:
                for cluster in palladium_dic['rack'][rack]['cluster'].keys():
                    # Filter cluster
                    if specified_cluster and (specified_cluster != 'ALL') and (specified_cluster != cluster):
                        del filtered_palladium_dic['rack'][rack]['cluster'][cluster]
                    else:
                        for logic_drawer in palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'].keys():
                            # Filter logic_drawer
                            if specified_logic_drawer and (specified_logic_drawer != 'ALL') and (specified_logic_drawer != logic_drawer):
                                del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]
                            else:
                                for domain in palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'].keys():
                                    # Filter domain
                                    if specified_domain and (specified_domain != 'ALL') and (specified_domain != domain):
                                        del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                    else:
                                        # Filter owner
                                        owner = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['owner']

                                        if specified_owner and (specified_owner != 'ALL') and (specified_owner != owner):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

                                        # Filter pid
                                        pid = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['pid']

                                        if specified_pid and (specified_pid != 'ALL') and (specified_pid != pid):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

                                        # Filter tpod
                                        tpod = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['tpod']

                                        if specified_tpod and (specified_tpod != 'ALL') and (specified_tpod != tpod):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

                                        # Filter design
                                        design = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['design']

                                        if specified_design and (specified_design != 'ALL') and (specified_design != design):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

        # Update domain_line_num.
        filtered_palladium_dic['domain_line_num'] = 0

        for rack in filtered_palladium_dic['rack'].keys():
            for cluster in filtered_palladium_dic['rack'][rack]['cluster'].keys():
                for logic_drawer in filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'].keys():
                    for domain in filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'].keys():
                        filtered_palladium_dic['domain_line_num'] += 1

    return filtered_palladium_dic


def multifilter_palladium_dic(
        palladium_dic,
        specified_rack_list=[],
        specified_cluster_list=[],
        specified_logic_drawer_list=[],
        specified_domain_list=[],
        specified_owner_list=[],
        specified_pid_list=[],
        specified_tpod_list=[],
        specified_design_list=[]
):
    filtered_palladium_dic = copy.deepcopy(palladium_dic)

    if palladium_dic:
        for rack in palladium_dic['rack'].keys():
            # Filter rack
            if specified_rack_list and ('ALL' not in specified_rack_list) and (rack not in specified_rack_list):
                del filtered_palladium_dic['rack'][rack]
            else:
                for cluster in palladium_dic['rack'][rack]['cluster'].keys():
                    # Filter cluster
                    if specified_cluster_list and ('ALL' not in specified_cluster_list) and (cluster not in specified_cluster_list):
                        del filtered_palladium_dic['rack'][rack]['cluster'][cluster]
                    else:
                        for logic_drawer in palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'].keys():
                            # Filter logic_drawer
                            if specified_logic_drawer_list and ('ALL' not in specified_logic_drawer_list) and (logic_drawer not in specified_logic_drawer_list):
                                del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]
                            else:
                                for domain in palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'].keys():
                                    # Filter domain
                                    if specified_domain_list and ('ALL' not in specified_domain_list) and (domain not in specified_domain_list):
                                        del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                    else:
                                        # Filter owner
                                        owner = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['owner']

                                        if specified_owner_list and ('ALL' not in specified_owner_list) and (owner not in specified_owner_list):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

                                        # Filter pid
                                        pid = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['pid']

                                        if specified_pid_list and ('ALL' not in specified_pid_list) and (pid not in specified_pid_list):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

                                        # Filter tpod
                                        tpod = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['tpod']

                                        if specified_tpod_list and ('ALL' not in specified_tpod_list) and (tpod not in specified_tpod_list):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

                                        # Filter design
                                        design = palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]['design']

                                        if specified_design_list and ('ALL' not in specified_design_list) and (design not in specified_design_list):
                                            del filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'][domain]
                                            continue

        # Update domain_line_num.
        filtered_palladium_dic['domain_line_num'] = 0

        for rack in filtered_palladium_dic['rack'].keys():
            for cluster in filtered_palladium_dic['rack'][rack]['cluster'].keys():
                for logic_drawer in filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'].keys():
                    for domain in filtered_palladium_dic['rack'][rack]['cluster'][cluster]['logic_drawer'][logic_drawer]['domain'].keys():
                        filtered_palladium_dic['domain_line_num'] += 1

    return filtered_palladium_dic


def get_palladium_host_info():
    """
    hardware_host_dic = {<hardware>: {'test_server_host': <test_server_host>, 'test_server': <test_server>
                                        'project_list': <project_list>, 'project_primary_factors': '',
                                        ''default_project_cost_dic': <default_project_cost_dic>, 'domain_dic': <domain_dic>}}
    """
    logger = common.get_logger()
    hardware_dic = {}
    palladium_config_dir = os.path.join(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config/palladium/')

    if not os.path.exists(palladium_config_dir):
        logger.error("Could not find any hardware information, please check!")
        sys.exit(1)

    for hardware in os.listdir(palladium_config_dir):
        if re.match('label', hardware):
            continue

        hardware_dic.setdefault(hardware, {})
        hardware_config_dir = os.path.join(palladium_config_dir, '%s/' % str(hardware))

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
                    if my_match := re.match(r'test_server\s*=\s*(\S+)\s*', line):
                        hardware_dic[hardware]['test_server'] = my_match.group(1)
                    elif my_match := re.match(r'test_server_host\s*=\s*(\S+)\s*', line):
                        hardware_dic[hardware]['test_server_host'] = my_match.group(1).replace('"', '')
                    elif my_match := re.match(r'project_primary_factors\s*=\s*\"(.*)\"\s*', line):
                        hardware_dic[hardware]['project_primary_factors'] = my_match.group(1)

        hardware_domain_file = os.path.join(config.db_path, '%s/domain_list.yaml' % str(hardware))

        if not os.path.exists(hardware_domain_file):
            logger.error("Could not find %s domain list, please use psample -H %s first!" % (hardware, hardware))
        else:
            with open(hardware_domain_file, 'r') as df:
                hardware_dic[hardware]['domain_dic'] = yaml.load(df, Loader=yaml.FullLoader)

    return hardware_dic