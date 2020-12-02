From apache/airflow
COPY ./requirements.txt /opt/airflow/requirements.txt
RUN pip install -U pip --user && pip install -r requirements.txt --user

