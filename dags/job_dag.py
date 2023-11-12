from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from datetime import timedelta
import os

default_args = {
    'owner': 'Zade',
    'start_date': datetime(2023, 11, 12),
}

dag = DAG(
    'my_dag',
    default_args=default_args,
    schedule_interval='1 0 * * *',  # Runs at 1 minute past midnight every day
    catchup=False,  # Prevent backfilling on first DAG run
)

def run_script(script_file):
    os.system(f'python {script_file}')

task_1 = PythonOperator(
    task_id='task_1',
    python_callable=run_script,
    op_args=['./job_search.py'],  # Get job id's
    dag=dag,
)

task_2 = PythonOperator(
    task_id='task_2',
    python_callable=run_script,
    op_args=['./add_techs.py'],  # Get techs from job id's
)

# task_3 = PythonOperator(
#     task_id='task_3',
#     python_callable=run_script,
#     op_args=['./check_results.py'],  # Currently not in a script, must add
#     dag=dag,
# )

# task_1 >> task_2 >> task_3  # Set the task execution order
