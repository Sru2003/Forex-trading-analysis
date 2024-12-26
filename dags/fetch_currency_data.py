# import yfinance as yf
# import pandas as pd
# import json
# from datetime import datetime
# import snowflake.connector
# # Snowflake connection details
# SNOWFLAKE_ACCOUNT = "pdfhwro-uc15394"
# SNOWFLAKE_USER = "OM51"
# SNOWFLAKE_PASSWORD = "Snowflake@123"
# SNOWFLAKE_DATABASE = "PROJECT"
# SNOWFLAKE_SCHEMA = "PROJECT_SCHEMA"
# SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
# SNOWFLAKE_TABLE = "FOREX_DATA"
# currencies = ["USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "NZD", "AED"]
# currency_pairs = [f"{base}{target}=X" for base in currencies for target in currencies if base != target]
# all_forex_data = {}
# for pair in currency_pairs:
#     try:
#         forex_data = yf.Ticker(pair)
#         historical_data = forex_data.history(start="2020-01-01")
#         all_forex_data[pair] = historical_data
#         print(f"Data fetched for {pair}")
#     except Exception as e:
#         print(f"Failed to fetch data for {pair}: {e}")
# data_from_2020_json = {}
# date_range_start = "2020-01-01"  # Start date
# current_date = datetime.today().strftime('%Y-%m-%d')  # Current date
# # Filter and prepare JSON data
# for pair, data in all_forex_data.items():
#     # Filter the data for the range 2020-01-01 to current date
#     data_in_range = data.loc[date_range_start:current_date] if not data.empty else None
#     if data_in_range is not None:
#         # Convert the index (dates) to string and prepare the data
#         data_in_range_dict = data_in_range.to_dict(orient="index")
#         data_in_range_dict = {str(key.date()): value for key, value in data_in_range_dict.items()}  # Remove time and timezone
#         # Store the date range and data
#         data_from_2020_json[pair] = data_in_range_dict
#     else:
#         data_from_2020_json[pair] = "No data available for this date range"
# # Save the forex data to a JSON file
# with open("forex_data_from_2020_to_current.json", "w") as f:
#     json.dump(data_from_2020_json, f, indent=4)
# print("Forex data saved to forex_data_from_2020_to_current.json")
# # Connect to Snowflake
# def get_snowflake_connection():
#     return snowflake.connector.connect(
#         user=SNOWFLAKE_USER,
#         password=SNOWFLAKE_PASSWORD,
#         account=SNOWFLAKE_ACCOUNT,
#         warehouse=SNOWFLAKE_WAREHOUSE,
#         database=SNOWFLAKE_DATABASE,
#         schema=SNOWFLAKE_SCHEMA
#     )
# # Insert data into Snowflake table
# # Insert data into Snowflake table
# def insert_data():
#     conn = get_snowflake_connection()
#     cursor = conn.cursor()
#     try:
#         # Open the JSON file
#         with open("forex_data_from_2020_to_current.json", "r") as f:
#             forex_data = json.load(f)
#         for pair, details in forex_data.items():
#             # Check if we have data for this pair
#             if isinstance(details, dict):  # Only proceed if data is available (not "No data available")
#                 # Prepare the SQL statement for inserting the nested JSON
#                 sql = f"""
#                     INSERT INTO {SNOWFLAKE_TABLE} (PAIR, DATA)
#                     SELECT %s, PARSE_JSON(%s)
#                 """
#                 # Insert the currency pair and its corresponding data as a JSON object
#                 cursor.execute(sql, (pair, json.dumps(details)))  # Convert the dictionary to a JSON string
#                 print(f"Inserted data for {pair}")
#     except Exception as e:
#         print(f"Error inserting into Snowflake: {e}")
#     finally:
#         cursor.close()
#         conn.close()
# # Call insert_data to save data into Snowflake
# insert_data()

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import json
import yfinance as yf
import snowflake.connector
from datetime import datetime

# Snowflake connection details (adjust these accordingly)
SNOWFLAKE_ACCOUNT = "pdfhwro-uc15394"
SNOWFLAKE_USER = "OM51"
SNOWFLAKE_PASSWORD = "Snowflake@123"
SNOWFLAKE_DATABASE = "PROJECT"
SNOWFLAKE_SCHEMA = "PROJECT_SCHEMA"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
SNOWFLAKE_TABLE = "FOREX_DATA"
currencies = ["USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "NZD", "AED"]
currency_pairs = [f"{base}{target}=X" for base in currencies for target in currencies if base != target]

# Snowflake connection function
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA
    )

# Function to fetch forex data and save it to a JSON file
def fetch_forex_data():
    all_forex_data = {}
    for pair in currency_pairs:
        try:
            forex_data = yf.Ticker(pair)
            historical_data = forex_data.history(start="2020-01-01")
            all_forex_data[pair] = historical_data
            print(f"Data fetched for {pair}")
        except Exception as e:
            print(f"Failed to fetch data for {pair}: {e}")
    data_from_2020_json = {}
    date_range_start = "2020-01-01"  # Start date
    current_date = datetime.today().strftime('%Y-%m-%d')  # Current date
    for pair, data in all_forex_data.items():
        data_in_range = data.loc[date_range_start:current_date] if not data.empty else None
        if data_in_range is not None:
            data_in_range_dict = data_in_range.to_dict(orient="index")
            data_in_range_dict = {str(key.date()): value for key, value in data_in_range_dict.items()}
            data_from_2020_json[pair] = data_in_range_dict
        else:
            data_from_2020_json[pair] = "No data available for this date range"
    with open("forex_data_from_2020_to_current.json", "w") as f:
        json.dump(data_from_2020_json, f, indent=4)
    print("Forex data saved to forex_data_from_2020_to_current.json")

# Function to insert forex data into Snowflake
def insert_data():
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        with open("forex_data_from_2020_to_current.json", "r") as f:
            forex_data = json.load(f)
        for pair, details in forex_data.items():
            if isinstance(details, dict):
                sql = f"""
                    INSERT INTO {SNOWFLAKE_TABLE} (PAIR, DATA)
                    SELECT %s, PARSE_JSON(%s)
                """
                cursor.execute(sql, (pair, json.dumps(details)))  # Insert JSON data
                print(f"Inserted data for {pair}")
    except Exception as e:
        print(f"Error inserting into Snowflake: {e}")
    finally:
        cursor.close()
        conn.close()

# Define default_args and DAG parameters
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 12, 24),  # Adjust as needed
    'catchup': False,
}

dag = DAG(
    'forex_data_insert_dag',
    default_args=default_args,
    description='A DAG to fetch forex data and insert it into Snowflake',
    schedule_interval=timedelta(days=1),  # Set this to the desired schedule
    catchup=False,
)

# Define the tasks using PythonOperator
fetch_forex_data_task = PythonOperator(
    task_id='fetch_forex_data',
    python_callable=fetch_forex_data,
    dag=dag,
)

insert_data_task = PythonOperator(
    task_id='insert_data',
    python_callable=insert_data,
    dag=dag,
)

# Set task dependencies
fetch_forex_data_task >> insert_data_task
