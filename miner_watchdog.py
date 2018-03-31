import subprocess
import sys
import os
import time
from datetime import datetime
import re
from threading import Thread, Event

READ_FLAG =[True]

linebuffer=[]

def run_miner(cmd_name, cmd_path):
    proc = subprocess.Popen(cmd_name, cwd=cmd_path,
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
    output = proc.stdout

    def reader(f, buffer):
        while READ_FLAG[0] == True:
            line=f.readline()
            if line:
                buffer.append(line)
            else:
                # print("Read Over")
                break

    t = Thread(target=reader,args=(output, linebuffer))
    t.daemon=True
    t.start()

def kill_miner():
    proc = subprocess.Popen("taskkill /im ccminer.exe /f", stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)

def main():

    OK = '\033[36m'
    FAIL = '\033[41m'
    LOG = '\033[32m'
    WARNING = '\033[33m'
    ENDC = '\033[0m'

    cmd_name = sys.argv[1]
    cmd_path = sys.argv[2]
    timeout = int(sys.argv[3])

    last_check = datetime.now()
    count = 0

    run_miner(cmd_name, cmd_path)

    while True:
        count += 1
        now = datetime.now()
        time_delta = (now - last_check).total_seconds()

        if time_delta <= timeout:
            print(OK, "[WatchDog] Now = {}, Last = {}, Elapsed = {} Sec".format(now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)

        if time_delta > timeout:
            print(FAIL, "[WatchDog] Now = {}, Last = {}, Elapsed = {} Sec".format(now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)
            print(WARNING, "Miner is Not Responsive, Restart ---> ")
            kill_miner()
            READ_FLAG[0] = False
            print("Miner Restarting, Wait ---> ")
            time.sleep(10)
            READ_FLAG[0] = True
            run_miner(cmd_name, cmd_path)
            last_check = datetime.now()
            print("Miner Restarting Complete ---> ", ENDC)

        while linebuffer:
            status =(linebuffer.pop()).decode(errors='ignore').rstrip('\n')
            time_stamp = re.search(r'\d{4}-\d{2}-\d{2}\s{1}\d{2}:\d{2}:\d{2}', status)
            print(LOG, "[Miner]  ", ENDC, status)
            if time_stamp:
                # print(time_stamp.group(0))
                last_check = datetime.strptime(time_stamp.group(0), '%Y-%m-%d %H:%M:%S')

        time.sleep(10)


main()
