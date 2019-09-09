#!/usr/bin/env python3
from flask import Flask, request, abort

import sys, os
import sqlalchemy as db
from sqlalchemy import and_
from web3.auto import w3

import logging
import queue
import argparse

app = Flask(__name__)
logger = logging.getLogger(__name__)

DB_FILE = 'eth.db'


@app.route("/create", methods=["POST"])
def create():
    """
    Create challenge given a player_id. If force_new is true,
    a new instance must be created and the old instance may be deleted.

    Return a description containing any
    information needed to access the challenge

    > return challenge_details
    """

    engine = db.create_engine("sqlite:///" + DB_FILE)
    connection = engine.connect()
    metadata = db.MetaData()
    contracts = db.Table('contracts', metadata, autoload=True, autoload_with=engine)


    data = request.form or request.get_json()
    player_id = str(data["player_id"])

    # Check if there is an existing assigned address
    query = db.select([contracts.columns.address]).where(contracts.columns.player == player_id)
    contract_addr = connection.execute(query).scalar()



    if not contract_addr:

        # Fetch an unused contract and unsolved address
        query = db.select([contracts.columns.address]).where(
            and_(contracts.columns.solved == 0, contracts.columns.player == None))
        contract_addr = connection.execute(query).scalar()

        if not contract_addr:
            logger.error("No contract addresses are available.")
            return "No contract addresses are available. Please contact admin."

        # Assign the contract address to the player
        query = db.update(contracts).values(player=player_id).where(contracts.columns.address == contract_addr)
        connection.execute(query)

        logger.info("New challenge for player %s: %s", player_id, contract_addr)
    else:
        logger.info("Existing challenge for player %s: %s", player_id, contract_addr)


    return (
        "Cause the contract at "
        '<a href="https://ropsten.etherscan.io/address/{0}">{0}</a> '
        "to selfdestruct itself."
    ).format(contract_addr)


@app.route("/attempt", methods=["POST"])
def check_solve():
    """
    Check a solve, given a player_id

    Return with a 200 code on successful solve or abort on
    a failed solve attempt
    """

    engine = db.create_engine("sqlite:///" + DB_FILE)
    connection = engine.connect()
    metadata = db.MetaData()
    contracts = db.Table('contracts', metadata, autoload=True, autoload_with=engine)

    data = request.form or request.get_json()

    player_id = str(data["player_id"])

    # Check if there is an existing assigned address
    query = db.select([contracts.columns.address]).where(contracts.columns.player == player_id)
    contract_addr = connection.execute(query).scalar()

    if not contract_addr:
        abort(401)

    logger.info(
        "Checking for solving of challenge at address %s for team %s", contract_addr, player_id
    )

    if len(w3.eth.getCode(contract_addr)) > 2:
        abort(403)

    query = db.update(contracts).values(solved=1).where(contracts.columns.address == contract_addr)
    connection.execute(query)

    return "Success"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()

    parser.add_argument("--dbfile", action='store', help="specify database file", default=DB_FILE)
    parser.add_argument("--port", action='store', type=int, help="set listener port", default=4002)

    args = parser.parse_args()

    # Change database
    if args.dbfile and args.dbfile != DB_FILE:
        DB_FILE = args.dbfile
        logger.info("Using db file: %s" % DB_FILE)

    # Start database connection
    if not os.path.isfile(DB_FILE):
        logger.error("Database file %s does not exist!" % DB_FILE)
        sys.exit(1)

    app.run(debug=True, threaded=True, host="127.0.0.1", port=args.port)
