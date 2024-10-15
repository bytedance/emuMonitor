import subprocess
import xlwt
import logging
import os
import re
import sys


def print_error(message):
    """
    Print error message with red color.
    """
    print('\033[1;31m' + str(message) + '\033[0m')


def print_warning(message):
    """
    Print warning message with yellow color.
    """
    print('\033[1;33m' + str(message) + '\033[0m')


def run_command(command, mystdin=subprocess.PIPE, mystdout=subprocess.PIPE, mystderr=subprocess.PIPE):
    """
    Run system command with subprocess.Popen, get returncode/stdout/stderr.
    """
    SP = subprocess.Popen(command, shell=True, stdin=mystdin, stdout=mystdout, stderr=mystderr)
    (stdout, stderr) = SP.communicate()

    return (SP.returncode, stdout, stderr)


def write_excel(excel_file, contents_list, specified_sheet_name='default'):
    """
    Open Excel for write.
    Input contents_list is a 2-dimentional list.

    contents_list = [
                     row_1_list,
                     row_2_list,
                     ...
                    ]
    """
    workbook = xlwt.Workbook(encoding='utf-8')

    # create worksheet
    worksheet = workbook.add_sheet(specified_sheet_name)

    # Set title style
    title_style = xlwt.XFStyle()
    font = xlwt.Font()
    font.bold = True
    title_style.font = font

    # write excel
    for (row, content_list) in enumerate(contents_list):
        for (column, content_string) in enumerate(content_list):
            if row == 0:
                worksheet.write(row, column, content_string, title_style)
            else:
                worksheet.write(row, column, content_string)

            # auto-width
            column_width = len(str(content_string)) * 256

            if column_width > worksheet.col(column).width:
                worksheet.col(column).width = column_width

    # save excel
    workbook.save(excel_file)


