from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow import DAG
import snowflake.connector
from airflow.hooks.base_hook import BaseHook
from deep_translator import GoogleTranslator
import uuid
import time
def fetch_and_insert_news_for_countries(batch_size=500000, insert_batch_size=1000):
    snowflake_conn_id = 'snowflake_con'
    snowflake_conn = BaseHook.get_connection(snowflake_conn_id)
    # Snowflake connection parameters
    account = "pdfhwro-uc15394"
    user = snowflake_conn.login
    password = snowflake_conn.password
    warehouse = snowflake_conn.extra_dejson.get('warehouse', 'COMPUTE_WH')
    database = "PROJECT"
    schema = "PROJECT_SCHEMA"
    role = snowflake_conn.extra_dejson.get('role', 'ACCOUNTADMIN')
    # Fetch the last offset value from the tracking table (TRANSFORMED_ROWS_TRACKER)
    offset = 0
    try:
        with snowflake.connector.connect(
            user=user,
            password=password,
            account=account,
            warehouse=warehouse,
            database=database,
            schema=schema,
            role=role,
        ) as conn:
            cursor = conn.cursor()
            # Get the last ROW_COUNT (offset) value
            cursor.execute("SELECT MAX(ROW_COUNT) FROM PROJECT.PROJECT_SCHEMA.TRANSFORMED_ROWS_TRACKER")
            result = cursor.fetchone()
            print(result[0])
            if result and result[0] is not None:
                offset = result[0]  # Set offset to the last value from the tracker table
            else:
                offset = 0  # Set to 0 if no rows exist in the tracker table (first execution)
    except Exception as e:
        print(f"Error fetching offset: {e}")
        offset = 0  # Set to 0 if any error occurs while fetching offset
    read_query = """
    select TITLE, SEENDATE, SOURCECOUNTRY, DOMAIN
    from news_data
    where LANGUAGE='English'
    AND DOMAIN IN (
        select DOMAIN
        from news_data
        group by DOMAIN
        having count(DOMAIN) > 100
    )
    LIMIT %s OFFSET %s;
    """
    insert_query = """
    INSERT INTO PROJECT.PROJECT_SCHEMA.TRANFORMRED_NEWS_DATA (TITLE, SOURCECOUNTRY, DATE, DOMAIN)
    VALUES (%s, %s, %s, %s)
    """
    tracking_query = """
    INSERT INTO PROJECT.PROJECT_SCHEMA.TRANSFORMED_ROWS_TRACKER (ROW_COUNT)
    VALUES (%s)
    """
    rows_processed = 0
    try:
        with snowflake.connector.connect(
            user=user,
            password=password,
            account=account,
            warehouse=warehouse,
            database=database,
            schema=schema,
            role=role,
        ) as conn:
            cursor = conn.cursor()
            while True:
                # Fetch rows in the current batch
                cursor.execute(read_query, (batch_size, offset))
                rows = cursor.fetchall()
                if not rows:  # Exit loop if no more rows
                    print("No more data to process.")
                    break
                transformed_data_batch = []
                for row in rows:
                    title, seen_date, source_country, domain = row
                    formatted_seen_date = datetime.strptime(seen_date, '%Y%m%dT%H%M%SZ').strftime('%Y-%m-%d')
                    # Add transformed row to batch
                    transformed_data_batch.append((title, source_country, formatted_seen_date, domain))
                    rows_processed += 1
                    # Insert in chunks of `insert_batch_size`
                    if len(transformed_data_batch) == insert_batch_size:
                        cursor.executemany(insert_query, transformed_data_batch)
                        print(f"Inserted {len(transformed_data_batch)} rows.")
                        transformed_data_batch = []  # Reset the batch
                # Insert any remaining rows in the batch
                if transformed_data_batch:
                    cursor.executemany(insert_query, transformed_data_batch)
                    print(f"Inserted {len(transformed_data_batch+offset)} remaining rows.")
                # Log the number of rows processed and update the tracker
                offset+=rows_processed
                cursor.execute(tracking_query, (offset))
                print(f"Logged {rows_processed} rows in tracking table.")
    except Exception as e:
        print(f"Error transforming data into Snowflake: {e}")
# Define DAG parameters and start the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}
with DAG(
    'transform',
    default_args=default_args,
    description='Fetch news from GDELT for multiple countries and insert into Snowflake with last execution tracking',
    schedule_interval='@daily',
    start_date=datetime(2024, 12, 19),
    catchup=False,
) as dag:
    transform_row_by_row = PythonOperator(
        task_id='fetch_and_insert_news_all_countries',
        python_callable=fetch_and_insert_news_for_countries,
        op_kwargs={
            'batch_size': 10000,  # Number of rows to fetch at a time
            'insert_batch_size': 1000,  # Number of rows to insert at a time
        },
    )