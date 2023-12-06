import mysql.connector

db_params = {
    'host': 'localhost',
    'user': 'mempool',
    'password': 'mempool',
    'database': 'coinbase'
}

connection = mysql.connector.connect(**db_params)
cursor = connection.cursor()

# Create the table that will contain all addresses that ever mined a coin
create_addresses_table_query = """
CREATE TABLE IF NOT EXISTS mining_addresses (
    Address VARCHAR(140) PRIMARY KEY,
    Last_Block_Update INT(11)
)
"""
cursor.execute(create_addresses_table_query)
connection.commit()

# Create the table that will contain all addresses related to known mining pools
create_pool_table_query = """
CREATE TABLE IF NOT EXISTS pool_addresses (
    Address VARCHAR(140),
    Pool_Id INT,
    Pool_Value BIGINT,
    FOREIGN KEY (Address) REFERENCES mining_addresses(Address)
)
"""
cursor.execute(create_pool_table_query)
connection.commit()

# Get needed data from the coinbase_data table 
cursor.execute("SELECT MAX(Last_Block_Update) FROM mining_addresses")
result = cursor.fetchone()
if not result[0]:
    select_query = "SELECT Height, Addresses, Transaction_Values, Pool_Id FROM coinbase_data"
    cursor.execute(select_query)
    coinbase_data = cursor.fetchall()
else:
    select_query = f"SELECT Height, Addresses, Transaction_Values, Pool_Id FROM coinbase_data WHERE Height > {result[0]}"
    cursor.execute(select_query)
    coinbase_data = cursor.fetchall()

print("Completing mining addresses and pool addresses tables...")
print(f"Number of blocks to process: {len(coinbase_data)}")

for row in coinbase_data:
    height = row[0]
    addresses = row[1]
    values = row[2]
    pool_id = row[3]
    for address, value in list(zip(eval(addresses), eval(values))):
        # Insert or update the mining_addresses table
        insert_address_query = f"""
            INSERT INTO mining_addresses (Address, Last_Block_Update)
            VALUES ('{address}', {height})
            ON DUPLICATE KEY UPDATE Last_Block_Update = GREATEST(Last_Block_Update, {height})
        """
        cursor.execute(insert_address_query)

        if pool_id == 0:
            continue # Do not include addresses not related to known pools
        # Check if the combination of Address and Pool_Id already exists
        select_existing_query = f"""
            SELECT Pool_Value
            FROM pool_addresses
            WHERE Address = '{address}' AND Pool_Id = {pool_id}
        """
        cursor.execute(select_existing_query)
        existing_data = cursor.fetchone()

        if existing_data:
            # Update the existing row
            update_query = f"""
                UPDATE pool_addresses
                SET Pool_Value = Pool_Value + {value}
                WHERE Address = '{address}' AND Pool_Id = {pool_id}
            """
            cursor.execute(update_query)
        else:
            # Insert a new row
            insert_pool_query = f"""
                INSERT INTO pool_addresses (Address, Pool_Id, Pool_Value)
                VALUES ('{address}', {pool_id}, {value})
            """
            cursor.execute(insert_pool_query)
    
    if height % 1000 == 0 or (result[0] and height == result[0] + 1) or height == 1:
        print(f"Block {height} / {coinbase_data[-1][0]}")
        connection.commit()

connection.commit()
cursor.execute("SELECT COUNT(*) FROM mining_addresses")
print(f"Number of mining addresses: {cursor.fetchone()[0]}")
print("Table mining_addresses completed.")
cursor.execute("SELECT COUNT(*) FROM pool_addresses")
print(f"Number of pool addresses: {cursor.fetchone()[0]}")
print("Table pool_addresses completed.")

connection.close()
