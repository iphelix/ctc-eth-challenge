Capture the Coin - Ethereum Oracle
==================================

CTFd oracle to support dynamic Ethereum challenges.

Deployer
--------

'eth-deployer' requires a running geth instance on a localhost with at least one account which will be used as a faucet.

```
$ python3 eth-deployer.py --generate-accounts 100

$ python3 eth-deployer.py --fill-accounts

$ python3 eth-deployer.py --deploy-contracts 100
```

The above command sequence will create 100 new accounts on the local geth server and deploy one contract for each of the geth accounts. The result is the 'eth.db' file which will be consumed by the oracle.

Oracle
------

'eth-oracle' is a stand-alone server which requires a pre-generated database file with contract addresses to keep track of the players and a ctfd-oracle plugin available here: https://github.com/nbanmp/ctfd-oracle-challenges
