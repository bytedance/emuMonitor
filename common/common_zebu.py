import re
import copy


def parse_current_zebu_info(current_zebu_info):

    current_zebu_dic = {
            'info': {},
            'unit_list': [],
            'module_list': [],
            'module_info_list': [],
            'sub_module_list': [],
            'status_list': [],
            'user_list': [],
            'host_list': [],
            'pid_list': [],
            'suspend_list': [],
            'row': 0
            }
    for line in current_zebu_info:
        if line:
            if re.match(r"\s*\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s*$", line):
                (module_info, status, uselessitem, user, host, pid, suspend) = line.split()

            elif re.match(r"\s*\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s*$", line):
                (module_info, status, uselessitem, user, host, pid) = line.split()
                suspend = 'None'

            elif re.match(r"\s*\S+\s+\S+\s*$", line):
                (module_info, status) = line.split()
                user = 'None'
                host = 'None'
                pid = 'None'
                suspend = 'None'

            if module_info not in current_zebu_dic['module_info_list']:
                current_zebu_dic['module_info_list'].append(module_info)

            (unit, module, sub_module) = module_info.split('.')
            current_zebu_dic['info'].setdefault(unit, {})
            current_zebu_dic['info'][unit].setdefault(module, {})
            current_zebu_dic['info'][unit][module].setdefault(sub_module, {})
            current_zebu_dic['info'][unit][module][sub_module] = {
                    'status': status,
                    'user': user,
                    'host': host,
                    'pid': pid,
                    'suspend': suspend
                    }
            if unit not in current_zebu_dic['unit_list']:
                current_zebu_dic['unit_list'].append(unit)
            if module not in current_zebu_dic['module_list']:
                current_zebu_dic['module_list'].append(module)
            if sub_module not in current_zebu_dic['sub_module_list']:
                current_zebu_dic['sub_module_list'].append(sub_module)
            if status not in current_zebu_dic['status_list']:
                current_zebu_dic['status_list'].append(status)
            if user not in current_zebu_dic['user_list']:
                current_zebu_dic['user_list'].append(user)
            if host not in current_zebu_dic['host_list']:
                current_zebu_dic['host_list'].append(host)
            if pid not in current_zebu_dic['pid_list']:
                current_zebu_dic['pid_list'].append(pid)
            if suspend not in current_zebu_dic['suspend_list']:
                current_zebu_dic['suspend_list'].append(suspend)

            current_zebu_dic['row'] += 1

    return current_zebu_dic


def parse_history_zebu_info(sys_report_lines, specified_unit='', specified_module='', specified_sub_module='', specified_user='', specified_host='', specified_pid=''):
    history_zebu_dic = {
                'info': {},
                'user_list': [],
                'host_list': [],
                'pid_list': [],
                'rows': 0
                }
    for line in sys_report_lines:
        if line:
            start_time, end_time, modules, user, pid, host = line.split(',')
            modules_list = modules.strip('()').split(' ')
            for modules in modules_list:
                if modules:
                    unit, module, sub_module = modules.split('.')
                    if specified_unit == 'ALL' or specified_unit == unit:
                        if specified_module == 'ALL' or specified_module == module:
                            if specified_sub_module == 'ALL' or specified_sub_module == sub_module:
                                if specified_user == 'ALL' or specified_user == user:
                                    if specified_host == 'ALL' or specified_host == host:
                                        if specified_pid == 'ALL' or specified_pid == pid:
                                            history_zebu_dic['info'].setdefault(pid, {})
                                            history_zebu_dic['info'][pid].setdefault('host', host)
                                            history_zebu_dic['info'][pid].setdefault('user', user)
                                            history_zebu_dic['info'][pid].setdefault('start_time', start_time)
                                            history_zebu_dic['info'][pid].setdefault('end_time', end_time)
                                            history_zebu_dic['info'][pid].setdefault('modules', [])
                                            history_zebu_dic['info'][pid]['modules'].append(modules)
                                            if user not in history_zebu_dic['user_list']:
                                                history_zebu_dic['user_list'].append(user)
                                            if pid not in history_zebu_dic['pid_list']:
                                                history_zebu_dic['pid_list'].append(pid)
                                            if host not in history_zebu_dic['host_list']:
                                                history_zebu_dic['host_list'].append(host)
                                            history_zebu_dic['rows'] += 1
    return history_zebu_dic


