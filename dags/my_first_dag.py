from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.bash import BashOperator

default_args={
    'owner': 'srush',
    'retries':5,
    'retry_delay': timedelta(minutes=2)
}

with DAG(
    dag_id='my_first_dag_v3',
    default_args=default_args,
    description='This is my first dag',
    start_date=datetime(2024,12,16),
    schedule_interval=timedelta(minutes=1)
) as dag:
    task1 = BashOperator(
        task_id='first_task',
        bash_command='echo hello world'
    )

    task2 = BashOperator(
            task_id='second_task',
            bash_command='echo task2 runs after task1'
        )

    task3 = BashOperator(
        task_id='third_task',
        bash_command='echo task3 runs after task1 and with task2'
    )
    task1.set_downstream(task2)  
    task1.set_downstream(task3) 