# module_order.py

import math
import pandas as pd
import time
from datetime import datetime
from module_utilities import create_report, read_option_chain, read_spot_price , calculate_mtm,log_message
from config import strategy_dict
from module_utilities import log_message


indicators = {}
client = None  # Replace with actual client object    
option_type = None
zone_index = None


def select_ikey(strategy_dict, status_dict, spot_price, nifty_options_df,option_type):

    def ikey_atm(nifty_options_df, spot_price, status_dict,option_type):
        if option_type == 'CE':
            atm_strike = math.ceil(spot_price / 100) * 100
        elif option_type == 'PE':
            atm_strike = math.floor(spot_price / 100) * 100
        
        filtered_df = nifty_options_df[(nifty_options_df['option_type'] == option_type) & 
                                       (nifty_options_df['strike_price'] == atm_strike)]
        
        if not filtered_df.empty:
            instrument_key = filtered_df.iloc[0]['instrument_key']
            status_dict['order_strike'] = atm_strike
            status_dict['order_ikey'] = instrument_key
            return instrument_key
        else:
            return None

    def ikey_itm(nifty_options_df, spot_price, status_dict,option_type):
        if option_type == 'CE':
            itm_strike = math.floor((spot_price - 1) / 100) * 100
        elif option_type == 'PE':
            itm_strike = math.ceil((spot_price + 1) / 100) * 100
        
        filtered_df = nifty_options_df[(nifty_options_df['option_type'] == option_type) & 
                                       (nifty_options_df['strike_price'] == itm_strike)]
        
        if not filtered_df.empty:
            instrument_key = filtered_df.iloc[0]['instrument_key']
            status_dict['order_strike'] = itm_strike
            status_dict['order_ikey'] = instrument_key
            return instrument_key
        else:
            return None

    def ikey_ltp(nifty_options_df, strategy_dict, status_dict, option_type):
        preferred_ltp = float(strategy_dict['ikey_criteria_value'])
        filtered_options = nifty_options_df[nifty_options_df['option_type'] == option_type].copy()
        
        if filtered_options.empty:
            log_message(f"No options found for type {option_type}")
            return None
        
        filtered_options['ltp_diff'] = abs(filtered_options['ltp'] - preferred_ltp)
        nearest_option = filtered_options.loc[filtered_options['ltp_diff'].idxmin()]
        
        status_dict['order_strike'] = nearest_option['strike_price']
        status_dict['order_ikey'] = nearest_option['instrument_key']
        return nearest_option['instrument_key']
    
    def ikey_strike(nifty_options_df, strategy_dict, status_dict, option_type):
        preferred_strike = float(strategy_dict['ikey_criteria_value'])
        filtered_options = nifty_options_df[nifty_options_df['option_type'] == option_type].copy()
        
        if filtered_options.empty:
            log_message(f"No options found for type {option_type}")
            return None
        
        filtered_options['strike_diff'] = abs(filtered_options['strike_price'] - preferred_strike)
        nearest_option = filtered_options.loc[filtered_options['strike_diff'].idxmin()]
        
        status_dict['order_strike'] = nearest_option['strike_price']
        status_dict['order_ikey'] = nearest_option['instrument_key']
        return nearest_option['instrument_key']

    if strategy_dict['ikey_criteria'] == 'ATM':
        return ikey_atm(nifty_options_df, spot_price, status_dict,option_type)
    elif strategy_dict['ikey_criteria'] == 'ITM':
        return ikey_itm(nifty_options_df, spot_price, status_dict,option_type)
    elif strategy_dict['ikey_criteria'] == 'LTP':
        return ikey_ltp(nifty_options_df, strategy_dict, status_dict,option_type)
    elif strategy_dict['ikey_criteria'] == 'STRIKE':
        return ikey_strike(nifty_options_df, strategy_dict, status_dict , option_type)
    else:
        log_message(f"Invalid ikey_criteria: {strategy_dict['ikey_criteria']}")
        return None


def initialize_status_dict(status_dict, zone_index, option_type, instrument_key):
    now = datetime.now()
    df = read_option_chain()

    status_dict.update({
        'index': strategy_dict['index'],
        'order_status': 'Defining entry conditions, proceeding to Entry Order',
        'zone_index': zone_index,
        'mtm': None,
        'order_ikey': instrument_key,
        'order_strike': df.loc[df['instrument_key'] == instrument_key, 'strike_price'].values[0],
        'option_type': option_type,
        'real_quantity': None,
        'current_ltp': None,

        'entry_transaction_type': 'B' if zone_index in [1, 5] else 'S',
        'entry_order_id': None,
        'entry_success': False,
        'entry_spot': None,
        'entry_ltp': None,
        'entry_time': None,

        'exit_transaction_type': 'S' if zone_index in [1, 5] else 'B',
        'exit_order_id': None,
        'exit_success': False,
        'exit_criteria': None,
        'exit_ltp': None,
        'exit_time': None,
        'exit_spot': None,

    })


