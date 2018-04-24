import subprocess
import sys
import os
import time
from datetime import datetime
import re
from threading import Thread, Event
import select
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yaml

OK = '\033[36m'
FAIL = '\033[41m'
LOG = '\033[32m'
WARNING = '\033[33m'
ENDC = '\033[0m'
READ_FLAG =[True]

miner_stdout_buffer = []

def run_miner(cmd_name, cmd_path):
    miner_proc = subprocess.Popen(cmd_name, cwd=cmd_path,
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
    miner_stdout = miner_proc.stdout

    def reader(stdout_pipe, miner_stdout_buffer):
        while READ_FLAG[0] == True:
            line = stdout_pipe.readline()
            if line:
                miner_stdout_buffer.append(line)
            else:
                break

    thread = Thread(target=reader, args=(miner_stdout, miner_stdout_buffer))
    thread.daemon = True
    thread.start()

def kill_miner():
    proc = subprocess.Popen("taskkill /im ccminer.exe /f", stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)

def main():

    timeout = 300

    last_check = datetime.now()
    count = 0
    coin = sys.argv[1]


    # Load Miner Configuration include Script Name and Path
    with open("miner_conf.yaml", 'r') as f:
        miner_dict = yaml.load(f)

    if coin not in miner_dict:
        coin = "raven"

    cmd_name = miner_dict[coin]['script']
    cmd_path = miner_dict[coin]['path']
    run_miner(cmd_name, cmd_path)

    while True:
        count += 1
        now = datetime.now()
        time_delta = (now - last_check).total_seconds()

        if time_delta <= timeout:
            print(OK, "[WatchDog] Mining [{}]. Now = {}, Last = {}, Elapsed = {} Sec".format(coin, now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)

        if time_delta > timeout:
            print(FAIL, "[WatchDog] Mining [{}]. Now = {}, Last = {}, Elapsed = {} Sec".format(coin, now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)
            print(WARNING, "Miner is Not Responsive, Restart ---> ")
            kill_miner()
            READ_FLAG[0] = False
            print("Miner Restarting, Wait ---> ")
            time.sleep(60)
            READ_FLAG[0] = True
            run_miner(cmd_name, cmd_path)
            last_check = datetime.now()
            print("Miner Restarting Complete ---> ", ENDC)

        while miner_stdout_buffer:
            status =(miner_stdout_buffer.pop()).decode(errors='ignore').rstrip('\n')
            time_stamp = re.search(r'\d{4}-\d{2}-\d{2}\s{1}\d{2}:\d{2}:\d{2}', status)
            print(LOG, "[Miner]  ", ENDC, status)
            if time_stamp:
                # print(time_stamp.group(0))
                last_check = datetime.strptime(time_stamp.group(0), '%Y-%m-%d %H:%M:%S')

        time.sleep(10)


main()
