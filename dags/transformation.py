from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow import DAG
import snowflake.connector
from airflow.hooks.base_hook import BaseHook
from deep_translator import GoogleTranslator
import uuid
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
    offset = 0  # Initialize the offset
    read_query = """
    SELECT TITLE, SEENDATE, SOURCECOUNTRY
    FROM PROJECT.PROJECT_SCHEMA.NEWS_DATA1
    LIMIT %s OFFSET %s;
    """
    insert_query = """
    INSERT INTO PROJECT.PROJECT_SCHEMA.TRANFORMRED_NEWS_DATA1 (TITLE, SOURCECOUNTRY, DATE)
    VALUES (%s, %s, %s)
    """
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
                    title, seen_date, source_country = row
                    # Translate the title using deep-translator (to English)
                    translated_title = GoogleTranslator(source='auto', target='en').translate(title)
                    # Convert SEENDATE from 'YYYYMMDDTHHMMSSZ' to 'YYYY-MM-DD'
                    formatted_seen_date = datetime.strptime(seen_date, '%Y%m%dT%H%M%SZ').strftime('%Y-%m-%d')
                    # Add transformed row to batch
                    transformed_data_batch.append((translated_title, source_country, formatted_seen_date))
                    # Insert in chunks of `insert_batch_size`
                    if len(transformed_data_batch) == insert_batch_size:
                        cursor.executemany(insert_query, transformed_data_batch)
                        print(f"Inserted {len(transformed_data_batch)} rows.")
                        transformed_data_batch = []  # Reset the batch
                        time.sleep(2)
                # Insert any remaining rows in the batch
                if transformed_data_batch:
                    cursor.executemany(insert_query, transformed_data_batch)
                    print(f"Inserted {len(transformed_data_batch)} remaining rows.")
                # Update the offset to fetch the next batch
                offset += batch_size
    except Exception as e:
        print(f"Error transforming data into Snowflake: {e}")
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
    schedule_interval=None,
    start_date=datetime(2024, 12, 19),
    catchup=False,
) as dag:
    transform_row_by_row = PythonOperator(
        task_id='fetch_and_insert_news_all_countries',
        python_callable=fetch_and_insert_news_for_countries,
        op_kwargs={
            'batch_size': 1000,  # Number of rows to fetch at a time
            'insert_batch_size': 10,  # Number of rows to insert at a time
        },
    )