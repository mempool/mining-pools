## `pools_addresses.csv`: a classification of all addresses related to known mining pools

The scripts in this directory are used to generate the file `pools_addresses.csv` that contains all the addresses related to known mining pools referenced in `pools-v2.json`.

`pools_addresses.csv` contains every pair `address` - `pool_id` where `address` is a bitcoin address related to one or more mining pools and `pool_id` is the id of the pool. Note that since an address can be related to multiple known mining pools, the table can contain multiple rows for the same address.

Each row looks like this:

| address  | pool_id |  pool_value  |
| -------- | ------- | ------------ |
| 39PV... | 94 | 391072421935 |
| 3KfRw... |    6    | 147319130014 |

Where:
- `address` is an address that received a coinbase transaction from a known mining pool
- `pool_id` is the id of the related known pool
- `pool_value` is the total number of sats mined by the address with `pool_id`

This table is used to access mining pools associated with addresses in a way that scales well when the number of known addresses grows.

The data generation process is explained below. It could eliminate the need for manual address additions to `pools-v2.json` and includes all known addresses (no omission).

## How to generate `pools_addresses.csv`:

### Prerequisites:
- bitcoin node with following `bitcoin.conf`:
```
rpcuser=mempool
rpcpassword=replace_me
rpcport=8332 # Listening on localhost
```

- mariadb or similar database server with a user `mempool`:
```
MariaDB [(none)]> drop database coinbase;
Query OK, 0 rows affected (0.00 sec)

MariaDB [(none)]> create database coinbase;
Query OK, 1 row affected (0.00 sec)

MariaDB [(none)]> grant all privileges on coinbase.* to 'mempool'@'%' identified by 'mempool';
Query OK, 0 rows affected (0.00 sec)
```

### Steps

1. Clone the repository and go to the `scripts` directory

2. Replace the rpc credentials in `coinbase_data.py` with your own

3. Run `python3 coinbase_data.py`

This should take few hours to compute. It populates the table `coinbase_data` from block 1 to current height with the following columns:

| Height  | Coinbase Signature | Output Addresses     | Output Values | Pool Id |
| ------- | ------------------ | -------------------- | ------------- | ------- |
| 123456  | 04ffff001d0280...  | ["1A1z...","38Xn..."] | [1234, 5678]  | 100     |


Where:
- `Height` is the block height
- `Coinbase Signature` is the signature of the coinbase transaction
- `Output Addresses` is the list of all the output addresses of the coinbase transaction
- `Output Values` is the list of all the corresponding output values (in sats) of the coinbase transaction
- `Pool Id` is the id of the pool that mined the block according to `pools-v2.json` (0 if unknown)


The table `coinbase_data` contains all the coinbase transactions data up to current block height (size is >300MB)

4. Run `python3 mining_addresses.py`

This uses the `coinbase_data` table to populate the tables `mining_addresses` and `pools_addresses`. The table `mining_addresses` simply lists all the addresses that ever received one or more coinbase transaction(s) and acts as foreign key for `pools_addresses`.

The table we are interested in is `pools_addresses` that only contains addresses related to known mining pools. Its structure is described [here](#pool_addressescsv-a-classification-of-all-addresses-related-to-known-mining-pools).

5. Export `pools_addresses` to csv

```
rm /path/to/pools_addresses.csv
mariadb> SELECT * FROM pools_addresses INTO OUTFILE '/path/to/pools_addresses.csv' FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';
```

----------------------------------------------
Last update of `pools_addresses.csv`:

```
MariaDB [coinbase]> SELECT MAX(Last_Block_Update) FROM mining_addresses;
+------------------------+
| MAX(Last_Block_Update) |
+------------------------+
|                 820165 |
+------------------------+
```
