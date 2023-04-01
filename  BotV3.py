print("""
 /$$    /$$ /$$$$$$$$ /$$        /$$$$$$   /$$$$$$  /$$$$$$ /$$$$$$$$ /$$     /$$       /$$$$$$ /$$   /$$
| $$   | $$| $$_____/| $$       /$$__  $$ /$$__  $$|_  $$_/|__  $$__/|  $$   /$$/      |_  $$_/| $$  / $$
| $$   | $$| $$      | $$      | $$  \ $$| $$  \__/  | $$     | $$    \  $$ /$$/         | $$  |  $$/ $$/
|  $$ / $$/| $$$$$   | $$      | $$  | $$| $$        | $$     | $$     \  $$$$/          | $$   \  $$$$/ 
 \  $$ $$/ | $$__/   | $$      | $$  | $$| $$        | $$     | $$      \  $$/           | $$    >$$  $$ 
  \  $$$/  | $$      | $$      | $$  | $$| $$    $$  | $$     | $$       | $$            | $$   /$$/\  $$
   \  $/   | $$$$$$$$| $$$$$$$$|  $$$$$$/|  $$$$$$/ /$$$$$$   | $$       | $$           /$$$$$$| $$  \ $$
    \_/    |________/|________/ \______/  \______/ |______/   |__/       |__/          |______/|__/  |__/
                                                                                                         
      VELOCITY IX BY STUXN3T
""")
import time
import json
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
import requests
import websockets as websocket
from web3 import Web3
import configparser
from etherscan import Etherscan
from eth_abi import decode_abi
from ta.volatility import AverageTrueRange

# Read configuration from file
config = configparser.ConfigParser()
config.read('config.ini')

INFURA_PROJECT_ID = config.get('infura', 'project_id')
YOUR_WALLET_ADDRESS = config.get('wallet', 'address')
YOUR_PRIVATE_KEY = config.get('wallet', 'private_key')
BENEFICIARY_WALLET = config.get('wallet', 'beneficiary_wallet')
ETHERSCAN_API_KEY = config.get('etherscan', 'api_key')

# Initialize the Etherscan API client
etherscan_client = Etherscan(api_key=ETHERSCAN_API_KEY)

# Initialize the web3 provider
web3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}'))

# Define a cache for token safety checks and liquidity locks
token_safety_cache = {}
liquidity_lock_cache = {}

# Define the ATR period and multiplier
atr_period = 14
atr_multiplier = 2

# Set up your Gmail account information
email_sender = 'your-gmail-username@gmail.com'
email_recipient = 'recipient-email-address@example.com'
email_password = 'your-gmail-password'

async def send_cache_periodically(cache_type):
    while True:
        if cache_type == 'token_safety' and token_safety_cache:
            # Get the contents of the token safety cache as a string
            cache_str = 'Token safety cache:\n'
            cache_str += '\n'.join([f'{k}: {v}' for k, v in token_safety_cache.items()])

            # Create a message object
            msg = MIMEMultipart()
            msg['From'] = email_sender
            msg['To'] = email_recipient
            msg['Subject'] = 'Token safety cache'
            msg.attach(MIMEText(cache_str, 'plain'))

            # Send the message using SMTP
            with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()

                smtp.login(email_sender, email_password)
                smtp.send_message(msg)

            # Clear the token safety cache
            token_safety_cache.clear()

        elif cache_type == 'liquidity_lock' and liquidity_lock_cache:
            # Get the contents of the liquidity lock cache as a string
            cache_str = 'Liquidity lock cache:\n'
            cache_str += '\n'.join([f'{k}: {v}' for k, v in liquidity_lock_cache.items()])

            # Create a message object
            msg = MIMEMultipart()
            msg['From'] = email_sender
            msg['To'] = email_recipient
            msg['Subject'] = 'Liquidity lock cache'
            msg.attach(MIMEText(cache_str, 'plain'))

            # Send the message using SMTP
            with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()

                smtp.login(email_sender, email_password)
                smtp.send_message(msg)

            # Clear the liquidity lock cache
            liquidity_lock_cache.clear()

        # Wait for one hour before sending the next email
        await asyncio.sleep(3600)


