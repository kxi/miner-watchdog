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
import json
import psutil
import regex as re
from logger import make_logger

# Command: python miner_watchdog.py kai_test_miner 15 ETH multi debug
# Eth speed: 46.754 MH/s


OK = '\033[36m'
FAIL = '\033[41m'
LOG = '\033[32m'
WARNING = '\033[33m'
ENDC = '\033[0m'
READ_FLAG =[True]

current_pid = None

miner_stdout_buffer = []

LOGGER = make_logger(sys.stderr, "coin-watchdog")

def get_most_profitable_coin(coin_pos, miner_dict, default_coin):
    try:
        scope = ['https://spreadsheets.google.com/feeds']
        creds = ServiceAccountCredentials.from_json_keyfile_name('key3.json', scope)
        gc = gspread.authorize(creds)
        wks = gc.open_by_url("https://docs.google.com/spreadsheets/d/12G_XdpgLKY_nb3zYI1BWfncjMJBcqVROkHoJcXO-JcE").worksheet("Coin Switch")
        coin = wks.acell(coin_pos).value
    except Exception as e:
        print(FAIL, "[WatchDog] Exception [{}] in Fetching Coin in Gspreadsheet. Load Default Coin [{}]".format(e, default_coin), ENDC)
        return default_coin

    if coin != "stay" and coin not in miner_dict:
        print(FAIL, "[WatchDog] Unknown Coin [{}]. Load Default Coin [{}]".format(coin, default_coin), ENDC)
        return default_coin

    print(OK, "[WatchDog] Recent Most Profitable Coin is {}".format(coin), ENDC)
    return coin


def update_mining_coin(coin_pos, coin, hashrate):
    try:
        scope = ['https://spreadsheets.google.com/feeds']
        creds = ServiceAccountCredentials.from_json_keyfile_name('key3.json', scope)
        gc = gspread.authorize(creds)
        wks = gc.open_by_url("https://docs.google.com/spreadsheets/d/12G_XdpgLKY_nb3zYI1BWfncjMJBcqVROkHoJcXO-JcE").worksheet("Coin Switch")
        dt_now = datetime.now().strftime('%Y-%m-%d %H:%M')
        wks.update_acell("C"+coin_pos[1], coin)
        wks.update_acell("D"+coin_pos[1], hashrate)
        wks.update_acell("E"+coin_pos[1], dt_now)

    except Exception as e:
        print(FAIL, "[WatchDog] Fail to Upload Coin Mining Status to Spreadsheet", ENDC)
        return

    print(OK, "[WatchDog] Successfully Upload Coin Mining Status to Spreadsheet", ENDC)
    return



def run_miner(cmd_path, cmd_script):

    miner_cmd = os.path.join(cmd_path, cmd_script)
    print(miner_cmd)
    miner_proc = subprocess.Popen([miner_cmd], stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=False)

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


def kill_miner(current_pid):
    for child in psutil.Process(current_pid).children(recursive=True):
        print(child.pid)
        p = psutil.Process(child.pid)
        p.terminate()


