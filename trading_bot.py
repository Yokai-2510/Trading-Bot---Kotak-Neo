# trading_bot.py

import threading
from datetime import datetime, timedelta
import time
from config import strategy_dict
from module_evaluate import start_strategy
from module_data import fetch_indicator, fetch_spot_yf, run_websocket
from module_utilities import read_spot_price , parse_time
from credentials import consumer_key, consumer_secret, mobile, mpin, login_password
from neo_api_client import NeoAPI

index = strategy_dict['index']
indicator = fetch_indicator(index)
print(indicator)
last_close = fetch_spot_yf(index)
current_zone = None
last_processed_price = None
client = None

# client = NeoAPI(consumer_key=consumer_key, consumer_secret=consumer_secret, environment='prod')
# client.login(mobilenumber=mobile, password=login_password)
# client.session_2fa(OTP=mpin)

# websocket_thread = threading.Thread(target=run_websocket, args=(client,))
# websocket_thread.start()
# time.sleep(2)


def main():
    current_zone = None
    last_processed_price = None
    iteration = 0

    while True:
        time.sleep(0.5) 
        spot_price = read_spot_price()
        current_time = datetime.now()

        # Parse market open and close times
        market_open_time = parse_time(strategy_dict["market_open"])
        market_close_time = parse_time(strategy_dict["market_close"])

        # Update market open and close times based on the parsed values
        market_open = current_time.replace(hour=market_open_time.hour, minute=market_open_time.minute, second=0, microsecond=0)
        market_close = current_time.replace(hour=market_close_time.hour, minute=market_close_time.minute, second=0, microsecond=0)


        if current_time > market_close:
            print("market closed")
            break

        if current_time < market_open:
            print("waiting for market to open")
            continue

        current_zone, last_processed_price = start_strategy(client, spot_price, indicator, current_zone, last_processed_price, strategy_dict)
        print (f" Current Zone : {current_zone}")
        
if __name__ == "__main__":
    main()