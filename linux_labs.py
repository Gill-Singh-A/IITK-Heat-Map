#! /usr/bin/env python3

import paramiko, ftplib
from getpass import getpass
from datetime import date, datetime
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

def isLeap(year):
    if year % 4 == 0:
        if year % 100 == 0:
            if year % 400 == 0:
                return True
            else:
                return False
        else:
            return True
    else:
        return False
months = {"Jan": 0,
          "Feb": 31,
          "Mar": 60 if isLeap(datetime.now().year) else 59,
          "Apr": 91 if isLeap(datetime.now().year) else 90,
          "May": 121 if isLeap(datetime.now().year) else  120,
          "Jun": 152 if isLeap(datetime.now().year) else  151,
          "Jul": 182 if isLeap(datetime.now().year) else  181,
          "Aug": 213 if isLeap(datetime.now().year) else  212,
          "Sep": 244 if isLeap(datetime.now().year) else  243,
          "Oct": 274 if isLeap(datetime.now().year) else  273,
          "Nov": 305 if isLeap(datetime.now().year) else  304,
          "Dec": 335 if isLeap(datetime.now().year) else  334}

ips = None
location = None
total_ips = None
location_users = None
location_info = None
timeout = 1
default_users = ["root"]
with open("users.txt", 'r') as file:
    all_cc_users = file.read().split('\n')

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
    page += f"<h1>Last Updated : {datetime.now().hour}:{datetime.now().minute} {datetime.now().day} {datetime.now().strftime('%B')} {datetime.now().year}</h1>"
    page += """<table>
          <thead>
            <tr>
              <th>Computer</th>
              <th>User</th>
              <th>SSH Users</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>"""
    for ip, users in location_users.items():
        if users["users"] != None:
            status = "occupied"
        else:
            status = "free"
        if location_info[ip]["authenticated"] == False:
            status = "power-off"
        page += f"<tr class={status}><td>{ips[ip]}</td><td>{users['users'] if users['users'] != None else '-'}</td><td>{(','.join(users['ssh_users'])) if len(users['ssh_users']) > 0 else '-'}</td><td>{status.upper()}</td></tr>\n"
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
    location_users = {ip: {"ssh_users": [], "users": None} for ip in ips}
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
                stdin, stdout, stderr = location_info[ip]["ssh_client"].exec_command("who")
                output = stdout.readlines()
                users = None
                ssh_users = []
                last_login_time = 1
                for line in output:
                    for spaces in range(20, 1, -1):
                        line = line.replace(' '*spaces, ' '*(spaces-1))
                    details = line.split(' ')
                    user = details[0]
                    if user not in default_users and user in all_cc_users:
                        if '-' in details[2]:
                            month = int(details[2].split('-')[1])
                            month = list(months.keys())[month-1]
                            login_date = int(details[2].split('-')[2])
                            hour = int(details[3].split(':')[0])
                            minutes = int(details[3].split(':')[1])
                            length_for_user = len(details[4])
                        else:
                            month = details[2]
                            login_date = int(details[3])
                            hour = int(details[4].split(':')[0])
                            minutes = int(details[4].split(':')[1])
                            length_for_user = len(details[5])
                        current_month = datetime.now().strftime("%B")[:3]
                        current_date = datetime.now().day
                        current_hour = datetime.now().hour
                        current_minute = datetime.now().minute
                        login_time = (months[current_month]+current_date+current_hour/24+current_minute/(24*60))-(months[month]+login_date+hour/24+minutes/(60*24))
                        if login_time < 0.5:
                            if length_for_user > 10:
                                ssh_users.append(user)
                            elif login_time < last_login_time:
                                last_login_time = login_time
                                users = user
                location_users[ip]["ssh_users"] = ssh_users
                location_users[ip]["users"] = users
                display(':', f"{Back.MAGENTA}{ip}{Back.RESET} => Users:{users}, SSH Users:{','.join(ssh_users)}")
            createPage()
            ftp_server = ftplib.FTP("webhome.cc.iitk.ac.in", arguments.webhome_user, webhome_password)
            with open(f"pages/{location}.html", 'rb') as file:
                ftp_server.storbinary(f"STOR /www/{arguments.webhome_user}/www/{location}.html", file)
            ftp_server.quit()
    except KeyboardInterrupt:
        display('*', f"Keyboard Interrupt Detected...", start='\n')
        display(':', "Exiting")
    except Exception as error:
        display('-', f"Error Occured => {Back.YELLOW}{error}{Back.RESET}")