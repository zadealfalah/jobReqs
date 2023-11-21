from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime
from datetime import timedelta
import os
import sys




default_args = {
    'owner': 'Zade',
    'depends_on_past': False,
    'start_date': datetime(2023, 11, 19),
    'retries': 0,
    # 'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'jobdag',
    default_args=default_args,
    # schedule_interval='1 0 * * *',  # Runs at 1 minute past midnight every day
    schedule='1 0 * * *',  # Test with schedule instead of schedule_interval

    catchup=False,  # Prevent backfilling on first DAG run
)

# def run_script(script_file):
#     print(f"Running script: {script_file}")
#     os.system(f'python {script_file}')

task_1 = BashOperator(
    task_id='task_1',
    bash_command = 'cd /opt/airflow/dags/scripts && python job_search.py',
    dag=dag,
)

# task_2 = BashOperator(
#     task_id='task_2',
#     bash_command='python add_techs.py',
#     dag=dag
# )

# task_3 = PythonOperator(
#     task_id='task_3',
#     python_callable=run_script,
#     op_args=['./check_results.py'],  # Currently not in a script, must add
#     dag=dag,
# )

task_1  # start with just task 1 for now

# task_1 >> task_2  # Have job search and add tech, ignore the check results for now.

# task_1 >> task_2 >> task_3  # Set the task execution order

# Will need to add a task to copy the new files to local machine with dockeroperator or something.
