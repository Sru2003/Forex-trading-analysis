from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.bash import BashOperator

default_args={
    'owner': 'srush',
    'retries':5,
    'retry_delay': timedelta(minutes=2)
}

with DAG(
    dag_id='my_first_dag',
    default_args=default_args,
    description='This is my first dag',
    start_date=datetime(2024,12,17,15),
    schedule_interval='@daily'
) as dag:
    task1 = BashOperator(
        task_id='first_task',
        bash_command='echo hello world'
    )
