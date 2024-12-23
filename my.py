from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

def test_snowflake_connection():
    print("hello")
    try:
        # Create a SnowflakeHook instance using the connection ID from Airflow
        snowflake_hook = SnowflakeHook(snowflake_conn_id='snowflake_con')  # Replace with your connection ID
        # Get connection object
        connection = snowflake_hook.get_conn()
        # Create a cursor and run a test query
        cursor = connection.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")  # This is a simple test query
        result = cursor.fetchone()
        print(f"Snowflake Connection Successful: {result}")
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")

# Call the function to test the connection
test_snowflake_connection()
