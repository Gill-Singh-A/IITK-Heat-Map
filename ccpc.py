#! /usr/bin/env python3

import paramiko
from getpass import getpass
from datetime import date
from optparse import OptionParser
from multiprocessing import Pool, cpu_count, Lock
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
ccpc_users = {ip: [] for ip in ccpc_ips}
timeout = 30

parallel_threads = cpu_count()
lock = Lock()

def connectSSH(ip, user, password, port=22, timeout=30):
    try:
        t1 = time()
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=user, password=password, allow_agent=False, timeout=timeout)
        with lock:
            display('+', f"Authenticated => {Back.MAGENTA}{ip}{Back.RESET}")
        t2 = time()
        return ssh, t2-t1
    except Exception as err:
        return err, -1
def sshHandler(ip, user, password, timeout, verbose=False):
    while True:
        ssh_client, authentication_time = connectSSH(ip, user, password, 22, timeout)
        if authentication_time != -1:
            break
        display('-', f"Error Occurred while Connecting to {Back.MAGENTA}{ip}{Back.RESET} => {Back.YELLOW}{ssh_client}{Back.RESET}")
    while True:
        stdin, stdout, stderr = ssh_client.exec_command("ps -aux")
        users = list(set([line.split(' ')[0] for line in stdout.readlines()]))
        users.sort()
        with lock:
            if verbose:
                display(':', f"{Back.MAGENTA}{ip}{Back.RESET} => {','.join(users)}")
            ccpc_users[ip] = users

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
    pool = Pool(parallel_threads)
    threads = []
    for ip in ccpc_ips:
        threads.append(pool.apply_async(sshHandler, (ip, arguments.user, password, arguments.timeout)))
    for thread in threads:
        thread.get()
    pool.close()
    pool.join()