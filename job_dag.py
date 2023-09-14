from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators import BashOperator, PythonOperator
from airflow.utils.dates import days_ago

import os
from dotenv import load_dotenv
load_dotenv()


default_args = {
    'owner':'airflow',
    'depends_on_past':False,
    'email':os.getenv("airflow_email"),
    'email_on_failure': True,
    'email_on_retry':True,
    'retries':1,
    'retry_delay':timedelta(minutes=5)
}

dag = DAG(
    'test',
    default_args=default_args,
    description='Test DAG',
    schedule_interval=timedelta(days=1),
    start_date=days_ago(1), #set this to start 12:01 on whatever day when I actually launch it
    tags=['testing']
)

get_jobs_script = fr"jobSearch.py"
add_techs_script = fr"add_techs.py"



#Used to get the raw_data-{date}.json files
t1 = BashOperator(
    task_id="get_jobs",
    bash_command=f"python {get_jobs_script}",
    dag=dag
)

t2 = BashOperator(
    task_id="add_techs",
    bash_command=f"python {add_techs_script}",
    dag=dag
)

t1 >> t2