def filter_zebu_dic(zebu_dic, specified_unit='', specified_module='', specified_sub_module='', specified_status='', specified_user='', specified_host='', specified_pid='', specified_suspend=''):
    filtered_zebu_dic = copy.deepcopy(zebu_dic)
    if zebu_dic:
        for unit in zebu_dic['info'].keys():
            if specified_unit and specified_unit != 'ALL' and specified_unit != unit:
                del filtered_zebu_dic['info'][unit]
                filtered_zebu_dic['unit_list'].remove(unit)
            else:
                for module in zebu_dic['info'][unit].keys():
                    if specified_module and specified_module != 'ALL' and specified_module != module:
                        del filtered_zebu_dic['info'][unit][module]
                        filtered_zebu_dic['module_list'].remove(module)
                    else:
                        for sub_module in zebu_dic['info'][unit][module].keys():
                            if specified_sub_module and specified_sub_module != 'ALL' and specified_sub_module != sub_module:
                                del filtered_zebu_dic['info'][unit][module][sub_module]
                            else:
                                status = zebu_dic['info'][unit][module][sub_module]['status']
                                if specified_status and specified_status != 'ALL' and specified_status != status:
                                    del filtered_zebu_dic['info'][unit][module][sub_module]
                                    continue
                                user = zebu_dic['info'][unit][module][sub_module]['user']
                                if specified_user and specified_user != 'ALL' and specified_user != user:
                                    del filtered_zebu_dic['info'][unit][module][sub_module]
                                    continue
                                host = zebu_dic['info'][unit][module][sub_module]['host']
                                if specified_host and specified_host != 'ALL' and specified_host != host:

                                    del filtered_zebu_dic['info'][unit][module][sub_module]
                                    continue
                                pid = zebu_dic['info'][unit][module][sub_module]['pid']
                                if specified_pid and specified_pid != 'ALL' and specified_pid != pid:
                                    del filtered_zebu_dic['info'][unit][module][sub_module]
                                    continue
                                suspend = zebu_dic['info'][unit][module][sub_module]['suspend']
                                if specified_suspend and specified_suspend != 'ALL' and specified_suspend != suspend:
                                    del filtered_zebu_dic['info'][unit][module][sub_module]

    filtered_zebu_dic['unit_list'] = []
    filtered_zebu_dic['module_list'] = []
    filtered_zebu_dic['sub_module_list'] = []
    filtered_zebu_dic['status_list'] = []
    filtered_zebu_dic['user_list'] = []
    filtered_zebu_dic['host_list'] = []
    filtered_zebu_dic['pid_list'] = []
    filtered_zebu_dic['suspend_list'] = []
    filtered_zebu_dic['module_name'] = []
    filtered_zebu_dic['row'] = 0

    for unit in filtered_zebu_dic['info']:
        for module in filtered_zebu_dic['info'][unit]:
            for sub_module in filtered_zebu_dic['info'][unit][module]:
                module_name = unit + '.' + module + '.' + sub_module
                if unit not in filtered_zebu_dic['unit_list']:
                    filtered_zebu_dic['unit_list'].append(unit)
                if module not in filtered_zebu_dic['module_list']:
                    filtered_zebu_dic['module_list'].append(module)
                if sub_module not in filtered_zebu_dic['sub_module_list']:
                    filtered_zebu_dic['sub_module_list'].append(sub_module)
                if status not in filtered_zebu_dic['status_list']:
                    filtered_zebu_dic['status_list'].append(status)
                if user not in filtered_zebu_dic['user_list']:
                    filtered_zebu_dic['user_list'].append(user)
                if host not in filtered_zebu_dic['host_list']:
                    filtered_zebu_dic['host_list'].append(host)
                if pid not in filtered_zebu_dic['pid_list']:
                    filtered_zebu_dic['pid_list'].append(pid)
                if suspend not in filtered_zebu_dic['suspend_list']:
                    filtered_zebu_dic['suspend_list'].append(suspend)
                if module_name not in filtered_zebu_dic['module_name']:
                    filtered_zebu_dic['module_name'].append(module_name)

                filtered_zebu_dic['row'] += 1

    return filtered_zebu_dic
