#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="FHDA"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = True

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index=0
prod_exchange_hostname="production"

port=25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

# ~~~~~============== NETWORKING CODE ==============~~~~~
def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)

def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")

def read_from_exchange(exchange):
    return json.loads(exchange.readline())


# ~~~~~============== MAIN LOOP ==============~~~~~
pending_orders = {}
cash = 0
ID = 0
expected_cash = 0
MOST_RECENT = 100
recent_stock_prices = {'MS':[], 'WFC':[], 'GS':[], 'VALBZ':[], 'VALE':[], 'XLF':[]}
recent_stock_quantities = {'MS':[], 'WFC':[], 'GS':[], 'VALBZ':[], 'VALE':[], 'XLF':[]}

position = {"BOND": 100, "VALBZ": 10, "VALE": 10, "GS": 100, "MS": 100, "WFC": 100, "XLF": 100}
curr_pos = {"BOND": 0, "VALBZ": 0, "VALE": 0, "GS": 0, "MS": 0, "WFC": 0, "XLF": 0}

def add_to_recent_list(stockName, quantity, price):
    if type(price) != int:
        return None
    if len(recent_stock_prices[stockName]) == MOST_RECENT:
        recent_stock_prices[stockName].pop(0)
        recent_stock_prices[stockName].append(price)
    else:
        recent_stock_prices[stockName].append(price)
    if len(recent_stock_quantities[stockName]) == MOST_RECENT:
        recent_stock_quantities[stockName].pop(0)
        recent_stock_quantities[stockName].append(price)
    else:
        recent_stock_quantities[stockName].append(price)

mean_stock_prices = {'MS':0, 'WFC':0, 'GS':0, 'VALBZ':0, 'VALE':0, 'XLF':0}

def get_stocks_prices(message):
    if message['type'] == 'trade' and message['symbol'] != 'BOND':
        add_to_recent_list(message['symbol'], message['size'], message['price'])
        mean_stock_prices[message['symbol']] = sum(recent_stock_prices[message['symbol']]) / len(recent_stock_prices[message['symbol']])


def buy_sell_stocks(message, exchange):
    global ID
    margin = 2
    if message['type'] != 'trade':
        return None

    stockName, price, quantity = message['symbol'], message['price'], message['size']
    if stockName == 'BOND' or stockName == 'XTF':
        return None
    # we buy stock if trade price is lower than fair price (aka mean)
    if price < int(mean_stock_prices[stockName]) + margin:
        if curr_pos[stockName] + quantity > position[stockName]:  # we cant buy more than limit
            return None
        ID += 1
        order = {"type": "add", "order_id": ID, "symbol": stockName, "dir": "BUY", "price": price, "size": quantity}
        pending_orders[ID] = (order, quantity)
        write_to_exchange(exchange, order)
    elif price + margin > int(mean_stock_prices[stockName]):
        if curr_pos[stockName] - quantity < -position[stockName]:  # we cant buy more than limit
            return None
        ID += 1
        order = {"type": "add", "order_id": ID, "symbol": stockName, "dir": "SELL", "price": price, "size": quantity}
        pending_orders[ID] = (order, quantity)
        write_to_exchange(exchange, order)

def buy_sell_bonds(message, exchange):
    """
    Actually writes the order, basic stock scalping strategy
    """
    if message['type'] == 'trade' and message['symbol'] == 'BOND':
        global ID
        ID += 1
        size = 1
        if message['price'] < 1000  and (curr_pos["BOND"] + quantity < position["BOND"]):
            if curr_pos['BOND'] + size > position['BOND']:  # we cant buy more than limit
                return None
            order = {"type": "add", "order_id": ID, "symbol": "BOND", "dir": "BUY", "price": message['price'], "size": size}
        elif message['price'] >= 1000 and (curr_pos["BOND"] - quantity > -1 * position["BOND"]):
            if curr_pos['BOND'] - size < -position['BOND']:  # we cant buy more than limit
                return None
            order = {"type": "add", "order_id": ID, "symbol": "BOND", "dir": "SELL", "price": message['price'], "size": size}
        pending_orders[ID] = (order, size)
        write_to_exchange(exchange, order)

def buy_convert_sell_etf(message, exchange):
    global ID
    global expected_cash
    global position
    global curr_pos



