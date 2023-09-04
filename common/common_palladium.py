import os
import re
import sys
import copy

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/config')
import config

sys.path.append(str(os.environ['EMU_MONITOR_INSTALL_PATH']) + '/common')
import common


def get_test_server_info(hardware, host=''):
    test_server_info = []

    if hardware == 'Z1':
        test_server = config.Z1_test_server
        host = config.Z1_test_server_host
    elif hardware == 'Z2':
        test_server = config.Z2_test_server
        host = config.Z2_test_server_host

    if not test_server:
        common.print_warning('*Warning*: test_server path is not specified on config/config.py.')
    else:
        command = test_server

        if host:
            command = 'ssh ' + str(host) + ' "' + str(command) + '"'

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


def filter_palladium_dic(palladium_dic, specified_rack='', specified_cluster='', specified_logic_drawer='', specified_domain='', specified_owner='', specified_pid='', specified_tpod='', specified_design=''):
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
