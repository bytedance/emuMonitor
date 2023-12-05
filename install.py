import os
import sys
import stat

CWD = os.getcwd()
PYTHON_PATH = os.path.dirname(os.path.abspath(sys.executable))


def check_python_version():
    """
    Check python version.
    python3 is required, anaconda3 is better.
    """
    print('>>> Check python version.')

    current_python = sys.version_info[:2]
    required_python = (3, 8)

    if current_python < required_python:
        sys.stderr.write("""
==========================
Unsupported Python version
==========================
This version of palladiumMonitor requires Python {}.{} (or greater version),
but you're trying to install it on Python {}.{}.
""".format(*(required_python + current_python)))
        sys.exit(1)
    else:
        print('    Required python version : ' + str(required_python))
        print('    Current  python version : ' + str(current_python))


def gen_shell_tools():
    """
    Generate shell scripts under <EMU_MONITOR_INSTALL_PATH>/tools.
    """
    tool_list = ['bin/pmonitor', 'bin/psample', 'bin/zmonitor', 'tools/patch', 'test/pmonitor_test', 'test/psample_test', 'test/zmonitor_test', 'test/gen_test_db']

    for tool_name in tool_list:
        tool = str(CWD) + '/' + str(tool_name)
        ld_library_path_setting = 'export LD_LIBRARY_PATH=$EMU_MONITOR_INSTALL_PATH/lib:'

        if 'LD_LIBRARY_PATH' in os.environ:
            ld_library_path_setting = str(ld_library_path_setting) + str(os.environ['LD_LIBRARY_PATH'])

        print('')
        print('>>> Generate script "' + str(tool) + '".')

        try:
            with open(tool, 'w') as SP:
                SP.write("""#!/bin/bash

# Set python3 path.
export PATH=""" + str(PYTHON_PATH) + """:$PATH

# Set install path.
export EMU_MONITOR_INSTALL_PATH=""" + str(CWD) + """

# Set LD_LIBRARY_PATH.
""" + str(ld_library_path_setting) + """

# Execute """ + str(tool_name) + """.py.'""")
            if tool_name == 'test/gen_test_db':
                with open(tool, 'a+') as SP:
                    SP.write('\npython3 $EMU_MONITOR_INSTALL_PATH/' + str(tool_name) + '.py -t palladium')
                    SP.write('\npython3 $EMU_MONITOR_INSTALL_PATH/' + str(tool_name) + '.py -t zebu$@')
            else:
                with open(tool, 'a+') as SP:
                    SP.write('\npython3 $EMU_MONITOR_INSTALL_PATH/' + str(tool_name) + '.py $@')

            os.chmod(tool, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on generating script "' + str(tool) + '": ' + str(error))
            sys.exit(1)


def gen_config_file():
    """
    Generate config file <EMU_MONITOR_INSTALL_PATH>/config/config.py.
    """
    config_file = str(CWD) + '/config/config.py'

    print('')
    print('>>> Generate config file "' + str(config_file) + '".')

    if os.path.exists(config_file):
        print('*Warning*: config file "' + str(config_file) + '" already exists, will not update it.')
    else:
        try:
            db_path = str(CWD) + '/db'

            with open(config_file, 'w') as CF:
                CF.write('''######## For Palladium ########
# Specify the database directory.
db_path = "''' + str(db_path) + '''"

# Specify test_server path for Palladium Z1.
Z1_test_server = ""

# Specify test_server path for Palladium Z2.
Z2_test_server = ""

# Specify test_server execute hosts for Palladium Z1, make sure you can ssh the host without password.
Z1_test_server_host = ""

# Specify test_server execute hosts for Palladium Z2, make sure you can ssh the host without password.
Z2_test_server_host = ""

# Specify which are the primary factors when getting project information, it could be one or serveral items between "user/execute_host/submit_host".
Z1_project_primary_factors = "user  execute_host"

Z2_project_primary_factors = "user  execute_host"

# Enable "others" project on COST tab, so cost can always be shared.
palladium_enable_cost_others_project = True

# Use default cost rate for no-use emu
palladium_enable_use_default_cost_rate = True




######## For Zebu ########
# Specify zRscManager path for Zebu.
zRscManager = ""

# Specify zebu system directory.
ZEBU_SYSTEM_DIR = ""

# Specify check status command.
check_status_command = zRscManager + \" -nc -sysstat \" + ZEBU_SYSTEM_DIR + \" -pid ; rm ZEBU_GLOBAL_SYSTEM_DIR_global_mngt.db\"

# Specify check report command.
check_report_command = zRscManager + \" -nc -sysreport \" + ZEBU_SYSTEM_DIR + \" -from FROMDATE -to TODATE -noheader -fields 'opendate, closedate, modulesList, user, pid, pc' -nofilter ; rm ZEBU_GLOBAL_SYSTEM_DIR_global_mngt.db\"

# Specify which are the primary factors when getting project information, it could be one or serveral items between "user/execute_host/submit_host".
zebu_project_primary_factors = "user  execute_host"

# Enable "others" project on COST tab, so cost can always be shared.
zebu_enable_cost_others_project = True

# Use default cost rate for no-use emu
zebu_enable_use_default_cost_rate = True

''')

            os.chmod(config_file, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
            os.chmod(db_path, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(config_file) + '" for write: ' + str(error))
            sys.exit(1)


def gen_test_config_file():
    """
    Generate test config file <EMU_MONITOR_INSTALL_PATH>/test/test_config/test_config.py.
    """
    test_config_file = str(CWD) + '/test/test_config/test_config.py'

    print('')
    print('>>> Generate config file "' + str(test_config_file) + '".')

    if os.path.exists(test_config_file):
        print('*Warning*: config file "' + str(test_config_file) + '" already exists, will not update it.')
    else:
        try:
            test_path = str(CWD) + '/test'

            with open(test_config_file, 'w') as CF:
                CF.write('''# Specify test hardware .
test_hardware = ""

# Specify the test database directory.
db_path = "''' + str(test_path) + '''/test_data/test_db"

# Specify project(s) file.
project_list_file = "''' + str(test_path) + '''/test_config/project_list"

# Specify project & execute_host relationship file.
project_execute_host_file = "''' + str(test_path) + '''/test_config/project_execute_host"

# Specify project & user relationship file.
project_user_file = "''' + str(test_path) + '''/test_config/project_user"

# Specify which are the primary factors when getting project information, it could be one or serveral items between "user/execute_host/submit_host".
project_primary_factors = "user  execute_host"

# Specify test_result which used for test
test_result = "''' + str(test_path) + '''/test_data/test_result"

# Specify test_db generate template db
test_palladium_db = "''' + str(test_path) + '''/test_data/test_palladium_db_file"
''')

            os.chmod(test_config_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
            os.chmod(test_path, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(test_config_file) + '" for write: ' + str(error))
            sys.exit(1)


def gen_cost_config_file():
    print('')

    zebu_project_list_file = str(CWD) + '/config/zebu/project_list'
    zebu_execute_host_file = str(CWD) + '/config/zebu/project_execute_host'
    zebu_user_file = str(CWD) + '/config/zebu/project_user'

    Z1_project_list_file = str(CWD) + '/config/palladium/Z1/project_list'
    Z1_execute_host_file = str(CWD) + '/config/palladium/Z1/project_execute_host'
    Z1_user_file = str(CWD) + '/config/palladium/Z1/project_user'

    Z2_project_list_file = str(CWD) + '/config/palladium/Z2/project_list'
    Z2_execute_host_file = str(CWD) + '/config/palladium/Z2/project_execute_host'
    Z2_user_file = str(CWD) + '/config/palladium/Z2/project_user'

    gen_project_list_file(zebu_project_list_file)
    gen_project_list_file(Z1_project_list_file)
    gen_project_list_file(Z2_project_list_file)

    gen_project_execute_host_file(zebu_execute_host_file)
    gen_project_execute_host_file(Z1_execute_host_file)
    gen_project_execute_host_file(Z2_execute_host_file)

    gen_project_user_file(zebu_user_file)
    gen_project_user_file(Z1_user_file)
    gen_project_user_file(Z2_user_file)


def gen_project_execute_host_file(project_execute_host_file):
    # Generate project_execute_host_file.
    print('>>> Generate project-execute_host relationship file "' + str(project_execute_host_file) + '".\n')

    if os.path.exists(project_execute_host_file):
        print('    *Warning*: config file "' + str(project_execute_host_file) + '" already exists, will not update it.')
    else:
        try:
            with open(project_execute_host_file, 'w') as PEHF:
                PEHF.write('''# Example:
# host1 : project1(0.3) project2(0.7)
# host2 : project3

''')

            os.chmod(project_execute_host_file, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(project_execute_host_file) + '" for write: ' + str(error))
            sys.exit(1)


def gen_project_list_file(project_list_file):
    # Generate project_list_file.
    print('>>> Generate project list file "' + str(project_list_file) + '".\n')

    if os.path.exists(project_list_file):
        print('    *Warning*: config file "' + str(project_list_file) + '" already exists, will not update it.')
    else:
        try:
            with open(project_list_file, 'w') as PLF:
                PLF.write('''# Example:
# project1
# project2

''')

            os.chmod(project_list_file, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(project_list_file) + '" for write: ' + str(error))
            sys.exit(1)


def gen_project_user_file(project_user_file):
    # Generate project_user_file.
    print('>>> Generate project-user relationship file "' + str(project_user_file) + '".\n')

    if os.path.exists(project_user_file):
        print('    *Warning*: config file "' + str(project_user_file) + '" already exists, will not update it.')
    else:
        try:
            with open(project_user_file, 'w') as PUF:
                PUF.write('''# Example:
# user1 : project1(0.3) project2(0.7)
# user2 : project3

''')

            os.chmod(project_user_file, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(project_user_file) + '" for write: ' + str(error))
            sys.exit(1)

################
# Main Process #
################
def main():
    check_python_version()
    gen_shell_tools()
    gen_config_file()
    gen_test_config_file()
    gen_cost_config_file()

    print('')
    print('Done, Please enjoy it.')


if __name__ == '__main__':
    main()