def place_order(client, status_dict, instrument_key, strategy_dict, order_flag):

    try:
        # Determine transaction type based on order_flag
        if order_flag == 'ENTRY':
            transaction = status_dict.get('entry_transaction_type')
        elif order_flag == 'EXIT':
            transaction = status_dict.get('exit_transaction_type')
        else:
            log_message("Invalid order_flag")
            return False


        # Determine quantity based on the index
        if strategy_dict.get('index') == 'BANKNIFTY':
            quantity = str(int(strategy_dict.get('quantity', 0)) * 15)
        elif strategy_dict.get('index') == 'NIFTY':
            quantity = str(int(strategy_dict.get('quantity', 0)) * 25)

        status_dict['real_quantity'] = quantity

        # Determine order parameters
        limit_price = '0' if strategy_dict.get('order_type') != 'LIMIT' else str(strategy_dict.get('limit_price', 0))
        order_type = 'L' if strategy_dict.get('order_type') == 'LIMIT' else 'MKT'
        #amo_flag = 'YES' if strategy_dict.get('AMO') == 'TRUE' else 'NO'
        print("quantity" , quantity)
        # Place the order
        order_response = client.place_order(

            price = '0',
            order_type = 'MKT' ,
            quantity = quantity,
            trading_symbol = instrument_key ,
            transaction_type = transaction,
            
            exchange_segment="nse_fo",
            product="NRML",
            validity = "DAY",
            amo = 'NO',
            disclosed_quantity = "0",
            pf="N",
            trigger_price = "0",
            market_protection="0",
            tag = '' )


        # Handle the order response
        log_message("order response", order_response)

        if order_response.get('stat') == 'Ok' and 'nOrdNo' in order_response:
            order_id = order_response['nOrdNo']
            status_dict['entry_order_id'] = order_id 
            log_message("Debug: Entry Order ID before creating report:", status_dict.get('entry_order_id'))
            log_message("Debug: Exit Order ID before creating report:", status_dict.get('exit_order_id')) 
            if order_flag == 'ENTRY' :
                status_dict['entry_success'] = True
                status_dict['entry_order_id'] = order_id

            if order_flag == 'EXIT' :
                status_dict['exit_success'] = True
                status_dict['exit_order_id'] = order_id
            return True
        else:
            
            if order_flag == 'ENTRY' :
                status_dict['entry_success'] = False
                
            if order_flag == 'EXIT' :
                status_dict['exit_success'] = False

            return False

    except Exception as e:
        log_message(f"Exception when placing order: {e}")
        if order_flag == 'ENTRY' :
            status_dict['entry_success'] = False

        if order_flag == 'EXIT' :
            status_dict['exit_success'] = False
        return False


def update_entry_status(client, status_dict,instrument_key ):
    entry_order_id = status_dict['entry_order_id']
    now = datetime.now
    spot_price = read_spot_price()
    options_df = read_option_chain()
    ltp = options_df.loc[options_df['instrument_key'] == instrument_key, 'ltp'].values[0]
    
    status_dict['entry_success'] = "True"
    status_dict['entry_ltp'] = ltp
    status_dict['entry_time'] = now
    status_dict['entry_spot'] = spot_price

    order_details = client.order_history(order_id=str(entry_order_id))

    if order_details['data']["stat"] == 'Ok':
        #data = order_details['data'][0]
        #status_dict['entry_success'] = "False" if data['ordSt'] == "rejected" else "True"

        status_dict['order_status'] = 'Entry Order Placed successfully , checking exit conditions'
    else:
        status_dict['entry_success'] = False


