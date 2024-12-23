import yfinance as yf
import json
from snowflake.snowpark import Session

# Snowflake connection details
SNOWFLAKE_ACCOUNT = "pdfhwro-uc15394"
SNOWFLAKE_USER = "OM51"
SNOWFLAKE_PASSWORD = "Snowflake@123"
SNOWFLAKE_DATABASE = "PROJECT"
SNOWFLAKE_SCHEMA = "PROJECT_SCHEMA"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
SNOWFLAKE_TABLE = "FOREX_DATA"

# List of common currency codes
currencies = ["USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "NZD"]

# Generate all possible pairs
currency_pairs = [f"{base}{target}=X" for base in currencies for target in currencies if base != target]

# Snowflake session setup
connection_parameters = {
    "account": SNOWFLAKE_ACCOUNT,
    "user": SNOWFLAKE_USER,
    "password": SNOWFLAKE_PASSWORD,
    "database": SNOWFLAKE_DATABASE,
    "schema": SNOWFLAKE_SCHEMA,
    "warehouse": SNOWFLAKE_WAREHOUSE
}

session = Session.builder.configs(connection_parameters).create()

# Fetch and insert data
for pair in currency_pairs:
    try:
        # Fetch historical data
        forex_data = yf.Ticker(pair)
        historical_data = forex_data.history(start="2020-01-01", period="max")
        
        if not historical_data.empty:
            # Convert to flattened JSON format
            flattened_data = historical_data.reset_index().to_dict(orient="records")
            data_json = json.dumps(flattened_data)  # Convert the data to a JSON string
            
            # Create Snowpark DataFrame for insertion
            data = session.create_dataframe([(pair, data_json)], schema=["pair", "data"])
            
            # Insert data into Snowflake, ensure data is treated as VARIANT
            session.sql(f"""
                INSERT INTO {SNOWFLAKE_TABLE} (pair, data)
                SELECT ?, PARSE_JSON(?)
            """).bind(pair, data_json).collect()
            print(f"Data inserted for {pair}")
        else:
            print(f"No data available for {pair}")
    except Exception as e:
        print(f"Failed to fetch or insert data for {pair}: {e}")

# Close the Snowflake session
session.close()

print("All forex data saved to Snowflake table.")
