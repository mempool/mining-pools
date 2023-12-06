from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import pymysql.cursors
import json

rpc_user = "mempool"
rpc_password = "replace_me"
rpc_port = 8332

db_host = "localhost"
db_user = "mempool"
db_password = "mempool"
db_name = "coinbase"

default_starting_block = 1

with open('../pools-v2.json') as f:
    pools_data = json.load(f)

def get_rpc_connection():
    try:
        rpc_connection = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@127.0.0.1:{rpc_port}/")
        return rpc_connection
    except JSONRPCException as e:
        print(f"Error connecting to Bitcoin Core RPC: {e}")
        return None

def create_database_connection():
    try:
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"Error connecting to MariaDB: {e}")
        return None

def hex_to_ascii(hex_str):
    try:
        return bytes.fromhex(hex_str).decode('ascii', errors='replace')
    except UnicodeDecodeError as e:
        print(f"Error decoding hex string: {e}")
        return None

rpc_connection = get_rpc_connection()
if rpc_connection is None:
    print("Can not connect to RPC: exiting")
    sys.exit()

db_connection = create_database_connection()
if db_connection is None:
    print("Can not connect to database: exiting")
    sys.exit()

try:
    block_height = rpc_connection.getblockcount()

    with db_connection.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coinbase_data (
            Height INT PRIMARY KEY,
            Coinbase_Signature TEXT,
            Addresses TEXT,
            Transaction_Values TEXT,
            Pool_Id INT
        )
        """)
        db_connection.commit()
        cursor.execute("SELECT MAX(Height) FROM coinbase_data")
        result = cursor.fetchone()
        if result['MAX(Height)'] is not None:
            default_starting_block = result['MAX(Height)'] + 1

        for height in range(default_starting_block, block_height + 1):
            block_hash = rpc_connection.getblockhash(height)
            block = rpc_connection.getblock(block_hash)
            coinbase_txid = block['tx'][0]
            coinbase_transaction = rpc_connection.getrawtransaction(coinbase_txid, 1)

            coinbase_signature = (coinbase_transaction['vin'][0]['coinbase'])
            coinbase_script_ascii = hex_to_ascii(coinbase_signature)
            pool_id = 0
            for pool in pools_data:
                for tag in pool['tags']:
                    if tag in coinbase_script_ascii:
                        pool_id = pool['id']
                        break
                if pool_id:
                    break

            addresses = []
            values = []
            for output in coinbase_transaction['vout']:
                if output['value'] > 0:
                    if output['scriptPubKey']['type'] == 'pubkey':
                        addresses.append(output['scriptPubKey']['desc'].split('(')[1].split(')')[0])
                        values.append(int(output['value'] * 100000000))
                    elif 'address' in output['scriptPubKey']:
                        addresses.append(output['scriptPubKey']['address'])
                        values.append(int(output['value'] * 100000000))

            insert_query = """
            INSERT INTO coinbase_data (Height, Coinbase_Signature, Addresses, Transaction_Values, Pool_Id)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (height, coinbase_signature, str(addresses), str(values), pool_id))

            if height % 1000 == 0 or height == block_height or height == default_starting_block:
                print(f"Block {height} / {block_height}")
                print(f"Coinbase signature: {coinbase_signature}")
                print(f"Addresses: {addresses}")
                print(f"Output Values: {values}")
                print(f"Pool ID: {pool_id}")
                print("-" * 50)
                db_connection.commit()
        db_connection.commit()
            
except JSONRPCException as e:
    print(f"Error while retrieving block information: {e}")
finally:
    db_connection.close()