def evaluate_exit(zone_index, strategy_dict, status_dict, indicators):

    if status_dict.get('entry_success') is False:
        status_dict['exit_success'] = 'Entry Order Failed, hence no exit order placed'
        return False
    
    
    def zonal_exit_conditions(zone_index, spot_price, indicator, status_dict):
        if zone_index == 1 and spot_price > indicator['low']:         
            status_dict['exit_criteria'] = 'Spot price reached below low hence squared off'
            return True
        
        if zone_index == 2 and spot_price > indicator['min_close']:
            status_dict['exit_criteria'] = 'Spot price reached above min close hence squared off'
            return True
        
        if zone_index == 3 and spot_price > indicator['max_close']:
            status_dict['exit_criteria'] = 'Spot price reached above max close hence squared off'
            return True

        if zone_index == 3 and spot_price < indicator['min_close']:
            status_dict['exit_criteria'] = 'Spot price reached below min close hence squared off'
            return True

        if zone_index == 4 and spot_price < indicator['max_close']:
            status_dict['exit_criteria'] = 'Spot price reached below max close hence squared off'
            return True

        if zone_index == 5 and spot_price < indicator['high']:
            status_dict['exit_criteria'] = 'Spot price reached below high hence squared off'
            return True

        return False

    while True:
        time.sleep(1)
        options_df = read_option_chain()
        spot_price = read_spot_price()
        row = options_df[options_df['instrument_key'] == status_dict['order_ikey']]
        status_dict['order_status'] = 'Checking Exit Conditions...'
        if row.empty:
            continue

        current_ltp = row.iloc[0]['ltp']
        status_dict['current_ltp'] = current_ltp
        entry_ltp = float(status_dict['entry_ltp'])
        
        global_profit = entry_ltp + float(strategy_dict.get('global_profit', 0))
        strategy_profit = entry_ltp + float(strategy_dict.get('strategy_profit', 0))
        global_loss = entry_ltp - float(strategy_dict.get('global_loss', 0))
        strategy_loss = entry_ltp - float(strategy_dict.get('strategy_loss', 0))
        exit_time_str = strategy_dict.get('exit_time', '3:28')
        exit_time = datetime.strptime(exit_time_str, '%H:%M').time()
        exit_time_today = datetime.combine(datetime.now().date(), exit_time)

        if current_ltp >= global_profit:
            status_dict['exit_criteria'] = 'global_profit'
            return True
        if current_ltp >= strategy_profit:
            status_dict['exit_criteria'] = 'strategy_profit'
            return True
        if current_ltp <= global_loss:
            status_dict['exit_criteria'] = 'global_loss'
            return True
        if current_ltp <= strategy_loss:
            status_dict['exit_criteria'] = 'strategy_loss'
            return True
        if datetime.now() > exit_time_today:
            status_dict['exit_criteria'] = 'market_close'
            print("exit time criteria met")
            return True
        if zonal_exit_conditions(zone_index, spot_price, indicators, status_dict):
            print("Zonal Criteria met")
            return True
    

def update_exit_status(client, status_dict,instrument_key):
    exit_order_id = status_dict['exit_order_id']
    order_details = client.order_history(order_id=str(exit_order_id))
    now = datetime.now
    spot_price = read_spot_price()
    options_df = read_option_chain()
    ltp = options_df.loc[options_df['instrument_key'] == instrument_key, 'ltp'].values[0]
    status_dict['exit_success'] = "True"
    status_dict['exit_ltp'] = ltp
    status_dict['exit_time'] = now
    status_dict['exit_spot'] = spot_price
    status_dict['order_status'] = 'Exit Order Placed Successfully'
    #print("order details" , order_details)

    #if order_details['data']['stat'] == 'Ok':
        #data = order_details['data'][0]

    #status_dict['exit_success'] = False



def execute_order(zone_index, option_type, indicators , strategy_dict,  client):

    # Assign Necessary Flags for Order Evaluation and Setup Status Dict 
    #------------------------------------------------------------------------------------------------------
    status_dict = {}
    nifty_options_df = read_option_chain()
    spot_price = read_spot_price()
    instrument_key = select_ikey(strategy_dict, status_dict, spot_price, nifty_options_df, option_type)
    if instrument_key is None:
        create_report(status_dict, zone_index)
        log_message(f"No suitable instrument found for option_type: {option_type}")
        return
    else :
        log_message("instrument key : " , instrument_key)
    initialize_status_dict(status_dict, zone_index, option_type, instrument_key)
    #------------------------------------------------------------------------------------------------------


    # Place the Entry Order
    #------------------------------------------------------------------------------------------------------
    if  place_order(client, status_dict, instrument_key, strategy_dict, 'ENTRY') is  False :
        status_dict['order_status'] = ['Entry Order Failed . Order Cancelled']
        create_report (status_dict,zone_index)
        return
    update_entry_status(client, status_dict , instrument_key)
    #------------------------------------------------------------------------------------------------------


    #Check EXIT order conditions and place exit order 
    #------------------------------------------------------------------------------------------------------
    if evaluate_exit(zone_index, strategy_dict, status_dict, indicators) == True: 
        if  place_order(client, status_dict, instrument_key, strategy_dict, 'EXIT') is True :
            update_exit_status(client, status_dict, instrument_key)
            status_dict['order_status'] = 'Exit order placed, Order Complete ! Report saved'
            log_message(f"Order Completed successfully for zone {zone_index}")
            calculate_mtm(status_dict)
            create_report(status_dict, zone_index)
            return   
        else:
            status_dict['order_status'] = 'Exit Order could not take place , if order is pending, square off manually'
            create_report(status_dict, zone_index)
            return      
    else :
        status_dict['order_status'] =  "unknown_error within exit evaluation , order cancelled"
        create_report(status_dict, zone_index)
        return
    #------------------------------------------------------------------------------------------------------


if __name__ == "__main__" :
    # Example usage    
    execute_order(zone_index, client, option_type, strategy_dict, indicators)
