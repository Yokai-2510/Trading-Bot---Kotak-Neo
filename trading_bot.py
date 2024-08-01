
strategy_dict = {

    "quantity" : '2', # Enter the Quantity ( in lots)
    "order_type" : "MKT" , # L for LIMIT and MKT for MARKET
    "limit_price" : "0" , # if order type is limit , then put the limit value
    "index" : "NIFTY" , # BANKNIFTY or NIFTY
    "ikey_criteria" : "LTP" , # Possible Values : STRIKE , ATM , ITM , LTP
    "ikey_criteria_value" : "130" , # only applicable for STRIKE and LTP otherwise 0
    "AMO" : "False" , # YES  or NO (after market order)
    "global_loss" : "1" , # Global stop loss - will supersede strategy stop loss
    "global_profit" : "1" , # Global profit - will supersede strategy profit 
    "strategy_loss" : "1" , # stop loss at strategy level
    "strategy_profit" : "1" , # profit/target at strategy level
    "market_open" : "6:15" , # Time at which the Market Opens
    "market_close" : "15:28" , # Time at which the Market closes
    "exit_time" : "7:36" , # supersede risk conditions if exit time is met.
}

status_dict = {
    
    'zone_index': "",  # Index of the current trading zone
    'option_type': "",  # Type of the option (e.g., call, put)
    'order_completion': "",  # Status of order completion
    'order_ikey': "",  # Instrument key for entry order 
    'order_status' : "" , # Current status of the order / strategy
    'order_strike': "",  # Strike price at entry order placement
    'mtm' : ' ',    # MTM of each order that has been squared off
    'real_quantity' : '' , # Total Quanity , lot size x  number of lots
    'current_ltp' : '' , # shows the current ltp of the selected instrument at various phases of the order
    
    'entry_transaction': "",  # Type of entry transaction (buy or sell)
    'entry_success': "",  # Status of entry order success
    'entry_ltp': "",  # Last traded price at entry order         
    'entry_time': "",  # Time at entry order placement
    'entry_spot': "",  # Spot price at entry order placement
    
    'exit_transaction': "",  # Type of exit transaction (buy or sell) Compliment of Entry 
    'exit_success': "",  # Status of exit order success
    'exit_criteria': "",  # Criteria for exit order
    'exit_ltp': "",  # Last traded price at exit
    'exit_time': "",  # Time of exit order
    'exit_spot': "",  # Spot price at exit order placement
}