def buy_convert_sell_adr(message, exchange):
    """
    Actually writes the order
    """
    global ID
    global expected_cash
    global position
    global curr_pos
    # and (curr_pos["VALBZ"] + quantity < position["VALBZ"]) and (curr_pos["VALE"] - quantity > position["VALE"])
    if message['type'] == 'trade' and message['symbol'] == 'VALBZ':
        add_to_recent_list('VALBZ', recent_stock_quantities['VALBZ'], recent_stock_prices['VALBZ'])
    elif message['type'] == 'trade' and message['symbol'] == 'VALE':
        add_to_recent_list('VALE', recent_stock_quantities['VALE'], recent_stock_prices['VALE'])
 
    
    if recent_stock_prices['VALBZ'] and recent_stock_prices['VALE']:
        quantity = min(recent_stock_quantities['VALBZ'][-1], recent_stock_quantities['VALE'][-1])
        if (recent_stock_prices['VALBZ'][-1] * quantity + 10 < recent_stock_prices['VALE'][-1] * quantity) and (curr_pos["VALBZ"] + quantity < position["VALBZ"]) and (curr_pos["VALE"] - quantity > -1 * position["VALE"]):
            ID += 1
            expected_cash -= recent_stock_prices['VALBZ'][-1] * quantity
            print("tryna buy valbz", recent_stock_prices['VALBZ'][-1])
            order = {"type": "add", "order_id": ID, "symbol": "VALBZ", "dir": "BUY", "price": recent_stock_prices['VALBZ'][-1], "size": quantity}
            pending_orders[ID] = (order, quantity)
            write_to_exchange(exchange, order)
            print("tryna convert VALBZ tp VAL")
            ID+=1
            order = {"type": "convert", "order_id": ID, "symbol": "VALBZ", "dir": "BUY", "size": quantity}
            pending_orders[ID] = (order, quantity)
            write_to_exchange(exchange, order)
            print("tryna sell vale", recent_stock_prices['VALE'][-1])
            ID += 1
            expected_cash += recent_stock_prices['VALE'][-1] * quantity
            order = {"type": "add", "order_id": ID, "symbol": "VALE", "dir": "SELL", "price": recent_stock_prices['VALE'][-1], "size": quantity}
            pending_orders[ID] = (order, quantity)
            write_to_exchange(exchange, order)
        elif recent_stock_prices['VALE'][-1] * quantity + 10 < recent_stock_prices['VALBZ'][-1] * quantity and (curr_pos["VALE"] + quantity < position["VALE"]) and (curr_pos["VALBZ"] - quantity > -1 * position["VALBZ"]):
            ID += 1
            expected_cash -= recent_stock_prices['VALE'][-1] * quantity
            print("tryna buy vale", recent_stock_prices['VALE'][-1])
            order = {"type": "add", "order_id": ID, "symbol": "VALE", "dir": "BUY", "price": recent_stock_prices['VALE'][-1], "size": quantity}
            pending_orders[ID] = (order, quantity)
            write_to_exchange(exchange, order)
            print("tryna convert VALE tp VALBZ")
            ID+=1
            order = {"type": "convert", "order_id": ID, "symbol": "VALE", "dir": "BUY", "size": quantity}
            pending_orders[ID] = (order, quantity)
            write_to_exchange(exchange, order)
            print("tryna sell vale", recent_stock_prices['VALBZ'][-1])
            ID += 1
            expected_cash += recent_stock_prices['VALBZ'][-1] * quantity
            order = {"type": "add", "order_id": ID, "symbol": "VALBZ", "dir": "SELL", "price": recent_stock_prices['VALBZ'][-1], "size": quantity}
            pending_orders[ID] = (order, quantity)
            write_to_exchange(exchange, order)



#in the works
def sell_adr(message, exchange):
    """
    Actually writes the order
    """
    global ID
    global expected_cash
 
    quantity_e = min(curr_pos["VALBZ"], recent_stock_quantities['VALE'][-1])
    quantity_bz =  min(recent_stock_quantities['VALBZ'][-1], curr_pos("VALE"))
    if recent_stock_prices['VALBZ'][-1] * quantity_e + 10 < curr_pos("VALE") * quantity_e: 
        ID += 1
        
        print("tryna convert VALBZ tp VAL")
        ID+=1
        order = {"type": "convert", "order_id": ID, "symbol": "VALBZ", "dir": "BUY", "size": quantity}
        pending_orders[ID] = (order, quantity)
        write_to_exchange(exchange, order)
        print("tryna sell vale", recent_stock_prices['VALE'][-1])
        ID += 1
        expected_cash += recent_stock_prices['VALE'][-1] * quantity
        order = {"type": "add", "order_id": ID, "symbol": "VALE", "dir": "SELL", "price": recent_stock_prices['VALE'][-1], "size": quantity}
        pending_orders[ID] = (order, quantity)
        write_to_exchange(exchange, order)



def main():
    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)
    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)
    global cash
    while True:
        message = read_from_exchange(exchange)
        get_stocks_prices(message)
        # buys/sells bonds
        if cash >= -20000:
            buy_sell_bonds(message, exchange)
        
        if expected_cash >= -10000:
            buy_sell_stocks(message, exchange)
        if expected_cash >= 0:
            buy_convert_sell_adr(message, exchange)
        #if len(pending_orders) < 6 and recent_bond_prices:
        #    take_action()
        #    print("we have placed", len(pending_orders), "pending orders so far and we have ", cash, " USD")

#	elif len(pending_orders) == 6:
#	    print("OUR PENDING ORDERS ARE:")
      #      for order in pending_orders.values():
      #          print(order[0])
        
        if message['type'] == 'reject':
            print(message)

        #if message['type'] == 'ack':
            #print("Placed order of ", str(pending_orders[message['order_id']]))

        if message['type'] == 'fill':
            #print("FILLED ORDER", message['order_id'], "TO", message['size'], "SHARES...")
            curr_order = pending_orders[message['order_id']]
            pending_orders[message['order_id']] = (curr_order[0], curr_order[1] - message['size'])
            if message['dir'] == 'BUY':
                cash -= message['size'] * message['price']
                curr_pos[message['symbol']] += message['size']
            elif message['dir'] == 'SELL':
                cash += message['size'] * message['price']
                curr_pos[message['symbol']] -= message['size']
            print("we have ", cash, " cash now")
        
        if message['type'] == 'out':
            del pending_orders[message['order_id']]
        
        if message["type"] == "close":
            print("The round has ended")
            break

if __name__ == "__main__":
    main()