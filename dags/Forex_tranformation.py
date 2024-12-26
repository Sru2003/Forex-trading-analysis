from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import snowflake.connector
import pandas as pd
import json

# Snowflake connection details
SNOWFLAKE_ACCOUNT = "pdfhwro-uc15394"
SNOWFLAKE_USER = "OM51"
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
        # Fetch data from FOREX_DATA
        cursor.execute(f"SELECT PAIR, DATA FROM {SNOWFLAKE_TABLE_SOURCE}")
        forex_data = cursor.fetchall()

        # Process FOREX data into a pandas DataFrame
        rows = []
        for pair, data in forex_data:
            data_dict = json.loads(data)
            for date, metrics in data_dict.items():
                rows.append({
                    "PAIR": pair,
                    "CALENDAR_DATE": date,
                    "HIGH": metrics.get("High"),
                    "LOW": metrics.get("Low"),
                    "OPEN": metrics.get("Open"),
                    "CLOSE": metrics.get("Close")
                })

        # Create pandas DataFrame
        forex_df = pd.DataFrame(rows)

        # Insert transformed data into Snowflake in batches
        batch_size = 50000  # Adjust this based on memory and query limits
        insert_query = f"""
            INSERT INTO {SNOWFLAKE_TABLE_TARGET} (PAIR, CALENDAR_DATE, HIGH, LOW, OPEN, CLOSE)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        for i in range(0, len(forex_df), batch_size):
            batch = forex_df.iloc[i:i + batch_size]
            data_to_insert = batch.to_records(index=False).tolist()
            cursor.executemany(insert_query, data_to_insert)
            print(f"Inserted batch {i // batch_size + 1}")

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
    schedule_interval=None,
    catchup=False,
    tags=['forex', 'pandas', 'snowflake']
) as dag:
    
    transform_task = PythonOperator(
        task_id='transform_and_load_forex_data',
        python_callable=transform_and_load_forex_data
    )
    
    transform_task