def main():

    timeout = 300
    hostname = sys.argv[1]

    hashrate = 0.0

    if len(sys.argv) == 6 and sys.argv[-1] == 'debug':
        print(OK, "[WatchDog] Debug Mode", ENDC)
        switch_count = int(sys.argv[2]) * 2 # 15 Min = 90 Count
        status_upload_count = int(sys.argv[2])

    else:
        switch_count = int(sys.argv[2]) * 6 # 15 Min = 90 Count
        status_upload_count = int(sys.argv[2])

    last_check = datetime.now()
    count = 0

    # Load Coin in Gspread Sheet Position
    with open("coin_switch_gspread_conf.yaml", 'r') as f:
        gspread_coin_dict = yaml.load(f, Loader=yaml.FullLoader)
    coin_pos = gspread_coin_dict[hostname]

    # Load Miner Configuration include Script Name and Path
    with open("miner_conf.yaml", 'r') as f:
        miner_dict = yaml.load(f, Loader=yaml.FullLoader)

    default_coin = sys.argv[3]
    if default_coin in miner_dict:
        print(OK, "[WatchDog] Default Coin: {}".format(default_coin), ENDC)
    else:
        print(FAIL, "[WatchDog] No Such Default Coin: {}".format(default_coin), ENDC)
        sys.exit(1)


    if sys.argv[4] == "multi":
        profit_switching_flag = True
        coin = get_most_profitable_coin(coin_pos, miner_dict, default_coin)
        if coin == "stay":
            print(OK, "[WatchDog] Stay with Recent Coin. Mining Default Coin: {}".format(default_coin), ENDC)
            coin = default_coin

    else:
        profit_switching_flag = False
        coin = defult_coin

    num_algo = len(miner_dict)
    if num_algo < 2:
        profit_switching_flag = False

    print(OK, "[WatchDog] Profit Switching Enabled: {}".format(profit_switching_flag), ENDC)

    cmd_path = miner_dict[coin]['path']
    cmd_script = miner_dict[coin]['script']


    current_pid = run_miner(cmd_path, cmd_script)
    recent_coin = coin

    while True:
        count += 1
        now = datetime.now()
        time_delta = (now - last_check).total_seconds()

        if count == switch_count:
            if profit_switching_flag:
                coin = get_most_profitable_coin(coin_pos, miner_dict, default_coin)

                if coin == "stay":
                    coin = recent_coin
                    print(OK, "[WatchDog] Stay with Recent Coin [{}]".format(coin), ENDC)

                if not recent_coin == coin:
                    print(WARNING, "[WatchDog] Most Profitable Coin Changes, Restart >>>>>>>> ")
                    print(WARNING, "[WatchDog] Killing Recent Mining Process ")
                    kill_miner(current_pid)
                    READ_FLAG[0] = False
                    time.sleep(10)

                    print(" [WatchDog] Miner Restarting, Wait... ")
                    READ_FLAG[0] = True
                    cmd_path = miner_dict[coin]['path']
                    cmd_script = miner_dict[coin]['script']

                    recent_coin = coin
                    current_pid = run_miner(cmd_path, cmd_script)
                    last_check = datetime.now()
                    print(" [WatchDog] Miner Restarting Complete >>>>>>>>", ENDC)
            count = 0

        if count == status_upload_count:
            update_mining_coin(coin_pos, recent_coin, hashrate)

        if time_delta <= timeout:
            print(OK, "[WatchDog] Mining [{}]. Now = {}, Last = {}, Elapsed = {} Sec".format(recent_coin, now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)

        if time_delta > timeout:
            print(FAIL, "[WatchDog] Mining [{}]. Now = {}, Last = {}, Elapsed = {} Sec".format(recent_coin, now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)
            print(WARNING, "Miner is Not Responsive, Restart ---> ")
            kill_miner(current_pid)
            READ_FLAG[0] = False
            print("Miner Restarting, Wait ---> ")
            time.sleep(30)
            READ_FLAG[0] = True
            current_pid = run_miner(cmd_path, cmd_script)
            last_check = datetime.now()
            print("Miner Restarting Complete ---> ", ENDC)

        while miner_stdout_buffer:
            status =(miner_stdout_buffer.pop()).decode(errors='ignore').rstrip('\n')
            time_stamp = re.search(r'\d{4}-\d{2}-\d{2}\s{1}\d{2}:\d{2}:\d{2}', status)
            hashrate_check = re.search(r'Eth speed:\ (\d+.\d+\ )[mMgGH]+\/s.*', status)
            
            if hashrate_check != None:
                hashrate = hashrate_check[1]
                last_check = datetime.now()
            print(LOG, "[Miner]  ", ENDC, status)
            if time_stamp:
                # print(time_stamp.group(0))
                last_check = datetime.strptime(time_stamp.group(0), '%Y-%m-%d %H:%M:%S')

        time.sleep(10)


main()