async def main():
    # Get the current time in UNIX timestamp format
    current_time = int(time.time())
    # Get the time 24 hours ago in UNIX timestamp format
    time_24_hours_ago = current_time - 24 * 60 * 60

    # Send the cache periodically for token safety
    asyncio.create_task(send_cache_periodically('token_safety'))

    # Send the cache periodically for liquidity lock
    asyncio.create_task(send_cache_periodically('liquidity_lock'))

    while True:
        # Query the Uniswap subgraph API for all new pairs created in the last 24 hours
        async with httpx.AsyncClient() as client:
            new_pairs_response = await client.post(
                "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
                json={
                    "query": """
                        query NewPairs($timestamp: Int!) {
                            pairs(first: 1000, where: {timestamp_gt: $timestamp}) {
                                token0 {
                                    address
                                }
                            }
                        }
                    """,
                    "variables": {"timestamp": time_24_hours_ago}
                }
            )
            new_pairs = new_pairs_response.json()['data']['pairs']

        for pair in new_pairs:
            token_address = pair['token0']['address']
            if await is_token_safe(token_address):
                print(f"Token {token_address} is safe to invest in.")
        
        await asyncio.sleep(60)  # Run the check every 1 minute (60 seconds)

async def is_liquidity_locked(token_address, unicrypt_locker_address, web3_instance):
    if token_address in liquidity_lock_cache:
        return liquidity_lock_cache[token_address]

    # Unicrypt locker contract ABI to get the locked liquidity information
    get_lock_data_abi = "0xc6e047a6"  # Equivalent to web3.sha3("getLockData(address)").hex()[:10]

    # Prepare the contract call to get the lock data
    contract_call = {
        "to": unicrypt_locker_address,
        "data": get_lock_data_abi + token_address[2:].rjust(64, "0")
    }

    # Call the contract and get the lock data
    lock_data_raw = web3_instance.eth.call(contract_call)

    # Decode the lock data response
    decoded_data = decode_abi(
        ["uint256", "uint256", "uint256", "uint256", "uint256", "uint256"],
        bytes.fromhex(lock_data_raw[2:])
    )

    # Extract the relevant data
    total_locked_tokens = decoded_data[2]
    unlock_time = decoded_data[5]

    # Check if there are locked tokens and if they are locked until the specified date
    locked = total_locked_tokens > 0 and unlock_time > int(time.time())
    liquidity_lock_cache[token_address] = locked
    return locked

async def get_buy_and_sell_tax_rates(token_address, web3_instance):
    buy_tax_rate_signature = "0x0a6b58c6"
    sell_tax_rate_signature = "0x1e3d3f85"

    buy_tax_call = {"to": token_address, "data": buy_tax_rate_signature}
    sell_tax_call = {"to": token_address, "data": sell_tax_rate_signature}

    buy_tax_rate_raw = web3_instance.eth.call(buy_tax_call)
    sell_tax_rate_raw = web3_instance.eth.call(sell_tax_call)

    buy_tax_rate = int(buy_tax_rate_raw.hex(), 16)
    sell_tax_rate = int(sell_tax_rate_raw.hex(), 16)

    return buy_tax_rate, sell_tax_rate

async def is_token_safe(token_address):
    if token_address in token_safety_cache:
        return token_safety_cache[token_address]

    # Query the Uniswap subgraph API to get the token information
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            json={
                "query": """
                    query Token($address: String!) {
                        tokens(where: {address: $address}) {
                            symbol
                            verified
                        }
                    }
                """,
                "variables": {"address": token_address}
            }
        )
        token = token_response.json()['data']['tokens'][0]

    # 1. Verify the token
    if not token['verified']:
        token_safety_cache[token_address] = False
        return False

    # 2. Check for a valid liquidity lock
    unicrypt_locker_address = "0x6CCD7C66697e6F2EacA8a6fB7e5BE5f295a02C1d"  # Replace with the correct locker address
    if not await is_liquidity_locked(token_address, unicrypt_locker_address, web3):
        token_safety_cache[token_address] = False
        return False
    
    # 3. Check for acceptable buy and sell tax rates
    max_acceptable_buy_tax = 500  # Example: 5% (tax rates are multiplied by 100)
    max_acceptable_sell_tax = 500  # Example: 5% (tax rates are multiplied by 100)
    buy_tax_rate, sell_tax_rate = await get_buy_and_sell_tax_rates(token_address, web3)
    if buy_tax_rate > max_acceptable_buy_tax or sell_tax_rate > max_acceptable_sell_tax:
        token_safety_cache[token_address] = False
        return False

    # 4. Review token distribution and liquidity
    async with httpx.AsyncClient() as client:
        # Get the top token holders
        holders_response = await client.get(f'https://api.etherscan.io/api?module=account&action=tokenbalance&contractaddress={token_address}&apikey={ETHERSCAN_API_KEY}')
        holders = holders_response.json()

        # Calculate the percentage of tokens held by the top holder
        top_holder_percentage = (int(holders['result']) / int(client.get_token_total_supply(token_address))) * 100

        # Get the token liquidity on the Uniswap exchange
        liquidity_response = await client.post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            json={
                "query": """
                    query Token($address: String!) {
                        token(id: $address) {
                            derivedETH
                        }
                    }
                """,
                "variables": {"address": token_address}
            }
        )
        token_liquidity = float(liquidity_response.json()['data']['token']['derivedETH'])

    # Set thresholds for top holder percentage and liquidity
    top_holder_threshold = 50  # If the top holder(s) hold more than this percentage, consider it a potential Rug pull
    liquidity_threshold = 0.5  # If the liquidity drops below this threshold, consider it a potential Rug pull

    if top_holder_percentage > top_holder_threshold or token_liquidity < liquidity_threshold:
        token_safety_cache[token_address] = False
        return False

    token_safety_cache[token_address] = True
    return True

