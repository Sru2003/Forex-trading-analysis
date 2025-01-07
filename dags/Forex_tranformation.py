from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import snowflake.connector
import pandas as pd
import json
# Snowflake connection details
SNOWFLAKE_ACCOUNT = "pdfhwro-uc15394"
SNOWFLAKE_USER = "SRUSH"
SNOWFLAKE_PASSWORD = "Snowflake@123"
SNOWFLAKE_DATABASE = "PROJECT"
SNOWFLAKE_SCHEMA = "PROJECT_SCHEMA"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
SNOWFLAKE_TABLE_SOURCE = "FOREX_DATA"
SNOWFLAKE_TABLE_TARGET = "TRANSFORMED_FOREX_DATA"
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
# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 12, 24),
}
# Define the DAG
with DAG(
    dag_id='transform_forex_data_dag',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    tags=['forex', 'pandas', 'snowflake']
) as dag:
    transform_task = PythonOperator(
        task_id='transform_and_load_forex_data',
        python_callable=transform_and_load_forex_data
    )
    transform_task