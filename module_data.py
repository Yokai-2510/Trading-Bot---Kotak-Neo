import yfinance as yf
import time 
import pandas as pd
import requests
import io
from config import strategy_dict
import pandas as pd
import time
from datetime import datetime

global index 
index = strategy_dict['index']

spot_price = {'value': None, 'timestamp': None}
last_valid_spot_price = {'value': None, 'timestamp': None}
option_chain_df = None
last_valid_ltps = {}
client = None

def fetch_indicator(index):
    ticker_symbol = "^NSEI" if index == "NIFTY" else "^NSEBANK"
    data = yf.download(ticker_symbol, period='1mo', interval='1d')
    today = datetime.now().date()
    data = data[data.index.date != today]
    last_5_days = data.tail(5)

    return {
        'high': last_5_days['High'].max(),
        'low': last_5_days['Low'].min(),
        'max_close': last_5_days['Close'].max(),
        'min_close': last_5_days['Close'].min()
    }

def fetch_spot_yf(index):
    ticker = yf.Ticker("^NSEI" if index == "NIFTY" else "^NSEBANK")
    data = ticker.history(period="1d")
    data = data.iloc[-1]['Close']
    print(f"data yf last close for {index}", data)
    return data

def fetch_ikeys(client, index):
    global spot_price
    scrip_master_data = client.scrip_master()
    nse_fo_url = next((url for url in scrip_master_data['filesPaths'] if 'nse_fo' in url), None)
    if not nse_fo_url:
        raise ValueError("NSE F&O data URL not found in scrip master data")
    
    response = requests.get(nse_fo_url)
    if response.status_code != 200:
        raise ValueError(f"Failed to download CSV. Status code: {response.status_code}")
    
    df = pd.read_csv(io.StringIO(response.text), low_memory=False)
    column_mapping = {
        'pTrdSymbol': 'instrument_key',
        'pSymbol': 'symbol',
        'pOptionType': 'option_type',
        'dStrikePrice;': 'strike_price',
        'lExpiryDate ': 'expiry_date',
        'pInstType': 'instrument_type',
        'pSymbolName': 'symbol_name'
    }
    df.rename(columns=column_mapping, inplace=True)
    
    df = df[(df['instrument_type'] == 'OPTIDX') & (df['symbol_name'] == index)]
    df['expiry_date'] = pd.to_datetime(df['expiry_date'], unit='s') + pd.DateOffset(years=10)
    td = pd.Timestamp(datetime.now().date())
    cur_exp = min(df['expiry_date'], key=lambda x: (x - td).days if (x - td).days >= 0 else float('inf'))
    df = df[df['expiry_date'] == cur_exp]
    df['strike_price'] = (df['strike_price'] / 100).astype(int)

    latest_spot_price = fetch_spot_yf(index) or 24000
    rounded_spot_price = round(latest_spot_price / 100) * 100
    strike_price_cap = 1200 if index == 'NIFTY' else 2300
    min_strike = rounded_spot_price - strike_price_cap
    max_strike = rounded_spot_price + strike_price_cap
    df = df[(df['strike_price'] >= min_strike) & (df['strike_price'] <= max_strike)]

    df = df[['instrument_key', 'symbol', 'option_type', 'strike_price', 'expiry_date']]
    df = df.reset_index(drop=True)
    print(f"Number of options in chain after filtering: {len(df)}")
    print(df)
    return df

def write_csv_with_retry(df, filename, max_retries=15, delay=0.1):
    for attempt in range(max_retries):
        try:
            df.to_csv(filename, index=False)
            return  # Success, exit the function
        except (OSError, IOError, PermissionError) as e:
            if attempt < max_retries - 1:  # don't sleep on the last attempt
                print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Failed to write to {filename} after {max_retries} attempts: {str(e)}")

def update_spot_price(instrument_token, ltp):   
    global spot_price, last_valid_spot_price
    if ltp is not None:
        spot_price['value'] = ltp
        last_valid_spot_price['value'] = ltp
    else:
        spot_price['value'] = last_valid_spot_price['value']
    spot_price['timestamp'] = datetime.now().isoformat()
    last_valid_spot_price['timestamp'] = spot_price['timestamp']
    write_csv_with_retry(pd.DataFrame([spot_price]), 'spot_price.csv')

def update_option_chain(instrument_token, ltp):
    global option_chain_df, last_valid_ltps
    if ltp is not None:
        option_chain_df.loc[option_chain_df['symbol'] == instrument_token, 'ltp'] = ltp
        last_valid_ltps[instrument_token] = ltp
    else:
        option_chain_df.loc[option_chain_df['symbol'] == instrument_token, 'ltp'] = last_valid_ltps.get(instrument_token)
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    option_chain_df['timestamp'] = current_time
    option_chain_df['strike_price'] = option_chain_df['strike_price'].astype(int)
    option_chain_df['ltp'] = option_chain_df['ltp'].astype(float)
    option_chain_df['expiry_date'] = pd.to_datetime(option_chain_df['expiry_date'], errors='coerce')
    option_chain_df['expiry_date'] = option_chain_df['expiry_date'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(x) else x)
    write_csv_with_retry(option_chain_df, 'option_chain.csv')

def process_websocket_message(message):
    global option_chain_df
    try:
        data = message.get('data', [])
        for item in data:
            instrument_token = item.get('tk')
            ltp = item.get('ltp')
            try:
                ltp = float(ltp)
            except (ValueError, TypeError):
                ltp = None

            if instrument_token == ('26000' if index == 'NIFTY' else '26009'):  # NIFTY or BANKNIFTY spot price
                update_spot_price(instrument_token, ltp)
            elif instrument_token in option_chain_df['symbol'].values:
                update_option_chain(instrument_token, ltp)

    except Exception as e:
        print(f"Error processing message: {e}")

def setup_websocket(client):
    def on_message(message):
        process_websocket_message(message)

    def on_error(error_message):
        print("Error:", error_message)

    def on_open(message):
        print('[OnOpen]:', message)

    def on_close(message):
        print('[OnClose]:', message)

    client.on_message = on_message
    client.on_error = on_error
    client.on_open = on_open
    client.on_close = on_close

def connect_websocket(client):
    global option_chain_df
    
    instrument_tokens = [
        {"instrument_token": token, "exchange_segment": "nse_fo"}
        for token in option_chain_df['symbol'].tolist()
    ]
    instrument_tokens.append({
        "instrument_token": "26000" if index == "NIFTY" else "26009", 
        "exchange_segment": "nse_cm"
    })

    try:
        client.subscribe(instrument_tokens=instrument_tokens)
        return True
    except Exception as e:
        print(f"Exception while connecting to socket: {e}")
        return False

def websocket_thread(client, stop_event):
    connect_websocket(client)
    while not stop_event.is_set():
        time.sleep(1)  # Keep the thread alive but allow for interruption

def run_websocket(client):
    global option_chain_df, last_valid_ltps

    # Fetch indicator data
    indicator = fetch_indicator(index)
    print("Indicator data:", indicator)

    # Initialize option_chain_df
    option_chain_df = fetch_ikeys(client, index)
    option_chain_df['ltp'] = None

    # Initialize last_valid_ltps
    for token in option_chain_df['symbol']:
        last_valid_ltps[token] = None

    # Setup websocket
    setup_websocket(client)

    # Connect websocket
    connect_websocket(client)

    # Main loop
    while True:
        time.sleep(1)

if __name__ == "__main__":

    run_websocket(client)
    fetch_spot_yf(index)
    fetch_indicator(index)