async def calculate_stop_loss_threshold(trading_pair, current_price, initial_price):
    # Calculate the price range (difference between the current price and the initial price)
    price_range = abs(current_price - initial_price)

    # Calculate the average daily price range
    async with httpx.AsyncClient() as client:
        daily_price_range = float(client.get_24h_price_range(trading_pair)['high']) - float(client.get_24h_price_range(trading_pair)['low'])

    # Calculate the volatility ratio (price range divided by daily price range)
    volatility_ratio = price_range / daily_price_range

    # Adjust the stop loss threshold based on the volatility ratio
    stop_loss_threshold = 0.5 + (volatility_ratio * 0.5)

    # Return the adjusted stop loss threshold
    return stop_loss_threshold

async def get_gas_prices():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://www.etherchain.org/api/gasPriceOracle')
        gas_prices = json.loads(response.text)
    return gas_prices

async def get_optimal_gas_price():
    gas_prices = await get_gas_prices()

    # Choose your preferred gas price strategy
    # Example: Use the 'fast' gas price
    optimal_gas_price = gas_prices['fast']

    return optimal_gas_price

async def trading_strategy(trading_pair):
    try:
        # Set the amount to buy in ETH
        amount_to_buy = 0.005

        # Set profit target and maximum holding time
        profit_target = 10  # Sell when the price doubles (10x)

        # Buy WETH pair tokens
        async with httpx.AsyncClient() as client:
            initial_price = float(client.get_token_price(trading_pair)['price'])
            order = client.place_order(trading_pair,'WETH',trading_pair.split('-')[0],'buy',str(amount_to_buy),str(initial_price))
        
        # Define a stop-loss threshold in percentage (e.g., 50% drop)
        stop_loss_threshold = await calculate_stop_loss_threshold(trading_pair, initial_price, initial_price)

        # Sell WETH pair when the invested amount is 10 times the initial invested amount or if stop-loss condition is met
        while True:
            current_price = float(client.get_token_price(trading_pair)['price'])
            if current_price >= initial_price * 10:
                break
            # Check if the price has dropped below the stop-loss threshold
            elif current_price <= initial_price * stop_loss_threshold:
                print(f"Stop-loss condition met for pair {trading_pair}. Exiting position.")
                break
            # Update the stop-loss threshold based on price action and volatility
            stop_loss_threshold = await calculate_stop_loss_threshold(trading_pair, current_price, initial_price)
            await asyncio.sleep(1)

        # Slippage safety measure
        min_sell_price = current_price * (1 - 0.01)  # Adjust the slippage percentage as needed

        order = client.place_order(
            trading_pair,
            'WETH',
            trading_pair.split('-')[1],
            'sell',
            str(float(client.get_token_balance(trading_pair.split('-')[0]))['balance']),
            str(min_sell_price)
        )

        # Record the trade information
        async with httpx.AsyncClient() as client:
            # Get the token balances before and after the trade
            initial_token_balance = float(client.get_token_balance(trading_pair.split('-')[0]))['balance']
            while True:
                order_status = client.get_order_status(order['id'])
                if order_status['status'] == 'filled':
                    break
                await asyncio.sleep(1)
            new_token_balance = float(client.get_token_balance(trading_pair.split('-')[0]))['balance']

            # Calculate the profit/loss and record the trade information
            token_profit = new_token_balance - initial_token_balance
            eth_profit = token_profit * current_price
            trade_info = {
                "trading_pair": trading_pair,
                "amount": amount_to_buy,
                "initial_price": initial_price,
                "sell_price": current_price,
                "profit": eth_profit
            }
            # Write the trade information to a file
            with open("trades.json", "a") as f:
                json.dump(trade_info, f)
                f.write("\n")

            # Print the trade information to the console
            print(f"Trading Pair: {trading_pair}")
            print(f"Amount: {amount_to_buy}")
            print(f"Initial Price: {initial_price}")
            print(f"Sell Price: {current_price}")
            print(f"Profit: {eth_profit}")
                
        # Set profit target and stop-loss thresholds
        profit_target = 2  # Sell when the price doubles (2x)
        stop_loss = 0.5  # Sell when the price drops to half (0.5x)

        # Wait for the order to be filled
        while True:
            order_status = client.get_order_status(order['id'])
            if order_status['status'] == 'filled':
                break
            await asyncio.sleep(1)

        # Monitor token price and sell if profit target or stop-loss is reached
        holding = True
        while holding:
            async with httpx.AsyncClient() as client:
                current_price = float(client.get_token_price(trading_pair)['price'])

            # Calculate current gain/loss ratio
            current_gain_loss_ratio = current_price / initial_price

            if current_gain_loss_ratio >= profit_target or current_gain_loss_ratio <= stop_loss:
                async with httpx.AsyncClient() as client:
                    # Implement the time delay
                    await asyncio.sleep(1)  # Wait for 1 second before selling

                    # Use a limit order with a slight price decrease for faster execution
                    sell_price = current_price * 0.98  # Slightly decrease the sell price
                    order = client.place_limit_order(trading_pair, trading_pair.split('-')[0], 'WETH', 'sell', str(amount_to_buy), str(sell_price))
                holding = False
            else:
                # Sleep for a short period before checking the price again
                await asyncio.sleep(0.5)  # Check the price every 0.5 seconds

        # Calculate the profit
        new_token_balance = float(client.get_token_balance(trading_pair.split('-')[0]))['balance']
        token_profit = new_token_balance - amount_to_buy
        eth_profit = token_profit * client.get_token_price(trading_pair)['price']

        # Send the profit to another wallet
        if eth_profit > 0:
            nonce = web3.eth.getTransactionCount(YOUR_WALLET_ADDRESS)
            tx = {
                'nonce': nonce,
                'to': BENEFICIARY_WALLET,
                'value': web3.toWei(eth_profit, 'ether'),
                'gas': 21000,
                'gasPrice': web3.toWei(str(await get_optimal_gas_price()), 'gwei')
            }
            signed_tx = web3.eth.account.signTransaction(tx, YOUR_PRIVATE_KEY)
            tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
            print("Transaction sent: ", tx_hash.hex())
        else:
            print("No profit to send.")
    except Exception as e:
        print(f"Error executing trading strategy for pair {trading_pair}: {e}")


