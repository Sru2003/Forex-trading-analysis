from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from datetime import datetime, timedelta
from airflow import DAG
from gdeltdoc import GdeltDoc, Filters
import snowflake.connector
from airflow.hooks.base_hook import BaseHook
import time
# Function to fetch news articles for a given date range and country
def fetch_and_insert_news_for_countries(end_date, **kwargs):
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
    INSERT INTO PROJECT.PROJECT_SCHEMA.NEWS_DATA
    (URL, URL_MOBILE, TITLE, SEENDATE, SOCIALIMAGE, DOMAIN, LANGUAGE, SOURCECOUNTRY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    update_last_execution_query = """
    UPDATE PROJECT.PROJECT_SCHEMA.FETCH_LOG
    SET LAST_EXECUTED_DATE = %s
    WHERE COUNTRY = %s;
    """
    get_last_execution_query = """
    SELECT LAST_EXECUTED_DATE
    FROM PROJECT.PROJECT_SCHEMA.FETCH_LOG
    WHERE COUNTRY = %s;
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
            # Fetch keywords from the KEYWORDS table
            cursor.execute("SELECT KEYWORD FROM KEYWORDS")
            keywords = [row[0] for row in cursor.fetchall()]
            # Fetch countries from the COUNTRIES2 table
            cursor.execute("SELECT COUNTRY_CODE FROM COUNTRIES")
            countries = [row[0] for row in cursor.fetchall()]
            print(f"Fetched Keywords: {keywords}")
            print(f"Fetched Countries: {countries}")
            for country in countries:
                print(f"Processing news for country: {country}")
                # Fetch the last executed date for the country
                cursor.execute(get_last_execution_query, (country,))
                last_executed_date = cursor.fetchone()
                print(last_executed_date[0].strftime('%Y-%m-%d'))
                # If last executed date is None, set it to default ('2020-01-01')
                if last_executed_date and last_executed_date[0]:
                    start_date = last_executed_date[0].strftime('%Y-%m-%d') if isinstance(last_executed_date[0], datetime) else last_executed_date[0].strftime('%Y-%m-%d')
                else:
                    start_date = '2020-01-01'  # Default start date in string format
                current_date = start_date
                # Ensure current_date is a string in 'YYYY-MM-DD' format
                if isinstance(current_date, datetime):
                    current_date = current_date.strftime('%Y-%m-%d')
                current_date = datetime.strptime(current_date, '%Y-%m-%d')
                end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
                # print(f"{current_date_dt} to {end_date_dt}")
                while current_date <= end_date_dt:
                    time.sleep(5)
                    next_day = current_date + timedelta(days=1)
                    filters = Filters(
                        keyword=keywords,
                        start_date=current_date.strftime("%Y-%m-%d"),
                        end_date=next_day.strftime("%Y-%m-%d"),
                        country=country,
                    )
                    try:
                        print(f"Fetching news from {current_date.strftime('%Y-%m-%d')} to {next_day.strftime('%Y-%m-%d')} for {country}...")
                        articles = gd.article_search(filters)
                        if not articles.empty:
                            articles = articles.fillna('')
                            articles_to_insert = [
                                (
                                    row.get('url', ''),
                                    row.get('url_mobile', ''),
                                    row.get('title', ''),
                                    row.get('seendate', ''),
                                    row.get('socialimage', ''),
                                    row.get('domain', ''),
                                    row.get('language', ''),
                                    row.get('sourcecountry', '')
                                )
                                for _, row in articles.iterrows()
                            ]
                            cursor.executemany(insert_query, articles_to_insert)
                            print(f"Inserted {len(articles)} articles into Snowflake table 'NEWS_DATA' for {country}.")
                        else:
                            print(f"No valid articles found for date: {current_date.strftime('%Y-%m-%d')} and country: {country}.")
                        # Update the last execution date
                        cursor.execute(update_last_execution_query, (current_date.strftime("%Y-%m-%d"), country))
                        conn.commit()
                    except Exception as e:
                        if "non-successful statuscode" in str(e):
                            print(f"Error fetching data: {e}. Stopping execution.")
                            cursor.execute(update_last_execution_query, (current_date.strftime("%Y-%m-%d"), country))
                            conn.commit()
                            raise e  # Stop execution for this country
                        else:
                            print(f"Non-critical error: {e}. Skipping to next date.")
                    current_date = next_day
                    print(f"Proceeding to next date: {current_date}")
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
    'test',
    default_args=default_args,
    description='Fetch news from GDELT for multiple countries and insert into Snowflake with last execution tracking',
    schedule_interval='@daily',
    start_date=datetime(2024, 12, 19),
    catchup=False,
) as dag:
    fetch_and_insert_all_countries_task = PythonOperator(
        task_id='fetch_and_insert_news_all_countries',
        python_callable=fetch_and_insert_news_for_countries,
        op_kwargs={
            'end_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        },
    )
fetch_and_insert_all_countries_task






