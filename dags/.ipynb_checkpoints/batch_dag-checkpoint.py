from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from datetime import datetime, timedelta
import pandas as pd
from gdeltdoc import GdeltDoc, Filters
import snowflake.connector
from airflow.hooks.base_hook import BaseHook
import time

# Function to fetch news articles for a given date range and country
def fetch_and_insert_news_for_countries(countries, start_date, end_date, **kwargs):
    # Initialize GDELT client
    gd = GdeltDoc()
    # Fetch Snowflake connection details
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
    insert_query = """
    INSERT INTO PROJECT.PROJECT_SCHEMA.DEMO_NEWS
    (URL, URL_MOBILE, TITLE, SEENDATE, SOCIALIMAGE, DOMAIN, LANGUAGE, SOURCECOUNTRY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
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
            for country in countries:
                print(f"Processing news for country: {country}")
                current_date = datetime.strptime(start_date, "%Y-%m-%d")
                end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
                while current_date <= end_date_dt:
                    next_day = current_date + timedelta(days=1)
                    filters = Filters(
                        keyword=["currency", "forex", "finance", "disease", "war", "election",
                                 "pandemic", "inflation", "bank", "trade", "treaty"],
                        start_date=current_date.strftime("%Y-%m-%d"),
                        end_date=next_day.strftime("%Y-%m-%d"),
                        country=country,
                    )





                    try:
                        print(f"Fetching news from {current_date.strftime('%Y-%m-%d')} to {next_day.strftime('%Y-%m-%d')} for {country}...")
                        articles = gd.article_search(filters)
                        
                        if not articles.empty:
                            articles = articles.fillna('')
                            # for _, row in articles.iterrows():
                            #     cursor.execute(insert_query, (
                            #         row.get('url', ''),
                            #         row.get('url_mobile', ''),
                            #         row.get('title', ''),
                            #         row.get('seendate', ''),
                            #         row.get('socialimage', ''),
                            #         row.get('domain', ''),
                            #         row.get('language', ''),
                            #         row.get('sourcecountry', '')
                            #     ))
                          
                            articles_to_insert = []
                            for _, row in articles.iterrows():
                                articles_to_insert.append((
                                    row.get('url', ''),
                                    row.get('url_mobile', ''),
                                    row.get('title', ''),
                                    row.get('seendate', ''),
                                    row.get('socialimage', ''),
                                    row.get('domain', ''),
                                    row.get('language', ''),
                                    row.get('sourcecountry', '')
                                ))
                            
                          
                            cursor.executemany(insert_query, articles_to_insert)
                            articles_to_insert = []  # Reset the list
                            print(f"Inserted {len(articles)} articles into Snowflake table 'DEMO_NEWS' for {country}.")
                        else:
                            print(f"No valid articles found for date: {current_date.strftime('%Y-%m-%d')} and country: {country}.")
                    except Exception as e:
                        print(f"Error fetching data from {start_date} to {end_date}: {e}")
                    current_date = next_day
                    # Pause every 30th day to avoid overwhelming GDELT or Snowflake
                    if current_date.day == 30:
                        time.sleep(5)
    except Exception as e:
        print(f"Error inserting data into Snowflake: {e}")

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    'demo',
    default_args=default_args,
    description='Fetch news from GDELT for 01-01-2020 to 18-12-2024 for multiple countries and insert into Snowflake',
    schedule_interval=None,
    start_date=datetime(2024, 12, 18),
    catchup=False,
) as dag:
    fetch_and_insert_all_countries_task = PythonOperator(
        task_id='fetch_and_insert_news_all_countries',
        python_callable=fetch_and_insert_news_for_countries,
        op_kwargs={
            'countries': [ 'CH', 'JA', 'NZ', 'SZ', 'RS'],
            'start_date': '2020-01-22',
            'end_date': '2024-12-18',
        },
    )

fetch_and_insert_all_countries_task