# Define the minimum liquidity threshold (in ETH)
min_liquidity_threshold = 1

# Keep track of the pairs that have already been traded
traded_pairs = set()

async def on_message(ws, message):
    async with httpx.AsyncClient() as client:
        # Parse the message
        data = json.loads(message)

        # Filter out messages that are not related to new pairs
        if data.get('event') != 'pair' or data.get('action') != 'added':
            return

        # Get the trading pair information
        pair = data.get('data', {}).get('pair')

        # Get the token address
        token_address = client.get_token_address(pair.split('-')[0])

        # Check if the token is safe
        if not await is_token_safe(token_address):
            print(f"Token {token_address} is not safe, skipping.")
            return

        # Check if the pair meets the minimum liquidity threshold
        if float(client.get_token_balance(pair.split('-')[0])['price']) < min_liquidity_threshold:
            print(f"Pair {pair} has insufficient liquidity, skipping.")
            return

        # Check if the pair has already been traded
        if pair in traded_pairs:
            print(f"Pair {pair} has already been traded, skipping.")
            return

        # Execute the trading strategy on the pair
        try:
            await trading_strategy(pair)
            traded_pairs.add(pair)
        except Exception as e:
            print(f"Error executing trading strategy for pair {pair}: {e}")

async def connect_and_listen():
    # Define the websocket URL
    websocket_url = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2'

    # Create an instance of AsyncClient
    async with httpx.AsyncClient() as client:
        # Establish the websocket connection
        async with websocket.connect(websocket_url) as ws:
            ws.on_message = on_message
            while True:
                try:
                    message = await ws.recv()
                    await on_message(ws, message, client)
                except Exception as e:
                    print(f"Error in websocket connection: {e}")
                    await asyncio.sleep(5)
                    await connect_and_listen()

if __name__ == "__main__":
    asyncio.run(connect_and_listen())