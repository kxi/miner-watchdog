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
import socket

OK = '\033[36m'
FAIL = '\033[41m'
LOG = '\033[32m'
WARNING = '\033[33m'
ENDC = '\033[0m'
READ_FLAG =[True]

miner_stdout_buffer = []

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


def update_mining_coin(coin_pos, coin):
    try:
        scope = ['https://spreadsheets.google.com/feeds']
        creds = ServiceAccountCredentials.from_json_keyfile_name('key3.json', scope)
        gc = gspread.authorize(creds)
        wks = gc.open_by_url("https://docs.google.com/spreadsheets/d/12G_XdpgLKY_nb3zYI1BWfncjMJBcqVROkHoJcXO-JcE").worksheet("Coin Switch")
        dt_now = datetime.now().strftime('%Y-%m-%d %H:%M')
        wks.update_acell("C"+coin_pos[1], coin)
        wks.update_acell("D"+coin_pos[1], dt_now)

    except Exception as e:
        print(FAIL, "[WatchDog] Fail to Upload Coin Mining Status to Spreadsheet", ENDC)
        return

    print(OK, "[WatchDog] Successfully Upload Coin Mining Status to Spreadsheet", ENDC)
    return

def run_miner(cmd_name, cmd_path):
    # miner_proc = subprocess.Popen(cmd_name, cwd=cmd_path,
                            # stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
    miner_proc = subprocess.Popen(os.path.join(cmd_path, cmd_name),
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)

    print(OK, "[WatchDog] Command = {}".format(os.path.join(cmd_path, cmd_name)), ENDC)

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


def kill_miner(cmd_miner):
    if os.name == 'posix':
        proc = subprocess.Popen("killall {}".format(cmd_miner), stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
    else:
        proc = subprocess.Popen("taskkill /im {} /f".format(cmd_miner), stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)

def main():

    timeout = 300
    hostname = str(socket.gethostname())

    if len(sys.argv) == 5 and sys.argv[-1] == 'debug':
        print(OK, "[WatchDog] Debug Mode", ENDC)
        switch_count = int(sys.argv[2]) * 2 # 15 Min = 90 Count
        status_upload_count = int(sys.argv[2])

    else:
        switch_count = int(sys.argv[1]) * 6 # 15 Min = 90 Count
        status_upload_count = int(sys.argv[1])

    last_check = datetime.now()
    count = 0

    # Load Coin in Gspread Sheet Position
    with open("coin_switch_gspread_conf.yaml", 'r') as f:
        gspread_coin_dict = yaml.load(f)
    coin_pos = gspread_coin_dict[hostname]

    # Load Miner Configuration include Script Name and Path
    with open("miner_conf.yaml", 'r') as f:
        miner_dict = yaml.load(f)

    default_coin = sys.argv[2]
    if default_coin in miner_dict:
        print(OK, "[WatchDog] Default Coin: {}".format(default_coin), ENDC)
    else:
        print(FAIL, "[WatchDog] No Such Default Coin: {}".format(default_coin), ENDC)
        sys.exit(1)


    if sys.argv[3] == "multi":
        profit_switching_flag = True
        coin = get_most_profitable_coin(coin_pos, miner_dict, default_coin)
        if coin == "stay":
            print(OK, "[WatchDog] Stay with Recent Coin. Mining Default Coin: {}".format(default_coin), ENDC)
            coin = default_coin

    else:
        profit_switching_flag = False
        coin = default_coin

    num_algo = len(miner_dict)
    if num_algo < 2:
        profit_switching_flag = False

    print(OK, "[WatchDog] Profit Switching Enabled: {}".format(profit_switching_flag), ENDC)

    cmd_name = miner_dict[coin]['script']
    cmd_path = miner_dict[coin]['path']
    cmd_miner = miner_dict[coin]['miner']

    run_miner(cmd_name, cmd_path)
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
                    kill_miner(cmd_miner)
                    READ_FLAG[0] = False
                    time.sleep(10)

                    print(" [WatchDog] Miner Restarting, Wait... ")
                    READ_FLAG[0] = True
                    cmd_name = miner_dict[coin]['script']
                    cmd_path = miner_dict[coin]['path']
                    cmd_miner = miner_dict[coin]['miner']
                    recent_coin = coin
                    run_miner(cmd_name, cmd_path)
                    last_check = datetime.now()
                    print(" [WatchDog] Miner Restarting Complete >>>>>>>>", ENDC)
            count = 0

        if count == status_upload_count:
            update_mining_coin(coin_pos, recent_coin)

        if time_delta <= timeout:
            print(OK, "[WatchDog] Mining [{}]. Now = {}, Last = {}, Elapsed = {} Sec".format(recent_coin, now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)

        if time_delta > timeout:
            print(FAIL, "[WatchDog] Mining [{}]. Now = {}, Last = {}, Elapsed = {} Sec".format(recent_coin, now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    last_check.strftime("%Y-%m-%d %H:%M:%S"),
                                                                    int(time_delta)), ENDC)
            print(WARNING, "Miner is Not Responsive, Restart ---> ")
            kill_miner(cmd_miner)
            READ_FLAG[0] = False
            print("Miner Restarting, Wait ---> ")
            time.sleep(30)
            READ_FLAG[0] = True
            run_miner(cmd_name, cmd_path)
            last_check = datetime.now()
            print("Miner Restarting Complete ---> ", ENDC)

        while miner_stdout_buffer:

            time_stamp = None

            status =(miner_stdout_buffer.pop()).decode(errors='ignore').rstrip('\n')

            if cmd_miner == "ccminer":
                time_stamp = re.search(r'\d{4}-\d{2}-\d{2}\s{1}\d{2}:\d{2}:\d{2}', status)

            if cmd_miner == "z-enemy":
                time_stamp = re.search(r'\d{2}/\d{2}/\d{2}\s{1}\d{2}:\d{2}:\d{2}', status)

            print(LOG, "[Miner]  ", ENDC, status)

            if time_stamp:
                # print(time_stamp.group(0))
                if cmd_miner == "ccminer":
                    last_check = datetime.strptime(time_stamp.group(0), '%Y-%m-%d %H:%M:%S')

                if cmd_miner == "z-enemy":
                    last_check = datetime.strptime(time_stamp.group(0), '%y/%m/%d %H:%M:%S')

            else:
                last_check = datetime.now()

        time.sleep(10)


main()