class CustomPrintFormatter(logging.Formatter):
    # logging color setting
    grey = "\x1b[38;20m"
    bold_grey = "\x1b[38;1m"
    green = "\x1b[32;20m"
    bold_green = "\x1b[32;1m"
    yellow = "\x1b[33;20m"
    bold_yellow = "\x1b[33;1m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    purple = "\x1b[35;20m"
    bold_purple = "\x1b[35;1m"

    reset = "\x1b[0m"
    error_format = '[%(asctime)s] *Error*: %(message)s'
    warning_format = '[%(asctime)s] *Warning*: %(message)s'
    info_format = '[%(asctime)s] *Info*: %(message)s'
    format = '[%(asctime)s]%(message)s'

    FORMATS = {
        logging.DEBUG: purple + format + reset,
        logging.INFO: green + info_format + reset,
        logging.WARNING: yellow + warning_format + reset,
        logging.ERROR: red + error_format + reset,
        logging.CRITICAL: grey + format + reset,
    }

    def __init__(self):
        super().__init__(datefmt='%Y-%m-%d %H:%M:%S')

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(fmt=log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


class CustomFileFormatter(logging.Formatter):
    error_format = '[%(asctime)s] *Error*: %(message)s'
    warning_format = '[%(asctime)s] *Warning*: %(message)s'
    info_format = '[%(asctime)s] *Info*: %(message)s'
    format = '[%(asctime)s]%(message)s'

    FORMATS = {
        logging.DEBUG: format,
        logging.INFO: info_format,
        logging.WARNING: warning_format,
        logging.ERROR: error_format,
        logging.CRITICAL: format,
    }

    def __init__(self):
        super().__init__(datefmt='%Y-%m-%d %H:%M:%S')

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(fmt=log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


def get_logger(save_log=False, log_path='log', name='root', level=logging.DEBUG):
    # create logger with 'spam_application'
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # create console handler with a higher log level
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(CustomPrintFormatter())
        logger.addHandler(ch)

        if save_log:
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(level=logging.INFO)
            file_handler.setFormatter(CustomFileFormatter())
            logger.addHandler(file_handler)

    return logger


def parse_project_list_file(project_list_file):
    """
    Parse project_list_file and return List "project_list".
    """
    logger = get_logger(level=logging.DEBUG)

    project_list = []
    default_project_cost_dic = {}

    if project_list_file or os.path.exists(project_list_file):
        with open(project_list_file, 'r') as PLF:
            for line in PLF.readlines():
                line = line.strip()

                if re.match(r'^\s*#.*$', line) or re.match(r'^\s*$', line):
                    continue

                elif my_match := re.match(r'^\s*(\S+)\s*(\S+)?\s*$', line):
                    project = my_match.group(1)
                    default_rate = my_match.group(2)

                    if project not in project_list:
                        project_list.append(project)

                    if default_rate:
                        if re.match(r'\s*\d+\.*\d*\s*', default_rate):
                            rate = round(100 * float(default_rate), 2)

                        else:
                            logger.warning('Could not recognize project default cost rate in line %s, will set 0' % line)
                            rate = 0

                        if project not in default_project_cost_dic:
                            default_project_cost_dic[project] = rate
                        else:
                            if default_project_cost_dic[project] != default_rate:
                                logger.warning('Project: %s cost rate is defined repeatly and has different value, will use the first definition!' % project)

        total_rate = 0

        if not project_list:
            logger.warning("Could not find any valid project infomation!")
        else:
            for project in default_project_cost_dic:
                total_rate += default_project_cost_dic[project]

            if total_rate != 100 or (set(default_project_cost_dic.keys()) != set(project_list)):
                if len(default_project_cost_dic.keys()) == 0:
                    logger.warning('Do not set project default cost rate, all project will amortized expenses!')
                elif set(default_project_cost_dic.keys()) != set(project_list):
                    logger.warning('Not all project has default cost rate, please check! ')

                if total_rate != 100:
                    if len(default_project_cost_dic.keys()) != 0:
                        logger.warning('Total default project rate is not 1, please check!')

                    default_project_cost_dic = {project: round(1 / (len(project_list)) * 100, 2) for project in project_list}
                    residual = 100

                    for rate in default_project_cost_dic.values():
                        residual -= rate

                    if residual:
                        default_project_cost_dic[list(default_project_cost_dic.keys())[-1]] += residual
                        default_project_cost_dic[list(default_project_cost_dic.keys())[-1]] = round(default_project_cost_dic[list(default_project_cost_dic.keys())[-1]], 2)

    return project_list, default_project_cost_dic


def parse_project_proportion_file(project_proportion_file):
    """
    Parse project_*_file and return dictory "project_proportion_dic".
    """
    logger = get_logger(level=logging.DEBUG)

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
                        logger.warning('"' + str(item) + '": repeated item on "' + str(project_proportion_file) + '", ignore.')
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
                        logger.warning('invalid line on "' + str(project_proportion_file) + '", ignore.\n' + '        ' + str(line))
                        continue
                    else:
                        sum_proportion = sum(list(tmp_dic.values()))

                        if sum_proportion == 1.0:
                            project_proportion_dic[item] = tmp_dic
                        else:
                            logger.warning('*Warning*: invalid line on "' + str(project_proportion_file) + '", ignore.\n' + str(line))
                            continue
                else:
                    logger.warning('*Warning*: invalid line on "' + str(project_proportion_file) + '", ignore.\n' + str(line))
                    continue

    return project_proportion_dic


def get_project_info(project_primary_factors, original_project_proportion_dic, execute_host='', user=''):
    """
    Get project information based on submit_host/execute_host/user.
    """
    logger = get_logger(level=logging.DEBUG)
    project_dic = {}
    factor_dic = {'execute_host': execute_host, 'user': user}

    if project_primary_factors:
        project_primary_factor_list = project_primary_factors.split()

        for project_primary_factor in project_primary_factor_list:
            if project_primary_factor not in factor_dic.keys():
                logger.error('"' + str(project_primary_factor) + '": invalid project_primary_factors setting on config file.')
                sys.exit(1)
            else:
                factor_value = factor_dic[project_primary_factor]
                project_proportion_dic = {}

                if factor_value in original_project_proportion_dic[project_primary_factor].keys():
                    project_proportion_dic = original_project_proportion_dic[project_primary_factor][factor_value]

                if project_proportion_dic:
                    project_dic = project_proportion_dic
                    break
                else:
                    continue

    return project_dic
