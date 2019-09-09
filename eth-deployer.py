#!/usr/bin/env python3
#
# Run geth with the following parameters:
# $ geth --testnet --syncmode "light" --rpc --rpcapi=eth,web3,net,personal
#
# Set command-line parameter for web3.auto to work:
#
# $ export WEB3_PROVIDER_URI=http://10.0.0.66:8545

import os, sys
import logging
import queue
import random
import threading
import json

import argparse

import sqlite3
from web3.auto import w3

CONTRACT_BYTECODE = "6080604052600080546001600160a01b03191633179055610163806100256000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c806370d6fc33146100465780638da5cb5b14610050578063f21dac3214610074575b600080fd5b61004e61009a565b005b6100586100b4565b604080516001600160a01b039092168252519081900360200190f35b61004e6004803603602081101561008a57600080fd5b50356001600160a01b03166100c3565b6000546001600160a01b031633146100b157600080fd5b33ff5b6000546001600160a01b031681565b806001600160a01b0316604051808069060f0626466686a6c6e760b31b815250600a019050600060405180830381855af49150503d8060008114610123576040519150601f19603f3d011682016040523d82523d6000602084013e610128565b606091505b5050505056fea265627a7a7230582089704978a1098aaa2b0714868bb161d8a101c1a1b80d82bc3f59bf6f64f4c7a764736f6c634300050a0032"
CONTRACT_ABI = json.loads("""[{"constant":false,"inputs":[],"name":"destroyme","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_address","type":"address"}],"name":"hackme","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"inputs":[],"payable":true,"stateMutability":"payable","type":"constructor"}]""")

DB_FILE = 'eth.db'

ETH_PASSWORD = 'PASSWORD'


logger = logging.getLogger(__name__)

def create_contract(from_addr):

    if not w3.personal.unlockAccount(from_addr, ETH_PASSWORD):
        raise RuntimeError("Unable to unlock your account. Make sure it has no passphrase.")

    logger.info("Creating new contract (last block: %i, from address: %s)", w3.eth.blockNumber, from_addr)

    Contract = w3.eth.contract(abi=CONTRACT_ABI, bytecode=CONTRACT_BYTECODE)
    tx_hash = Contract.constructor().transact({'from': from_addr})

    # Wait for the transaction to be mined.
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    addr = tx_receipt.contractAddress

    logger.info("Created new contract at addr %s", addr)
    return addr

def store_address(conn, address_data):

    c = conn.cursor()
    try:
        c.execute('''INSERT INTO contracts (address, owner) VALUES (?, ?)''', address_data)
    except sqlite3.IntegrityError as e:
        print('sqlite error: ', e.args[0]) # column name is not unique
    conn.commit()

def create_database(conn):
    logger.info("Creating a new database.")
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS contracts (id INTEGER PRIMARY KEY, address TEXT NOT NULL UNIQUE, owner TEXT, balance INTEGER default 0, player TEXT, solved INTEGER NOT NULL default 0)')
    conn.commit()

def deploy_contracts(n):
    logger.info("Deploying contracts...")

    # Open the database and create it if necessary
    if os.path.isfile(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
    else:
        conn = sqlite3.connect(DB_FILE)
        create_database(conn)

    # Get available ethereum accounts without the first faucet account
    eth_accounts = w3.personal.listAccounts[1:]
    eth_accounts_num = len(eth_accounts)


    for i in range(n):

        eth_acc = eth_accounts[i % eth_accounts_num]
        logger.info("Deploying %d contract on %s (%d) account..." % (i, eth_acc, i % eth_accounts_num))

        try:
            contract_addr = create_contract(eth_acc)
            address_data = (contract_addr, eth_acc)
            store_address(conn, address_data)

        except ValueError as err:
            logger.error("Error creating a contract:", err)

def get_eth(faucet_acc, generator_acc, amount):

    if not w3.personal.unlockAccount(faucet_acc, ETH_PASSWORD):
        raise RuntimeError("Unable to unlock your account.")

    tx_hash = w3.eth.sendTransaction(
        {'to': generator_acc, 'from': faucet_acc, 'value': amount})

    #tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

# The first account is a faucet we will use it to populate the rest of accounts
def fill_accounts():

    eth_accounts = w3.personal.listAccounts

    faucet_acc = eth_accounts[0]

    for i, acc in enumerate(eth_accounts[1:]):

        # Check balance and request funds from a faucet if below threshold
        balance = w3.eth.getBalance(acc)

        if balance < w3.toWei(0.005, 'ether'):
            logger.info("Account %s is below the threshold. Filling..." % acc)
            get_eth(faucet_acc, acc, w3.toWei(0.005, 'ether') - balance)

def generate_accounts(n):
    logger.info("Generating %d accounts" % n)

    for i in range(n):
        w3.personal.newAccount(ETH_PASSWORD)

    list_accounts()


def list_accounts():
    logger.info("Account summary:")
    for acc in w3.personal.listAccounts:
        logger.info("\t%s - %d" % (acc, w3.eth.getBalance(acc)))


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-accounts", type=int, help="generate specified number of accounts")
    parser.add_argument("--fill-accounts", help="request some eth for existing accounts", action='store_true')
    parser.add_argument("--list-accounts", help="list accounts and their balances", action='store_true')
    parser.add_argument("--deploy-contracts", type=int, help="deploy specified number of contracts")
    parser.add_argument("--dbfile", action='store', help="specify database file", default=DB_FILE)
    parser.add_argument("--ethpass", action='store', help='specify ethereum account password', default=ETH_PASSWORD)

    args = parser.parse_args()

    if args.dbfile and args.dbfile != DB_FILE:
        DB_FILE = args.dbfile
        logger.info("Using db file: %s" % DB_FILE)

    if args.ethpass and args.ethpass != ETH_PASSWORD:
        ETH_PASSWORD = args.ethpass
        logger.info("Using eth password: %s" % ETH_PASSWORD)

    if args.list_accounts:
        list_accounts()

    if args.generate_accounts:
        generate_accounts(args.generate_accounts)

    elif args.fill_accounts:
        fill_accounts()

    if args.deploy_contracts:
        deploy_contracts(args.deploy_contracts)

    #contract_creator_thread = threading.Thread(target=contract_creator)
    #contract_creator_thread.start()
