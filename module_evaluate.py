# module_evaluate.py

import threading
from datetime import datetime, timedelta
import time 
from module_utilities import read_spot_price, read_option_chain, create_report
from module_order import execute_order
from config import strategy_dict


def monitor_price(current_price, indicator):
    if current_price > indicator['high']:
        return 5
    elif indicator['high'] >= current_price > indicator['max_close']:
        return 4
    elif indicator['max_close'] >= current_price > indicator['min_close']:
        return 3
    elif indicator['min_close'] >= current_price > indicator['low']:
        return 2
    else:
        return 1


def assign_zone_order(zone: int, client, indicator, strategy_dict):
    if zone == 5:
        threading.Thread(target=execute_order, args=(zone, 'CE', indicator, strategy_dict, client)).start()
    elif zone == 4:
        threading.Thread(target=execute_order, args=(zone, 'PE', indicator, strategy_dict, client)).start()
    elif zone == 3:
        threading.Thread(target=execute_order, args=(zone, "CE", indicator, strategy_dict, client)).start()
        threading.Thread(target=execute_order, args=(zone, "PE", indicator, strategy_dict, client)).start()
    elif zone == 2:
        threading.Thread(target=execute_order, args=(zone, "CE", indicator, strategy_dict, client)).start()
    elif zone == 1:
        threading.Thread(target=execute_order, args=(zone, "PE", indicator, strategy_dict, client)).start()


def start_strategy(client, spot_price, indicator, current_zone, last_processed_price, strategy_dict):
    if spot_price is not None and spot_price != last_processed_price:
        print(f"Current spot price: {spot_price}")
        new_zone = monitor_price(spot_price, indicator)
        
        if new_zone != current_zone:
            print(f"Zone changed from {current_zone} to {new_zone}")
            assign_zone_order(new_zone, client , indicator, strategy_dict)
            print("strategy started for " , new_zone)
            current_zone = new_zone
        
        last_processed_price = spot_price
    
    return current_zone, last_processed_price

