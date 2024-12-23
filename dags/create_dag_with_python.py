from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args={
    'owner': 'srush',
    'retries': 5,
    'retry_delay': timedelta(minutes=5)
}

def greet(age,ti):
    name =  ti.xcom_pull(task_ids='get_name')
    print(f"Hello World! My name is {name}, I am {age} years old")


def get_name():
    return "Jerry"
with DAG(
    default_args=default_args,
    dag_id="Our_first_dag_using_python_operator_v2",
    start_date=datetime(2024,12,17),
    schedule_interval='@daily'
    # schedule_interval=timedelta(minutes=1)
) as dag:
    task1 = PythonOperator(
        task_id='greet',
        python_callable=greet,
        op_kwargs={ 'age': 20}
    )
    task2 = PythonOperator(
        task_id='get_name',
        python_callable=get_name
    )
    task2 >> task1