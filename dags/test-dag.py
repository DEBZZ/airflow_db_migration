import logging
from datetime import timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import os
from airflow.hooks.postgres_hook import PostgresHook
from airflow.hooks.base_hook import BaseHook
from airflow.utils import dates
from airflow.models import Connection
from airflow import settings
from configparser import ConfigParser


logging.basicConfig(format="%(name)s-%(levelname)s-%(asctime)s-%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

default_args = {
    "owner": "test",
    "description": (
        "DAG to migrate data"
    ),
    "depends_on_past": False,
    "start_date": dates.days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "provide_context": True,
}
new_dag = DAG(
    'test-dag-airflow',
    default_args=default_args,
    schedule_interval=None,
)


def check_conn_exist(**kwargs):
    '''
    Checking if the connection exists. If not, add the connection to Airflow connection list
    '''
    try:
        ti = kwargs['ti']
        fetched_val = ti.xcom_pull(task_ids=kwargs['t_id'])
        BaseHook.get_connection(fetched_val['conn_id'])
    except Exception as e:
        print(e)
        new_conn = Connection(conn_id=fetched_val['conn_id'],
                              login=fetched_val['login'],
                              host=fetched_val['host'], conn_type=fetched_val['conn_type'], port=fetched_val['port'],
                              schema=None)
        new_conn.set_password(fetched_val['password'])
        session = settings.Session()
        session.add(new_conn)
        session.commit()


def fetch_data_from_postgres(**kwargs):
    '''
    Fetching data from SourceDB and storing in NFS
    '''
    ti = kwargs['ti']
    fetched_val = ti.xcom_pull(task_ids='read_configuration_src')
    print(fetched_val)
    postgres_hook = PostgresHook(postgres_conn_id=fetched_val['conn_id'], schema=fetched_val['schema'])
    f = open("testfile.csv", "w")
    records_received = postgres_hook.get_records(sql=kwargs['sql'].format(**fetched_val))
    for row in records_received:
        print(row)
        f.write(','.join([str(tup) for tup in row]) + '\n')
    f.close()
    return len(records_received)


def insert_data_into_postgres(**kwargs):
    '''
    Inserting data from NFS to Destination DB
    '''
    ti = kwargs['ti']
    fetched_val = ti.xcom_pull(task_ids='read_configuration_dest')
    print(fetched_val)
    postgres_hook = PostgresHook(postgres_conn_id=fetched_val['conn_id'], schema=fetched_val['schema'])
    f = open("testfile.csv", "r")
    lst = []
    for line in f.readlines():
        print(line.replace('\n','').split(',')[1:])
        lst.append(tuple(line.replace('\n','').split(',')[1:]))
    postgres_hook.insert_rows(table= fetched_val['tablename'], rows=iter(lst),target_fields=fetched_val['colname'].split(','))
    print("------- Data stored successfully in Destination DB ------------")


def count_validation_after_fetching(**kwargs):

    '''
    Validating the count of data stored in NFS with the count in Source DB
    '''
    ti = kwargs['ti']
    # get value_1
    pulled_value_1 = ti.xcom_pull(task_ids='fetch_data')
    print("VALUE IN PULLER : ", pulled_value_1)
    os.getcwd()
    with open("testfile.csv", 'rb') as f:
        count_each_partition = sum(1 for _ in f)
    if count_each_partition == pulled_value_1:
        print("Count matching")
    else:
        print("Count not matching")


def count_validation_after_migration(**kwargs):
    '''
    Validating the records from source and destination db after migration
    '''
    src_config = read_config(section='src')
    dest_config = read_config(section='dest')
    postgres_hook_src = PostgresHook(postgres_conn_id=src_config['conn_id'], schema=src_config['schema'])
    postgres_hook_dest = PostgresHook(postgres_conn_id=dest_config['conn_id'], schema=dest_config['schema'])
    src_res = postgres_hook_src.get_records(sql=kwargs['sql'].format(**src_config))
    dest_res = postgres_hook_dest.get_records(sql=kwargs['sql'].format(**dest_config))
    print(src_res)
    print(dest_res)

    if src_res == dest_res :
        print("Validation of data for both source and destination DB passed")
    else:
        print("Validation of data for both source and destination DB failed")



def read_config(section, filename='/opt/airflow/dags/config.ini',key=None, **kwargs):
    '''
    Reading config file
    '''
    print(os.getcwd())
    parser = ConfigParser()
    parser.read(filename)
    db = {}
    if parser.has_section(section):
        params = parser.items(section)

        for param in params:
            db[param[0]] = param[1]
        if key != None:
            return db.get(key, 'Not found')
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


task_1 = PythonOperator(
    task_id='read_configuration_src',
    op_kwargs={'section': 'src'},
    python_callable=read_config,
    provide_context=True,
    dag=new_dag
)

task_2 = PythonOperator(
    task_id='check_conn_src',
    op_kwargs={'t_id': 'read_configuration_src'},
    python_callable=check_conn_exist,
    provide_context=True,
    dag=new_dag
)

task_3 = PythonOperator(
    task_id='fetch_data_src',
    op_kwargs={'sql': 'SELECT * FROM {tablename}'},
    python_callable=fetch_data_from_postgres,
    provide_context=True,
    dag=new_dag
)

task_4 = PythonOperator(
    task_id='Record_count_validation',
    python_callable=count_validation_after_fetching,
    provide_context=True,
    dag=new_dag
)

task_5 = PythonOperator(
    task_id='read_configuration_dest',
    op_kwargs={'section': 'dest'},
    python_callable=read_config,
    provide_context=True,
    dag=new_dag
)

task_6 = PythonOperator(
    task_id='check_conn_dest',
    op_kwargs={'t_id': 'read_configuration_dest'},
    python_callable=check_conn_exist,
    provide_context=True,
    dag=new_dag
)

task_7 = PythonOperator(
    task_id='insert_data_dest',
    op_kwargs=None,
    python_callable=insert_data_into_postgres,
    provide_context=True,
    dag=new_dag
)

task_8 = PythonOperator(
    task_id='Validation_data_after_migration',
    op_kwargs={'sql': 'SELECT * FROM {tablename}'},
    python_callable=count_validation_after_migration,
    provide_context=True,
    dag=new_dag
)
task_1 >> task_2 >> task_3 >> task_4 >> task_5 >> task_6 >> task_7 >> task_8
