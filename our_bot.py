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
test_exchange_index=1
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
    global recent_bond_prices
    if message['type'] == 'trade' and message['symbol'] == 'BOND':
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
    while True:
        message = read_from_exchange(exchange)
        
        get_bond_price(message)

        if len(pending_orders) < 6:
            take_action()
            print("we have placed", len(pending_orders), "pending orders so far and we have ", cash, " USD")
        
        if message['type'] == 'reject':
            print(message)

        if message['type'] == 'ack':
            print("Placed order of ", str(pending_orders[message['order_id']]))

        if message['type'] == 'fill':
            print("FILLED ORDER", message['order_id'], "TO", message['size'], "SHARES...")
            curr_order = pending_orders[message['order_id']]
            pending_orders[message['order_id']] = (curr_order[0], curr_order[1] - message['size'])
            global cash
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