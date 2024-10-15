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
    tool_list = ['bin/palladium_monitor', 'bin/psample', 'bin/zebu_monitor', 'bin/protium_sample', 'bin/protium_monitor', 'tools/patch']

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
            with open(tool, 'a+') as SP:
                SP.write('\npython3 $EMU_MONITOR_INSTALL_PATH/' + str(tool_name) + '.py $@')

            os.chmod(tool, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
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
            tool_path = str(CWD) + '/tools'

            with open(config_file, 'w') as CF:
                CF.write('''# Specify the database directory.
db_path = "''' + str(db_path) + '''"

######## For Palladium ########
# Enable "others" project on COST tab, so cost can always be shared.
palladium_enable_cost_others_project = True

# Use default cost rate for no-use emu
palladium_enable_use_default_cost_rate = True


######## For Zebu ########
# Specify zRscManager path for Zebu.
zRscManager = ""

# Specify zebu system directory.
ZEBU_SYSTEM_DIR = ""

# Specify zebu system directory.
zebu_system_dir_record = ""

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


######## For Protium ########
# Check protium information tcl file
ptmRun_check_info_file = "''' + str(tool_path) + '''/check.info.tcl"

# Enable "others" project on COST tab, so cost can always be shared.
protium_enable_cost_others_project = True

# Use default cost rate for no-use emu
protium_enable_use_default_cost_rate = True
''')

            os.chmod(config_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
            os.chmod(db_path, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(config_file) + '" for write: ' + str(error))
            sys.exit(1)


def gen_sub_config_file():
    print('')

    zebu_project_list_file = str(CWD) + '/config/zebu/project_list'
    zebu_execute_host_file = str(CWD) + '/config/zebu/project_execute_host'
    zebu_user_file = str(CWD) + '/config/zebu/project_user'

    Z1_project_list_file = str(CWD) + '/config/palladium/Z1/project_list'
    Z1_execute_host_file = str(CWD) + '/config/palladium/Z1/project_execute_host'
    Z1_user_file = str(CWD) + '/config/palladium/Z1/project_user'
    Z1_config_file = str(CWD) + '/config/palladium/Z1/config.py'

    Z2_project_list_file = str(CWD) + '/config/palladium/Z2/project_list'
    Z2_execute_host_file = str(CWD) + '/config/palladium/Z2/project_execute_host'
    Z2_user_file = str(CWD) + '/config/palladium/Z2/project_user'
    Z2_config_file = str(CWD) + '/config/palladium/Z2/config.py'

    X1_project_list_file = str(CWD) + '/config/protium/X1/project_list'
    X1_execute_host_file = str(CWD) + '/config/protium/X1/project_execute_host'
    X1_user_file = str(CWD) + '/config/protium/X1/project_user'
    X1_config_file = str(CWD) + '/config/protium/X1/config.py'

    X2_project_list_file = str(CWD) + '/config/protium/X2/project_list'
    X2_execute_host_file = str(CWD) + '/config/protium/X2/project_execute_host'
    X2_user_file = str(CWD) + '/config/protium/X2/project_user'
    X2_config_file = str(CWD) + '/config/protium/X2/config.py'

    gen_project_list_file(zebu_project_list_file)
    gen_project_list_file(Z1_project_list_file)
    gen_project_list_file(Z2_project_list_file)
    gen_project_list_file(X1_project_list_file)
    gen_project_list_file(X2_project_list_file)

    gen_project_execute_host_file(zebu_execute_host_file)
    gen_project_execute_host_file(Z1_execute_host_file)
    gen_project_execute_host_file(Z2_execute_host_file)
    gen_project_execute_host_file(X1_execute_host_file)
    gen_project_execute_host_file(X2_execute_host_file)

    gen_project_user_file(zebu_user_file)
    gen_project_user_file(Z1_user_file)
    gen_project_user_file(Z2_user_file)
    gen_project_user_file(X1_user_file)
    gen_project_user_file(X2_user_file)

    gen_palladium_config_file(Z1_config_file)
    gen_palladium_config_file(Z2_config_file)

    gen_protium_config_file(X1_config_file)
    gen_protium_config_file(X2_config_file)


def gen_check_info_file():
    # Generate protium check information tcl file.
    check_file_file = str(CWD) + '/tools/check.info.tcl'

    print('>>> Generate protium check information file "' + str(check_file_file) + '".\n')

    if os.path.exists(check_file_file):
        print('    *Warning*: file "' + str(check_file_file) + '" already exists, will not update it.')
    else:
        try:
            with open(check_file_file, 'w') as PLF:
                PLF.write('''
sys
exit
    ''')

            os.chmod(check_file_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening file "' + str(check_file_file) + '" for write: ' + str(error))
            sys.exit(1)


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

            os.chmod(project_execute_host_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
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

            os.chmod(project_list_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
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

            os.chmod(project_user_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(project_user_file) + '" for write: ' + str(error))
            sys.exit(1)


def gen_palladium_config_file(palladium_config_file):
    # Generate project_user_file.
    print('>>> Generate palladium config file "' + str(palladium_config_file) + '".\n')

    if os.path.exists(palladium_config_file):
        print('    *Warning*: config file "' + str(palladium_config_file) + '" already exists, will not update it.')
    else:
        try:
            with open(palladium_config_file, 'w') as PUF:
                PUF.write('''
# Specify test_server path for Palladium hardware.
test_server = ""

# Specify test_server execute hosts for Palladium hardware, make sure you can ssh the host without password.
test_server_host = ""

# Specify which are the primary factors when getting project information, it could be one or serveral items between "user/execute_host/submit_host".
project_primary_factors = "user  execute_host"
    ''')

            os.chmod(palladium_config_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(palladium_config_file) + '" for write: ' + str(error))
            sys.exit(1)


def gen_protium_config_file(protium_config_file):
    # Generate project_user_file.
    print('>>> Generate protium config file "' + str(protium_config_file) + '".\n')

    if os.path.exists(protium_config_file):
        print('    *Warning*: config file "' + str(protium_config_file) + '" already exists, will not update it.')
    else:
        try:
            with open(protium_config_file, 'w') as PUF:
                PUF.write('''
# protium server
host = ""

# Specify protium system ip list file
PTM_SYS_IP_LIST = ""

# Specify ptmRun path for protium
ptmRun = ""

# Specify ptmRun bsub command, example "bsub -q normal -Is". if "", run "ptmRun" locally rather than using LSF scheduler
ptmRun_bsub_command = ""

# Specify which are the primary factors when getting project information, it could be one or serveral items between "user/execute_host/submit_host".
project_primary_factors = "user  execute_host"
        ''')

            os.chmod(protium_config_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
        except Exception as error:
            print('*Error*: Failed on opening config file "' + str(protium_config_file) + '" for write: ' + str(error))
            sys.exit(1)


################
# Main Process #
################
def main():
    check_python_version()
    gen_shell_tools()
    gen_config_file()
    gen_sub_config_file()
    gen_check_info_file()

    print('')
    print('Done, Please enjoy it.')


if __name__ == '__main__':
    main()
