FROM apache/airflow:2.7.3

USER root
# Install system-level dependencies
RUN apt-get update && \
    apt-get install -y wget bzip2 libxtst6 libgtk-3-0 libx11-xcb-dev libdbus-glib-1-2 libxt6 libpci-dev && \
    rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements.txt /

RUN echo ${AIRFLOW_VERSION}

# Upgrade pip
RUN pip install --user --upgrade pip

# Install Apache Airflow and Python dependencies
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

RUN mkdir /home/airflow/.cache/selenium