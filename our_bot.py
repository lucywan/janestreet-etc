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
recent_bond_prices = []
mean_bond_price = 0

def get_bond_price(message):
    if message['type'] == 'trade' and message['symbol'] == 'BOND':
        print(message)
        if len(recent_bond_prices) == 100:
            recent_bond_prices.pop(0)
            recent_bond_prices.append(message['price'])
        else:
            recent_bond_prices.append(message['price'])
        print(message)
        global mean_bond_price
        mean_bond_price = sum(recent_bond_prices) / len(recent_bond_prices)

ID = 0
def basic_buy_bond_order():
    global ID
    ID += 1
    price = int(mean_bond_price) - 1
    size = 2  # TODO: change to something better
    order = {"type": "add", "order_id": ID, "symbol": "BOND", "dir": "BUY", "price": price, "size": size}
    pending_orders[ID] = (order, size)
    return order

def basic_sell_bond_order():
    global ID
    ID += 1
    price = int(mean_bond_price) + 1
    size = 2  # TODO: change to something better
    order = {"type": "add", "order_id": ID, "symbol": "BOND", "dir": "SELL", "price": price, "size": size}
    pending_orders[ID] = (order, size)
    return order

expected_cash = 0

def buy_sell_bonds(message, exchange):
    """
    Actually writes the order
    """
    if message['type'] == 'trade' and message['symbol'] == 'BOND':
        global ID
	global expected_cash
        ID += 1
        size = message['size']
        if message['price'] < 1000:
            expected_cash -= message['price']
           # print("tryna buy", message['price'])
            order = {"type": "add", "order_id": ID, "symbol": "BOND", "dir": "BUY", "price": message['price'], "size": size}
        elif message['price'] >= 1000:
	   # print('tryna sell', message['price'])
            expected_cash += message['price']
            order = {"type": "add", "order_id": ID, "symbol": "BOND", "dir": "SELL", "price": message['price'], "size": size}
        pending_orders[ID] = (order, size)
        write_to_exchange(exchange, order)


def take_action():
    write_to_exchange(connect(), basic_buy_bond_order())
    write_to_exchange(connect(), basic_sell_bond_order())

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
        
        # buys/sells bonds
        if expected_cash > -20000:
            buy_sell_bonds(message, exchange)

        # get_stock_price(message)

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
            elif message['dir'] == 'SELL':
                cash += message['size'] * message['price']
            print("we have ", cash, " cash now")
        
        if message['type'] == 'out':
            del pending_orders[message['order_id']]
        
        if message["type"] == "close":
            print("The round has ended")
            break

if __name__ == "__main__":
    main()