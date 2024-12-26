from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import json
import yfinance as yf
import snowflake.connector
# Snowflake connection details
SNOWFLAKE_ACCOUNT = "pdfhwro-uc15394"
SNOWFLAKE_USER = "OM51"
SNOWFLAKE_PASSWORD = "Snowflake@123"
SNOWFLAKE_DATABASE = "PROJECT"
SNOWFLAKE_SCHEMA = "PROJECT_SCHEMA"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
SNOWFLAKE_TABLE = "FOREX_DATA"
currencies = ["USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "NZD", "AED"]
# currencies = ["USD", "EUR"]
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
        for pair in currency_pairs:
            try:
                # Query Snowflake to get the latest date for the pair
                sql_latest_date = f"""
                    SELECT MAX(VALUE)
                    FROM TABLE(
                        FLATTEN(
                            INPUT => OBJECT_KEYS(
                                (SELECT DATA FROM {SNOWFLAKE_TABLE} WHERE PAIR = %s)
                            )
                        )
                    )
                """
                cursor.execute(sql_latest_date, (pair,))
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
                    sql_update = f"""
                        UPDATE {SNOWFLAKE_TABLE}
                        SET DATA = OBJECT_INSERT(DATA, %s, PARSE_JSON(%s))
                        WHERE PAIR = %s
                    """
                    for date, details in daily_data.items():
                        cursor.execute(sql_update, (date, json.dumps(details), pair))
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
# Define DAG default_args
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 12, 24),
    'catchup': False,
}
# Define DAG
dag = DAG(
    'forex',
    default_args=default_args,
    description='A DAG to fetch and append daily Forex data into Snowflake',
    schedule_interval='@daily',
    catchup=False,
)
# Define the task using PythonOperator
fetch_and_append_task = PythonOperator(
    task_id='fetch_and_append_daily_forex_data',
    python_callable=fetch_and_append_daily_forex_data,
    dag=dag,
)