from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import json
import yfinance as yf
import pandas as pd
import snowflake.connector
# Snowflake connection details
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_TABLE_SOURCE = os.getenv("SNOWFLAKE_TABLE_SOURCE")
SNOWFLAKE_TABLE_TARGET = os.getenv("SNOWFLAKE_TABLE_TARGET")

currencies = ["USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "NZD", "AED", "RUB"]
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
# Function to fetch Forex data for the most recent day and append to Snowflake
def fetch_and_append_daily_forex_data():
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        print("hi")
        for pair in currency_pairs:
            print(f"fetching for")
            try:
                sql_latest_date = f"""
                    SELECT MAX(VALUE)
                    FROM TABLE(
                        FLATTEN(
                            INPUT => OBJECT_KEYS(
                                (SELECT DATA FROM {SNOWFLAKE_TABLE_SOURCE} WHERE PAIR = %s)
                            )
                        )
                    )
                """
                cursor.execute(sql_latest_date, (pair,))
                print("hi2")
                latest_date_result = cursor.fetchone()
                if latest_date_result and latest_date_result[0]:
                    # Strip double quotes and convert to datetime
                    latest_date = latest_date_result[0].strip('"')
                    start_date = (datetime.strptime(latest_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    # Default start date if no data exists
                    start_date = "2020-01-01"
                end_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                # Fetch Forex data from start_date to end_date
                forex_data = yf.Ticker(pair)
                historical_data = forex_data.history(start=start_date, end=end_date)
                if not historical_data.empty:
                    daily_data = historical_data.to_dict(orient="index")
                    daily_data = {str(key.date()): value for key, value in daily_data.items()}
                    # Append the fetched data to Snowflake
                    # sql_merge = f"""
                    #     MERGE INTO {SNOWFLAKE_TABLE_SOURCE} AS target
                    #     USING (SELECT %s AS PAIR, PARSE_JSON(%s) AS DATA) AS source
                    #     ON target.PAIR = source.PAIR
                    #     WHEN MATCHED THEN
                    #         UPDATE SET target.DATA = OBJECT_INSERT(target.DATA, %s, source.DATA)
                    #     WHEN NOT MATCHED THEN
                    #         INSERT (PAIR, DATA) VALUES (source.PAIR, source.DATA);
                    # """
                    sql_update = f"""
                        UPDATE {SNOWFLAKE_TABLE_SOURCE}
                        SET DATA = OBJECT_INSERT(DATA, %s, PARSE_JSON(%s))
                        WHERE PAIR = %s
                    """
                    for date, details in daily_data.items():
                        cursor.execute(sql_merge, (pair, json.dumps({date: details}), date))
                    print(f"Appended data for {pair} from {start_date} to {end_date}")
                else:
                    print(f"No new data available for {pair} from {start_date} to {end_date}")
            except Exception as e:
                print(f"Failed to fetch or append data for {pair}: {e}")
    except Exception as e:
        print(f"Error updating Snowflake: {e}")
    finally:
        cursor.close()
        conn.close()
# Task to expand, transform, and insert data
def transform_and_load_forex_data():
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT DISTINCT PAIR FROM {SNOWFLAKE_TABLE_SOURCE}")
        pairs = [row[0] for row in cursor.fetchall()]
        for pair in pairs:
            # Fetch the last calendar date from the TRANSFORMED_FOREX_DATA table
            cursor.execute(f"SELECT MAX(CALENDAR_DATE) FROM {SNOWFLAKE_TABLE_TARGET} WHERE PAIR = %s", (pair,))
            last_date_result = cursor.fetchone()
            # Determine start and end dates
            if last_date_result and last_date_result[0]:
                last_calendar_date = last_date_result[0]
                start_date = (last_calendar_date + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                start_date = "2020-01-01"  # Default start date if no data exists for the pair
            print(start_date)
            end_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            # Fetch data for the pair from FOREX_DATA
            cursor.execute(f"SELECT DATA FROM {SNOWFLAKE_TABLE_SOURCE} WHERE PAIR = %s", (pair,))
            forex_data = cursor.fetchone()
            if not forex_data:
                print(f"No data found for pair {pair}")
                continue
            data_dict = json.loads(forex_data[0])
            rows = []
            # Filter and process data within the date range
            for date, metrics in data_dict.items():
                if start_date <= date <= end_date:
                    rows.append({
                        "PAIR": pair,
                        "CALENDAR_DATE": date,
                        "HIGH": metrics.get("High"),
                        "LOW": metrics.get("Low"),
                        "OPEN": metrics.get("Open"),
                        "CLOSE": metrics.get("Close")
                    })
            # Insert filtered data into the target table
            if rows:
                forex_df = pd.DataFrame(rows)
                batch_size = 5000  # Adjust based on your needs
                insert_query = f"""
                    INSERT INTO {SNOWFLAKE_TABLE_TARGET} (PAIR, CALENDAR_DATE, HIGH, LOW, OPEN, CLOSE)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                for i in range(0, len(forex_df), batch_size):
                    batch = forex_df.iloc[i:i + batch_size]
                    data_to_insert = batch.to_records(index=False).tolist()
                    cursor.executemany(insert_query, data_to_insert)
                    print(f"Inserted batch {i // batch_size + 1} for pair {pair}")
            else:
                print(f"No new data to transform for pair {pair}")
        print("Data transformation and insertion completed.")
    except Exception as e:
        print(f"Error during transformation: {e}")
    finally:
        cursor.close()
        conn.close()
# Define DAG default_args
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 12, 24),
    'catchup': False,
}
# Define DAG
with DAG(
    'fetch_and_transform_forex_data',
    default_args=default_args,
    description='A DAG to fetch and append daily Forex data into Snowflake',
    schedule_interval=None,
    catchup=False,
) as dag:
# Define the task using PythonOperator
    fetch_and_append_task = PythonOperator(
        task_id='fetch_and_append_daily_forex_data',
        python_callable=fetch_and_append_daily_forex_data,
        dag=dag,
    )
    transform_task = PythonOperator(
            task_id='transform_and_load_forex_data',
            python_callable=transform_and_load_forex_data
        )
    fetch_and_append_task>>transform_task
