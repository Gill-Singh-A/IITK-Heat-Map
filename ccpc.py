#! /usr/bin/env python3

import paramiko, json
from getpass import getpass
from datetime import date
from socket import gethostbyname
from optparse import OptionParser
from colorama import Fore, Back, Style
from time import strftime, localtime, time

status_color = {
    '+': Fore.GREEN,
    '-': Fore.RED,
    '*': Fore.YELLOW,
    ':': Fore.CYAN,
    ' ': Fore.WHITE
}

def display(status, data, start='', end='\n'):
    print(f"{start}{status_color[status]}[{status}] {Fore.BLUE}[{date.today()} {strftime('%H:%M:%S', localtime())}] {status_color[status]}{Style.BRIGHT}{data}{Fore.RESET}{Style.RESET_ALL}", end=end)

def get_arguments(*args):
    parser = OptionParser()
    for arg in args:
        parser.add_option(arg[0], arg[1], dest=arg[2], help=arg[3])
    return parser.parse_args()[0]

with open("ccpc_ips.txt", 'r') as file:
    ccpc_ips = [ip for ip in file.read().split('\n') if ip != '']
total_ips = len(ccpc_ips)
ccpc_users = {ip: {"ssh_users": [], "users": []} for ip in ccpc_ips}
ccpc_info = {ip: {"ssh_client": None, "authenticated": False, "authentication_time": None, "error": None} for ip in ccpc_ips}
timeout = 1
webhome_ip = gethostbyname("webhome.cc.iitk.ac.in")
default_users = ["root"]

def connectSSH(ip, user, password, port=22, timeout=30):
    try:
        t1 = time()
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=user, password=password, allow_agent=False, timeout=timeout)
        display('+', f"Authenticated => {Back.MAGENTA}{ip}{Back.RESET}")
        t2 = time()
        return ssh, t2-t1
    except Exception as err:
        return err, -1
def webhomeHandler(user, password, timeout):
    while True:
        ssh_client, authentication_time = connectSSH(webhome_ip, user, password, 22, timeout)
        if authentication_time != -1:
            break
        display('-', f"Error Occured while Connecting to {Back.MAGENTA}WEBHOME{Back.RESET} => {Back.YELLOW}{ssh_client}{Back.RESET}")
    while True:
        users = list(set([current_pc_users for current_pc_users in ccpc_users.values()]))
        with open("users.json", 'w') as file:
            json.dump(users, file)
if __name__ == "__main__":
    arguments = get_arguments(('-u', "--user", "user", "Computer Center (CC) User ID"),
                              ('-t', "--timeout", "timeout", f"Timeout for Authenticating to a Linux Lab Computer (Default={timeout}seconds)"))
    if not arguments.user:
        display('-', f"Please Provide a {Back.YELLOW}CC User ID!{Back.RESET}")
        exit(0)
    password = getpass(f"Enter Password for {arguments.user} : ")
    if not arguments.timeout:
        arguments.timeout = timeout
    else:
        arguments.timeout = int(arguments.timeout)
    display(':', f"Linux Lab Computers = {Back.MAGENTA}{len(ccpc_ips)}{Back.RESET}")
    default_users.append(arguments.user)
    try:
        while True:
            for ip in ccpc_ips:
                while ccpc_info[ip]["authenticated"] == False:
                    ssh_client, authentication_time = connectSSH(ip, arguments.user, password, 22, timeout)
                    if authentication_time != -1:
                        ccpc_info[ip]["authenticated"] = True
                        ccpc_info[ip]["ssh_client"] = ssh_client
                        ccpc_info[ip]["authentication_time"] = authentication_time
                    else:
                        ccpc_info[ip]["error"] = ssh_client
                        display('-', f"Error Occurred while Connecting to {Back.MAGENTA}{ip}{Back.RESET} => {Back.YELLOW}{ssh_client}{Back.RESET}")
                    break
                if ccpc_info[ip]["error"] != None:
                    continue
                stdin, stdout, stderr = ccpc_info[ip]["ssh_client"].exec_command("ps -aux | grep sshd")
                ssh_users = list(set([line.split(' ')[0] for line in stdout.readlines() if line.split(' ')[0] not in default_users]))
                stdin, stdout, stderr = ccpc_info[ip]["ssh_client"].exec_command("ps -aux | grep gnome-session")
                users = list(set([line.split(' ')[0] for line in stdout.readlines() if line.split(' ')[0] not in default_users]))
                users.sort()
                ccpc_users[ip]["ssh_users"] = ssh_users
                ccpc_users[ip]["users"] = users
                display(':', f"{Back.MAGENTA}{ip}{Back.RESET} => Users:{','.join(users)}, SSH Users:{','.join(ssh_users)}")
    except KeyboardInterrupt:
        display('*', f"Keyboard Interrupt Detected...", start='\n')
        display(':', "Exiting")
    except Exception as error:
        display('-', f"Error Occured => {Back.YELLOW}{error}{Back.RESET}")