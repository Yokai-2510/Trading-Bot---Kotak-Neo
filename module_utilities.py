import os
import json
import numpy as np
from datetime import datetime
import logging
import pandas as pd
import time 
spot_price = None
current_zone = None


# Define the log file path as 'logfile.txt' in the current directory
LOG_FILE_PATH = os.path.join(os.getcwd(), 'logfile.txt')

# Configure logging
logging.basicConfig(filename=LOG_FILE_PATH, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_message(*args):
    message = ' '.join(str(arg) for arg in args)
    logging.info(message)

def clear_log():
    try:
        with open(LOG_FILE_PATH, 'w') as f:
            pass  # Opening in write mode truncates the file
    except IOError as e:
        print(f"Unable to clear log file: {e}. Continuing without clearing.")

def read_log():
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'r') as f:
            return f.read()
    return ""

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
                log_message(f"All {max_retries+1} attempts failed. Using last fetched spot price: {spot_price}")
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
                log_message(f"All {max_retries+1} attempts failed. Using last fetched data: {option_chain_df}")
    return option_chain_df

def create_report(status_dict, zone_index):
    report_dir = 'reports'
    
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    base_filename = f'report.zone{zone_index}'
    report_filename = base_filename
    report_path = os.path.join(report_dir, report_filename + '.txt')
    
    letter = 'a'
    report_count = 1
    while os.path.exists(report_path):
        if letter <= 'z':
            report_filename = f'{base_filename}{letter}'
            letter = chr(ord(letter) + 1)
        else:
            report_filename = f'{base_filename}{report_count}'
            report_count += 1
        report_path = os.path.join(report_dir, report_filename + '.txt')

    try:
        with open(report_path, 'w') as report_file:
            for key, value in status_dict.items():
                if callable(value):
                    value = str(value())
                elif isinstance(value, (datetime, np.integer, np.floating, np.ndarray)):
                    value = str(value)
                report_file.write(f"{key}: {value}\n")
        log_message(f"Report saved to {report_path}")
    except Exception as e:
        log_message(f"Error while creating report: {e}")
        log_message("Status dict contents:")
        for key, value in status_dict.items():
            log_message(f"{key}: {type(value)} - {value}")

def calculate_mtm(status_dict):
    transaction_type = status_dict['entry_transaction_type']
    quantity = float(status_dict['real_quantity'])
    exit_ltp = float(status_dict['exit_ltp'])
    entry_ltp = float(status_dict['entry_ltp'])

    if transaction_type == 'B':
        mtm = (exit_ltp - entry_ltp) * quantity
    elif transaction_type == 'S':
        mtm = (entry_ltp - exit_ltp) * quantity
    else:
        raise ValueError("Invalid transaction type. Must be 'B' or 'S'.")
    status_dict['mtm'] = mtm
    return mtm

def display_info(spot_price, current_zone):
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear the console
    print(f"Current Spot Price: {spot_price}")
    print(f"Current Zone: {current_zone}")
    print("\nRecent Log Messages:")
    print(read_log())

if __name__ == "__main__": 
    # Test functions
    create_report({"status": "success"}, 1)
    read_option_chain()
    read_spot_price()
    display_info(spot_price, current_zone)
