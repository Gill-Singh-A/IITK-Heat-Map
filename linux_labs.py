#! /usr/bin/env python3

import paramiko, ftplib
from getpass import getpass
from datetime import date
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

ips = None
location = None
total_ips = None
location_users = None
location_info = None
timeout = 1
default_users = ["root"]
with open("users.txt", 'r') as file:
    users = file.read().split('\n')

with open("template/template_start.html", 'r') as file:
    template_start = file.read()
with open("template/template_end.html", 'r') as file:
    template_end = file.read()

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
def createPage():
    page = template_start
    for ip, users in location_users.items():
        if len(users["users"]) > 0:
            status = "occupied"
        else:
            status = "free"
        if location_info[ip]["authenticated"] == False:
            status = "power-off"
        page += f"<tr class={status}><td>{ips[ip]}</td><td>{(','.join(users['users'])) if len(users['users']) > 0 else '-'}</td><td>{(','.join(users['ssh_users'])) if len(users['ssh_users']) > 0 else '-'}</td><td>{status.upper()}</td></tr>\n"
    page += template_end
    with open(f"pages/{location}.html", 'w') as file:
        file.write(page)

if __name__ == "__main__":
    arguments = get_arguments(('-u', "--user", "user", "Computer Center (CC) User ID"),
                              ('-w', "--webhome-user", "webhome_user", "Webhome User (Default=CC User ID)"),
                              ('-t', "--timeout", "timeout", f"Timeout for Authenticating to a Linux Lab Computer (Default={timeout}seconds)"),
                              ('-l', "--location", "location", f"Location in Campus (Linux Lab:ccpc, kd_lab)"))
    if not arguments.user:
        display('-', f"Please Provide a {Back.YELLOW}CC User ID!{Back.RESET}")
        exit(0)
    if not arguments.timeout:
        arguments.timeout = timeout
    else:
        arguments.timeout = int(arguments.timeout)
    if not arguments.location:
        display('-', f"Please Provide a Location")
        exit(0)
    else:
        location = arguments.location
    password = getpass(f"Enter Password for {arguments.user} : ")
    if arguments.webhome_user:
        webhome_password = getpass(f"Enter Password for {arguments.webhome_user}@webhome : ")
    else:
        arguments.webhome_user = arguments.user
        webhome_password = password
    default_users.append(arguments.user)
    with open(f"csv/{location}.csv", 'r') as file:
        ips = {line.split(',')[0]: line.split(',')[1] for line in file.read().split('\n') if line != ''}
    total_ips = len(ips)
    location_users = {ip: {"ssh_users": [], "users": []} for ip in ips}
    location_info = {ip: {"ssh_client": None, "authenticated": False, "authentication_time": None, "error": None} for ip in ips}
    display(':', f"IPs = {Back.MAGENTA}{total_ips}{Back.RESET}")
    try:
        ftp_server = ftplib.FTP("webhome.cc.iitk.ac.in", arguments.webhome_user, webhome_password)
    except Exception as error:
        display('-', f"Error Occured while Connecting to {Back.MAGENTA}WEBHOME{Back.RESET} => {Back.YELLOW}{error}{Back.RESET}")
        exit(0)
    try:
        while True:
            for ip in location_users.keys():
                while location_info[ip]["authenticated"] == False:
                    ssh_client, authentication_time = connectSSH(ip, arguments.user, password, 22, timeout)
                    if authentication_time != -1:
                        location_info[ip]["authenticated"] = True
                        location_info[ip]["ssh_client"] = ssh_client
                        location_info[ip]["authentication_time"] = authentication_time
                    else:
                        location_info[ip]["error"] = ssh_client
                        display('-', f"Error Occurred while Connecting to {Back.MAGENTA}{ip}{Back.RESET} => {Back.YELLOW}{ssh_client}{Back.RESET}")
                    break
                if location_info[ip]["error"] != None:
                    continue
                stdin, stdout, stderr = location_info[ip]["ssh_client"].exec_command("ps -aux | grep sshd")
                ssh_users = list(set([line.split(' ')[0] for line in stdout.readlines() if line.split(' ')[0] not in default_users and line.split(' ')[0] in users]))
                stdin, stdout, stderr = location_info[ip]["ssh_client"].exec_command("ps -aux | grep gnome-session")
                users = list(set([line.split(' ')[0] for line in stdout.readlines() if line.split(' ')[0] not in default_users and line.split(' ')[0] in users]))
                users.sort()
                location_users[ip]["ssh_users"] = ssh_users
                location_users[ip]["users"] = users
                display(':', f"{Back.MAGENTA}{ip}{Back.RESET} => Users:{','.join(users)}, SSH Users:{','.join(ssh_users)}")
            createPage()
            ftp_server = ftplib.FTP("webhome.cc.iitk.ac.in", arguments.webhome_user, webhome_password)
            with open(f"pages/{location}.html", 'rb') as file:
                ftp_server.storbinary(f"STOR /www/{arguments.user}/www/{location}.html", file)
            ftp_server.quit()
    except KeyboardInterrupt:
        display('*', f"Keyboard Interrupt Detected...", start='\n')
        display(':', "Exiting")
    except Exception as error:
        display('-', f"Error Occured => {Back.YELLOW}{error}{Back.RESET}")