# module_utilities.py

import pandas as pd
import time 
import os
import json
from config import strategy_dict
import json
import os
import numpy as np
from datetime import datetime



def parse_time(time_str):
    return datetime.strptime(time_str, "%H:%M").time()

def read_spot_price(file_path='spot_price.csv', max_retries=20, delay=0.05, default_spot_price=None):
    spot_price = default_spot_price
    for attempt in range(max_retries + 1):
        try:
            df = pd.read_csv(file_path)
            if not df.empty:
                spot_price = float(df.iloc[-1]['value'])
                break
        except (pd.errors.EmptyDataError, FileNotFoundError) as e:
            if attempt < max_retries:
                time.sleep(delay)
            else:
                print(f"All {max_retries+1} attempts failed. Using last fetched spot price: {spot_price}")
    return spot_price


def read_option_chain(file_path='option_chain.csv', max_retries=20, delay=0.05, default_df=None):
    option_chain_df = default_df
    for attempt in range(max_retries + 1):
        try:
            option_chain_df = pd.read_csv(file_path)
            if not option_chain_df.empty:
                break
        except (pd.errors.EmptyDataError, FileNotFoundError) as e:
            if attempt < max_retries:
                time.sleep(delay)
            else:
                print(f"All {max_retries+1} attempts failed. Using last fetched data: {option_chain_df}")
    return option_chain_df



def create_report(status_dict, zone_index):
    report_dir = 'reports'
    
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    base_filename = f'report.zone{zone_index}'
    report_filename = base_filename
    report_path = os.path.join(report_dir, report_filename + '.json')
    
    letter = 'a'
    report_count = 1
    while os.path.exists(report_path):
        if letter <= 'z':
            report_filename = f'{base_filename}{letter}'
            letter = chr(ord(letter) + 1)
        else:
            report_filename = f'{base_filename}{report_count}'
            report_count += 1
        report_path = os.path.join(report_dir, report_filename + '.json')

    def json_serial(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Type {type(obj)} not serializable")

    try:
        with open(report_path, 'w') as report_file:
            json.dump(status_dict, report_file, indent=4, default=json_serial)
        print(f"Report saved to {report_path}")
    except Exception as e:
        print(f"Error while creating report: {e}")
        print("Status dict contents:")
        for key, value in status_dict.items():
            print(f"{key}: {type(value)} - {value}")


def calculate_mtm(status_dict):

    transaction_type = status_dict['entry_transaction_type']
    quantity = float(status_dict['real_quantity'])
    exit_ltp = float(status_dict['exit_ltp'])
    entry_ltp = float(status_dict['entry_ltp'])

    if transaction_type == 'BUY' :
        mtm = (exit_ltp - entry_ltp) * quantity
    elif transaction_type == 'SELL':
        mtm = (entry_ltp - exit_ltp) * quantity
    else:
        raise ValueError("Invalid transaction type. Must be 'Buy' or 'Sell'.")
    status_dict['mtm'] = mtm
    return mtm


if __name__ == "__main__": 
    create_report()
    read_option_chain()
    read_spot_price()
