import subprocess
import sys
import os
import time
from datetime import datetime
import re
from threading import Thread, Event
import select
import signal
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yaml
import json
import psutil


OK = '\033[36m'
FAIL = '\033[41m'
LOG = '\033[32m'
WARNING = '\033[33m'
ENDC = '\033[0m'
READ_FLAG =[True]

miner_stdout_buffer = []


# def run_miner(cmd_name, cmd_path):
    # miner_proc = subprocess.Popen(cmd_name, cwd=cmd_path,
    #                         stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)

def run_miner(coin_name):

    # miner_proc = subprocess.Popen(f"~/mining/{coin_name}/RUN-ETC-Test",
    #                         stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=False)
    miner_proc = subprocess.Popen([f"/home/coin/mining/{coin_name}/RUN-{coin_name}-Test"],
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=False)
    miner_stdout = miner_proc.stdout

    current_pid = miner_proc.pid
    print(f"Current Miner PID = {current_pid}")


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
    return current_pid

def kill_miner(cmd_miner):
    proc = subprocess.Popen(f"kill {current_pid}", stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)


def main():
    mining_coin_name = 'ETC'
    current_pid = run_miner(mining_coin_name)

    # miner_proc = subprocess.Popen(['/bin/bash', f"~/mining/{coin_name}/RUN-ETC-Test"],
                        # stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=False)
    # miner_proc = subprocess.Popen([f"mining/{coin_name}/RUN-{coin_name}-Test"],
    #                         stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=False)
    # miner_proc_output = miner_proc.stdout
    # print(f"Output: {miner_proc_output.readline()}")
    # miner_proc_output = miner_proc.stderr
    # print(f"Error: {miner_proc_output.readline()}")

    # counter = 0
    while True:

        with open (f"most_profitable_coin.json", 'r') as file:
            most_profitable_coin = json.load(file)['name']

        while miner_stdout_buffer:
            status =(miner_stdout_buffer.pop()).decode(errors='ignore').rstrip('\n')
            time_stamp = re.search(r'\d{4}-\d{2}-\d{2}\s{1}\d{2}:\d{2}:\d{2}', status)
            print(LOG, "[Miner]  ", ENDC, status)
            if time_stamp:
                # print(time_stamp.group(0))
                last_check = datetime.strptime(time_stamp.group(0), '%Y-%m-%d %H:%M:%S')
        time.sleep(5)
        # counter += 5

        print(f"Current Mining Coin = {mining_coin_name}, Most Profitable Coin = {most_profitable_coin}")
        for child in psutil.Process(current_pid).children(recursive=True):
            print(child.pid)

        if most_profitable_coin != mining_coin_name:
            for child in psutil.Process(current_pid).children(recursive=True):
                print(child.pid)
                # os.killpg(child.pid, signal.SIGTERM)
                p = psutil.Process(child.pid)
                p.terminate()
            mining_coin_name = most_profitable_coin
            current_pid = run_miner(mining_coin_name)


    # miner_proc = subprocess.Popen(f"~/mining/{coin_name}/RUN-ETC",
    #                         stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
    # miner_stdout = miner_proc.stdout
    # miner_stderr = miner_proc.stderr

    # while True:
    #     with open ("get_most_profitable_coin.json", 'r') as file:
    #         coin_dict = json.load(file)
    #
    #     if coin_dict['name']!=coin_name:
    #         run_miner(coin_name)
    #
    #     time.sleep 15;

main()
